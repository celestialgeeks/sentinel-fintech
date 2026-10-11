"""Order reads: the ledger page, one order's detail, and the live feed.

``list_orders`` is the hot path the ledger screen and the CSV export both use, so
its filters are pushed into SQL (verdict, risk_score, utr are real columns) while
the evidence bundle's JSON is only read for fields nobody filters on.
"""


from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import ComplianceEvent, EvidenceBundle, OverrideNote, P2POrderRecord, SettlementVoucher, VendorCall
from src.portal import schemas as S  # noqa: N812 - short alias keeps response models readable
from src.portal.ledger.mappers import as_list, aware, order_row, red_flags, timeline, voucher_row
from src.portal.ledger.scoping import Filters, scoped

# Whitelisted sort keys: user-supplied column names never reach the ORDER BY.
_ORDER_SORTS: dict[str, Any] = {
    "decided_at": P2POrderRecord.decided_at,
    "created_at": P2POrderRecord.created_at,
    "risk_score": P2POrderRecord.risk_score,
    "confidence": P2POrderRecord.confidence,
    "inr_value": P2POrderRecord.inr_value,
    "verdict": P2POrderRecord.verdict,
}


async def enrich(
    session: AsyncSession, records: Sequence[P2POrderRecord]
) -> tuple[dict[str, SettlementVoucher], dict[tuple[str, str], tuple[float, int]]]:
    """Fetch vouchers and per-gate vendor cost/latency for a page of records.

    Keyed on ``(order_id, phase)``: an order screened at both gates spent money
    twice, and a ledger row that reports the other gate's cost is simply wrong.
    """
    ids = [rec.order_id for rec in records]
    if not ids:
        return {}, {}
    vouchers = (
        await session.execute(select(SettlementVoucher).where(SettlementVoucher.order_id.in_(ids)))
    ).scalars().all()
    by_order = {v.order_id: v for v in vouchers}
    agg = (
        await session.execute(
            select(
                VendorCall.order_id,
                VendorCall.phase,
                func.sum(VendorCall.cost_usd),
                func.max(VendorCall.latency_ms),
            )
            .where(VendorCall.order_id.in_(ids))
            .group_by(VendorCall.order_id, VendorCall.phase)
        )
    ).all()
    costs = {(order_id, phase): (float(total or 0.0), int(latency or 0)) for order_id, phase, total, latency in agg}
    return by_order, costs


async def list_orders(
    session: AsyncSession,
    keys: Sequence[str],
    *,
    filters: Filters | None = None,
    sort: str = "decided_at",
    desc: bool = True,
    limit: int = 25,
    offset: int = 0,
) -> S.Page[S.OrderRow]:
    """The transaction-history ledger, filtered and paginated."""
    conds = (filters or Filters()).conditions()
    total = (
        await session.execute(scoped(select(func.count()).select_from(P2POrderRecord), keys).where(*conds))
    ).scalar_one()

    column = _ORDER_SORTS.get(sort, P2POrderRecord.decided_at)
    stmt = scoped(select(P2POrderRecord), keys).where(*conds).order_by(column.desc() if desc else column.asc())
    records = (await session.execute(stmt.limit(limit).offset(offset))).scalars().all()
    vouchers, costs = await enrich(session, records)

    items = [
        order_row(rec, vouchers.get(rec.order_id), *costs.get((rec.order_id, rec.phase), (0.0, 0))) for rec in records
    ]
    return S.Page[S.OrderRow](
        items=items, total=int(total), limit=limit, offset=offset, has_more=(offset + len(items)) < int(total)
    )


async def totals_for(
    session: AsyncSession, keys: Sequence[str], conds: Sequence[Any]
) -> dict[str, float]:
    """Aggregate header above the ledger: it must move when filters change."""
    row = (
        await session.execute(
            scoped(
                select(
                    func.count().label("orders"),
                    func.sum(case((P2POrderRecord.verdict == "BLOCK", P2POrderRecord.inr_value), else_=0.0)),
                    func.avg(P2POrderRecord.risk_score),
                ).where(*conds),
                keys,
            )
        )
    ).one()
    return {"orders": float(row[0] or 0), "inr_blocked": float(row[1] or 0.0), "avg_risk": float(row[2] or 0.0)}


