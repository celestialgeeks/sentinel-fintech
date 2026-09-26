"""Portal ledger reads: ``/api/v1/portal/*`` — orders, buyers, settlement, feed.

Everything here is authenticated and merchant-scoped. The prefix matters:
``HmacAuthMiddleware`` signs-guarding applies to POSTs under ``/api/v1/p2p/``,
which is the bot's surface. Portal writes therefore live under ``/portal`` so a
browser session and a signed bot call never trip over each other. Two paths
changed hands when this module arrived:

* ``GET /p2p/orders/{order_id}/evidence`` used to sit on the bot router with no
  authentication at all. It returns an evidence pack containing buyer names, UTRs
  and masked account numbers, so an enumerable order id was a PII oracle. It now
  lives here, behind a session token and a merchant check — bots do not need
  evidence packs, the compliance human does.
* ``POST /p2p/liens`` still lives on the bot router (bank-facing webhook intake)
  but the portal has its own create route that files the case into the caller's
  workspace rather than trusting a caller-supplied ``merchant_id``.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session, session_factory
from src.core.models import P2POrderRecord
from src.p2p import evidence as evidence_builder
from src.p2p import lien as lien_intake
from src.p2p.schemas import LienNotice
from src.portal.deps import AccessScope, get_scope

# ``aggregates`` rather than ``insights``: the /insights endpoint below is itself
# named ``insights``, and a module import with the same name would shadow it.
from src.portal.ledger import aggregates, cases, orders
from src.portal.ledger.scoping import Filters
from src.portal.schemas import (
    ComplianceRow,
    CounterpartyRow,
    LienCaseFile,
    LienCreateRequest,
    LienRow,
    LienUpdateRequest,
    OrderDetail,
    OrderRow,
    OverrideRequest,
    OverviewResponse,
    Page,
    StatsSummary,
    VoucherRow,
)

router = APIRouter(prefix="/portal", tags=["portal-ledger"])

CSV_COLUMNS = (
    "order_id", "merchant_id", "decided_at", "phase", "verdict", "action", "risk_score", "confidence",
    "asset", "fiat", "qty", "price_inr", "inr_value", "buyer_user", "buyer_name", "buyer_country",
    "payment_method", "utr", "payer_name", "account_no_masked", "hard_rules", "reasons", "degraded",
    "evidence_ref", "voucher_ref", "pool", "spend_usd", "latency_ms",
)


def _keys_or_400(scope: AccessScope, merchant: str | None) -> tuple[str, ...]:
    keys = scope.resolve(merchant)
    if not keys:
        raise HTTPException(status_code=400, detail="no merchant workspace on this account")
    return keys


# ─── Ledger ───────────────────────────────────────────────────────────────────


@router.get("/orders", response_model=Page[OrderRow])
async def list_orders(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    verdict: list[str] | None = Query(None, description="ALLOW / HOLD / BLOCK, repeatable"),
    phase: list[str] | None = Query(None, description="pre_screen / release_gate, repeatable"),
    risk_min: float | None = Query(None, ge=0, le=1),
    risk_max: float | None = Query(None, ge=0, le=1),
    hard_rule: str | None = Query(None, description="Exact rule name, e.g. mule_account"),
    degraded: bool | None = Query(None),
    has_utr: bool | None = Query(None),
    payment_method: str | None = Query(None),
    pool: str | None = Query(None, description="quarantine | operating"),
    confirmed: bool | None = Query(None),
    buyer_key: str | None = Query(None),
    search: str | None = Query(None, description="order id, UTR, VPA, buyer"),
    since: datetime | None = Query(None, description="ISO instant, inclusive, on decided_at"),
    until: datetime | None = Query(None),
    sort: str = Query("decided_at"),
    desc: bool = Query(True),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[OrderRow]:
    """The transaction history table."""
    keys = _keys_or_400(scope, merchant)
    filters = Filters(
        verdicts=verdict, phases=phase, risk_min=risk_min, risk_max=risk_max, hard_rule=hard_rule,
        degraded=degraded, has_utr=has_utr, payment_method=payment_method, pool=pool, confirmed=confirmed,
        buyer_key=buyer_key, search=search, start=_naive(since), end=_naive(until),
    )
    return await orders.list_orders(
        session, keys, filters=filters, sort=sort, desc=desc, limit=limit, offset=offset
    )


def _naive(value: datetime | None) -> datetime | None:
    """Query params arrive tz-aware; the ledger column is naive UTC."""
    if value is None:
        return None
    return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value


@router.get("/orders/export")
async def export_orders(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    verdict: list[str] | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(5000, ge=1, le=20_000),
) -> Response:
    """CSV for the bank email or the CA. Same filters as the table."""
    keys = _keys_or_400(scope, merchant)
    filters = Filters(
        verdicts=verdict, start=_naive(since), end=_naive(until)
    )
    page = await orders.list_orders(session, keys, filters=filters, limit=limit)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in page.items:
        record = row.model_dump()
        record["decided_at"] = record["decided_at"].isoformat() if record["decided_at"] else ""
        record["hard_rules"] = ";".join(record["hard_rules"])
        record["reasons"] = ";".join(record["reasons"])
        writer.writerow(record)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="sentinel-orders-{stamp}.csv"'},
    )


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: str,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
) -> OrderDetail:
    """One order, with the verdict, signals, sources, pack, voucher and history."""
    keys = _keys_or_400(scope, merchant)
    detail = await orders.order_detail(session, keys, order_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"no order '{order_id}' in your workspace")
    return detail


@router.get("/orders/{order_id}/evidence")
async def download_evidence(
    order_id: str,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    fmt: str = Query("markdown", pattern="^(markdown|json)$"),
) -> Response:
    """The stored pack, authenticated and scoped to your workspaces."""
    keys = _keys_or_400(scope, None)
    record, _reason = await orders.get_record(session, keys, order_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no order '{order_id}' in your workspace")
    bundle = await cases.latest_bundle(session, keys, order_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"no evidence bundle for order {order_id}")
    body = (
        evidence_builder.to_markdown(bundle)
        if fmt == "markdown"
        else evidence_builder.to_json(bundle)
    )
    media = "text/markdown" if fmt == "markdown" else "application/json"
    ref = bundle.get("reference", "EV-UNKNOWN")
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{ref}.{"md" if fmt == "markdown" else "json"}"'},
    )


@router.post("/orders/{order_id}/override", response_model=OrderDetail)
async def override_order(
    order_id: str,
    req: OverrideRequest,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
) -> OrderDetail:
    """Record a human disagreement. The verdict and the pack are never rewritten."""
    keys = _keys_or_400(scope, None)
    if req.action not in ("release", "hold", "reject"):
        raise HTTPException(status_code=400, detail="action must be release, hold or reject")
    record, _reason = await orders.get_record(session, keys, order_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no order '{order_id}' in your workspace")
    if req.action == "release":
        # Releasing is the override that can cost money, so it needs the owner of
        # the workspace this order actually belongs to — not of whichever one the
        # caller listed first.
        if scope.role_in(record.merchant_id) != "owner":
            raise HTTPException(
                status_code=403,
                detail="only an owner may override a decision to release; risk and read roles cannot",
            )
    await cases.record_override(session, keys, order_id, scope.user.email, req.action, req.reason)
    detail = await orders.order_detail(session, keys, order_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"no order '{order_id}' in your workspace")
    return detail


@router.get("/holds", response_model=Page[OrderRow])
async def list_holds(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    sort: str = Query("decided_at", description="decided_at (oldest first) or inr_value"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[OrderRow]:
    """The step-up worklist, ordered by how close it is to expiring."""
    keys = _keys_or_400(scope, merchant)
    filters = Filters(verdicts=["HOLD"])
    return await orders.list_orders(
        session, keys, filters=filters, sort=sort, desc=(sort == "inr_value"), limit=limit, offset=offset
    )


# ─── Counterparties ───────────────────────────────────────────────────────────


@router.get("/counterparties", response_model=Page[CounterpartyRow])
async def list_counterparties(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    search: str | None = Query(None),
    flagged_only: bool = Query(False),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    sort: str = Query("seen"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[CounterpartyRow]:
    """Repeat buyers: your own history with each one."""
    keys = _keys_or_400(scope, merchant)
    return await cases.list_counterparties(
        session, keys, search=search, flagged_only=flagged_only,
        start=_naive(since), end=_naive(until), sort=sort, limit=limit, offset=offset,
    )


@router.get("/counterparties/{buyer_key}", response_model=Page[OrderRow])
async def buyer_orders(
    buyer_key: str,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> Page[OrderRow]:
    """Every order this buyer ever touched your desk."""
    keys = _keys_or_400(scope, merchant)
    return await orders.list_orders(
        session, keys, filters=Filters(buyer_key=buyer_key), limit=limit
    )


# ─── Settlement ───────────────────────────────────────────────────────────────


@router.get("/vouchers", response_model=Page[VoucherRow])
async def list_vouchers(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    pool: str | None = Query(None),
    status: str | None = Query(None, description="issued | credited | swept | stale"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[VoucherRow]:
    """The quarantine ledger, with misroute alerts recomputed on read."""
    keys = _keys_or_400(scope, merchant)
    return await cases.list_vouchers(
        session, keys, pool=pool, status=status, limit=limit, offset=offset
    )


# ─── Freeze cases ─────────────────────────────────────────────────────────────


@router.get("/liens", response_model=Page[LienRow])
async def list_liens(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[LienRow]:
    keys = _keys_or_400(scope, merchant)
    return await cases.list_liens(session, keys, status=status, limit=limit, offset=offset)


@router.post("/liens", response_model=LienCaseFile, status_code=201)
async def create_lien(
    req: LienCreateRequest,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
) -> LienCaseFile:
    """Open a freeze case and pull the evidence pack that answers it.

    ``merchant_id`` comes from the session, never from the body, so a case can
    only ever be filed into the caller's own ledger.
    """
    keys = _keys_or_400(scope, merchant)
    notice = LienNotice(
        order_id=req.order_id,
        utr=req.utr,
        account_no_masked=req.account_no_masked,
        source=req.source,
        notice_text=req.notice_text,
    )
    result = await lien_intake.open_case(notice, merchant_id=keys[0])
    row = await cases.get_lien(session, (keys[0],), result["case"]["case_ref"])
    if row is None:  # pragma: no cover - the case was just written
        raise HTTPException(status_code=500, detail="freeze case was created but could not be read back")
    missing: list[str] = []
    if not result["assembled"]:
        missing.append(
            "No stored evidence pack for this order. Either it predates your Sentinel "
            "connection or the gate was never called for it."
        )
    return LienCaseFile(
        case=row,
        assembled=bool(result["assembled"]),
        evidence_markdown=result["evidence_markdown"],
        missing=missing,
    )


@router.patch("/liens/{case_ref}", response_model=LienRow)
async def update_lien(
    case_ref: str,
    req: LienUpdateRequest,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
) -> LienRow:
    """Move a case across the board: open → awaiting_bank → submitted → lifted."""
    keys = _keys_or_400(scope, None)
    if req.status not in cases.LIEN_STATUSES:
        raise HTTPException(status_code=400, detail="status must be one of " + ", ".join(cases.LIEN_STATUSES))
    row = await cases.update_lien(session, keys, case_ref, req.status, req.note)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no freeze case '{case_ref}' in your workspace")
    return row


# ─── Compliance and aggregates ────────────────────────────────────────────────


@router.get("/compliance-events", response_model=Page[ComplianceRow])
async def list_compliance(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    event_type: str | None = Query(None, description="STR_CONTEXT | TDS_194S | KYC_RETENTION"),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[ComplianceRow]:
    """Advisory register. Sentinel records reportable events; it does not file them."""
    keys = _keys_or_400(scope, merchant)
    return await cases.list_compliance(
        session, keys, event_type=event_type, start=_naive(since), end=_naive(until),
        limit=limit, offset=offset,
    )


@router.get("/stats/summary", response_model=StatsSummary)
async def stats_summary(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    window: str = Query("today", description="today | 24h | 7d | 30d | all"),
) -> StatsSummary:
    keys = _keys_or_400(scope, merchant)
    return await aggregates.summary(session, keys, window=window)


@router.get("/insights", response_model=OverviewResponse)
async def insights(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    window: str = Query("7d"),
) -> OverviewResponse:
    """Rules, providers, cost and mix — the tuning screen."""
    keys = _keys_or_400(scope, merchant)
    return await aggregates.overview(session, keys, window=window)


@router.get("/overview", response_model=OverviewResponse)
async def overview(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None),
    window: str = Query("today"),
) -> OverviewResponse:
    """Everything the dashboard's first screen needs, in one consistent snapshot."""
    keys = _keys_or_400(scope, merchant)
    return await aggregates.overview(session, keys, window=window)