async def get_record(
    session: AsyncSession, keys: Sequence[str], order_id: str
) -> tuple[P2POrderRecord | None, str | None]:
    """The newest gate row for an order, plus a 404 reason if it is out of scope."""
    rows = (
        await session.execute(
            scoped(select(P2POrderRecord).where(P2POrderRecord.order_id == order_id), keys)
            .order_by(P2POrderRecord.id.desc())
        )
    ).scalars().all()
    if rows:
        return rows[0], None
    any_merchant = (
        await session.execute(select(P2POrderRecord).where(P2POrderRecord.order_id == order_id).limit(1))
    ).scalar()
    return None, ("order exists but belongs to another merchant" if any_merchant else "unknown order id")


async def gate_rows(session: AsyncSession, order_id: str) -> list[P2POrderRecord]:
    """Both gates for one order, oldest first — the timeline's spine."""
    rows = (
        await session.execute(
            select(P2POrderRecord).where(P2POrderRecord.order_id == order_id).order_by(P2POrderRecord.id.asc())
        )
    ).scalars().all()
    return list(rows)


async def order_detail(session: AsyncSession, keys: Sequence[str], order_id: str) -> S.OrderDetail | None:
    """Everything the order-detail screen needs, assembled from five tables."""
    record, _reason = await get_record(session, keys, order_id)
    if record is None:
        return None

    calls = (
        await session.execute(
            select(VendorCall)
            .where(VendorCall.order_id == order_id, VendorCall.phase == record.phase)
            .order_by(VendorCall.id.asc())
        )
    ).scalars().all()
    bundle_row = (
        await session.execute(
            select(EvidenceBundle)
            .where(EvidenceBundle.order_id == order_id, EvidenceBundle.merchant_id.in_(list(keys)))
            .order_by(EvidenceBundle.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    voucher = (
        await session.execute(
            select(SettlementVoucher).where(SettlementVoucher.order_id == order_id)
        )
    ).scalar_one_or_none()
    events = (
        await session.execute(
            select(ComplianceEvent)
            .where(ComplianceEvent.order_id == order_id, ComplianceEvent.phase == record.phase)
            .order_by(ComplianceEvent.id.asc())
        )
    ).scalars().all()
    overrides = (
        await session.execute(
            select(OverrideNote)
            .where(OverrideNote.order_id == order_id, OverrideNote.merchant_key.in_(list(keys)))
            .order_by(OverrideNote.id.asc())
        )
    ).scalars().all()

    payload: dict[str, Any] = dict(bundle_row.payload or {}) if bundle_row else {}
    buyer_raw = payload.get("buyer") or {}
    payment_raw = payload.get("payment") or {}
    wallet_raw = payload.get("wallet") or {}
    decision_raw = payload.get("decision") or {}
    reasons = as_list(record.reasons)

    ok_risks = [call.risk for call in calls if call.status == "ok"]
    step_up = as_list(record.step_up)

    worst_latency = max((call.latency_ms for call in calls), default=0)
    order_block = order_row(record, voucher, sum(call.cost_usd for call in calls), worst_latency)
    gates = await gate_rows(session, order_id)
    timeline_nodes = timeline(gates, list(calls), voucher, payload, bundle_row)

    return S.OrderDetail(
        order=order_block,
        decision=S.DecisionBlock(
            verdict=record.verdict,
            action=record.action,
            risk_score=record.risk_score,
            confidence=record.confidence,
            hard_rules=as_list(record.hard_rules),
            reasons=reasons,
            evidence=as_list(decision_raw.get("evidence")),
            step_up=step_up,
            behavioural_score=record.behavioural_score,
            vendor_max_risk=max(ok_risks, default=0.0),
            composite=record.risk_score,
            degraded=bool(record.degraded),
            decided_at=aware(record.decided_at),
        ),
        buyer=S.BuyerBlock(
            binance_user=record.buyer_user,
            verified_name=record.buyer_name or buyer_raw.get("verified_name"),
            country=record.buyer_country,
            trade_count=int(buyer_raw.get("trade_count") or 0),
            completion_rate=float(buyer_raw.get("completion_rate") or 0.0),
            account_age_days=buyer_raw.get("account_age_days"),
            chat_red_flags=red_flags(reasons),
        ),
        payment=S.PaymentBlock(
            method=record.payment_method or payment_raw.get("method"),
            utr=record.utr or payment_raw.get("utr"),
            vpa=record.vpa or payment_raw.get("vpa"),
            account_no_masked=record.account_no_masked or payment_raw.get("account_no_masked"),
            ifsc=payment_raw.get("ifsc"),
            bank_name=payment_raw.get("bank_name"),
            payer_name_on_account=record.payer_name or payment_raw.get("payer_name_on_account"),
            amount=payment_raw.get("amount"),
            confirmed=bool(record.credit_confirmed or payment_raw.get("confirmed")),
        ),
        wallet=S.WalletBlock(
            chain=wallet_raw.get("chain"),
            deposit_address=wallet_raw.get("deposit_address"),
            withdrawal_address=wallet_raw.get("withdrawal_address"),
            exchange=wallet_raw.get("exchange"),
        ) if wallet_raw else None,
        vendor_calls=[
            S.VendorCallRow(
                provider=call.provider,
                category=call.category,
                status=call.status,
                risk=call.risk,
                cost_usd=call.cost_usd,
                latency_ms=call.latency_ms,
            )
            for call in calls
        ],
        evidence=S.EvidenceMeta(
            reference=bundle_row.reference,
            phase=bundle_row.phase,
            verdict=bundle_row.verdict,
            created_at=aware(bundle_row.created_at),
            download_path=f"/api/v1/portal/orders/{order_id}/evidence",
        ) if bundle_row else None,
        voucher=voucher_row(voucher) if voucher else None,
        compliance=[
            S.ComplianceRow(
                event_type=event.event_type,
                order_id=event.order_id,
                amount=event.amount,
                created_at=aware(event.created_at) or event.created_at,
                payload=dict(event.payload or {}),
            )
            for event in events
        ],
        overrides=[
            S.OverrideRow(
                actor_email=note.actor_email,
                action=note.action,
                from_verdict=note.from_verdict,
                reason=note.reason,
                created_at=aware(note.created_at) or note.created_at,
            )
            for note in overrides
        ],
        timeline=timeline_nodes,
        not_screened=False,
    )


async def feed_after(
    session: AsyncSession, keys: Sequence[str], after_id: int, limit: int = 50
) -> list[P2POrderRecord]:
    """Decisions newer than ``after_id``, oldest first, for the live feed.

    The cursor is the row's primary key rather than a timestamp: two gates can
    decide in the same millisecond, and a ledger that skips or repeats a verdict
    on refresh is worse than one that polls a little too often.
    """
    rows = (
        await session.execute(
            scoped(
                select(P2POrderRecord).where(P2POrderRecord.id > after_id),
                keys,
            )
            .order_by(P2POrderRecord.id.asc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def latest_cursor(session: AsyncSession, keys: Sequence[str]) -> int:
    """Highest decision id today, so a fresh client starts at the edge."""
    value = (
        await session.execute(scoped(select(func.max(P2POrderRecord.id)), keys))
    ).scalar()
    return int(value or 0)


async def order_bounds(session: AsyncSession, keys: Sequence[str]) -> tuple[int, datetime | None, datetime | None]:
    """Count, first and last decision — the integration wizard's connected check."""
    row = (
        await session.execute(
            scoped(
                select(func.count(), func.min(P2POrderRecord.decided_at), func.max(P2POrderRecord.decided_at)),
                keys,
            ).where(P2POrderRecord.decided_at.is_not(None))
        )
    ).one()
    return int(row[0] or 0), aware(row[1]), aware(row[2])