# ─── Live feed ────────────────────────────────────────────────────────────────


def _feed_event(record: P2POrderRecord) -> str:
    payload = {
        "id": record.id,
        "order_id": record.order_id,
        "merchant_id": record.merchant_id,
        "phase": record.phase,
        "verdict": record.verdict,
        "action": record.action,
        "risk_score": record.risk_score,
        "confidence": record.confidence,
        "inr_value": record.inr_value,
        "asset": record.asset,
        "qty": record.qty,
        "buyer_user": record.buyer_user,
        "buyer_name": record.buyer_name,
        "utr": record.utr,
        "hard_rules": record.hard_rules or [],
        "reasons": record.reasons or [],
        "degraded": bool(record.degraded),
        "evidence_ref": record.evidence_ref,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
    }
    return f"data: {json.dumps(payload, default=str)}\n\n"


@router.get("/feed")
async def decision_feed(
    request: Request,
    scope: AccessScope = Depends(get_scope),
    merchant: str | None = Query(None),
    after_id: int | None = Query(
        None,
        ge=0,
        description="Resume after this decision id. Omit to start at the newest; send 0 to replay the backlog.",
    ),
    poll_seconds: float = Query(1.5, ge=0.2, le=30),
    max_events: int = Query(0, ge=0, description="Stop after N events; 0 means unbounded"),
    once: bool = Query(False, description="Replay the backlog and close (polling fallback)"),
):
    """Server-Sent Events stream of decisions as they land.

    A cursor over the primary key, polled from the ledger, rather than a Kafka
    fan-out: the portal needs to never miss or duplicate a verdict, and Postgres
    already holds the durable truth. ``once=true`` is the documented fallback for
    clients behind proxies that buffer event streams.
    """
    keys = _keys_or_400(scope, merchant)

    async def generate():
        cursor = after_id
        if cursor is None:
            async with session_factory() as session:
                cursor = await orders.latest_cursor(session, keys)
        sent = 0
        while True:
            async with session_factory() as session:
                rows = await orders.feed_after(session, keys, cursor)
            for record in rows:
                cursor = record.id
                sent += 1
                yield _feed_event(record)
            if once:
                break
            if max_events and sent >= max_events:
                break
            if await request.is_disconnected():
                break
            if not rows:
                yield ": ping\n\n"
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
