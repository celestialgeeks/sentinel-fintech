"""Pure shaping of ORM rows into portal response models.

No session, no SQL: everything here is a function of the row it is handed, which
is why the ledger router and the aggregates can share it without either owning
the other. Times are normalised to aware UTC by :func:`aware` so a client never
has to guess the offset of a 15-minute release window.
"""


from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from src.core.models import EvidenceBundle, LienCase, P2POrderRecord, SettlementVoucher, VendorCall
from src.portal import schemas as S  # noqa: N812 - short alias keeps response models readable


def aware(value: datetime | None) -> datetime | None:
    """Stamp UTC onto naive column values so the API always emits an offset.

    The guard stores naive UTC (see :func:`src.p2p.store._naive_utc`); without
    this a client would have to guess whether ``2026-09-25T19:02:43`` is the
    merchant's local time, which for a 15-minute release window is a real bug.
    """
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def as_list(value: Any) -> list[str]:
    """JSON columns may hold null or a non-list; the UI always wants a list."""
    return list(value) if isinstance(value, (list, tuple)) else []


def red_flags(reasons: Sequence[str]) -> list[str]:
    """Extract the matched chat phrases from a ``deal_red_flags`` reason."""
    for reason in reasons:
        if reason.startswith("deal_red_flags:"):
            tail = reason.split(":", 1)[1].strip()
            return [piece.strip() for piece in tail.split(",") if piece.strip()]
    return []


def order_row(
    rec: P2POrderRecord,
    voucher: SettlementVoucher | None = None,
    spend_usd: float = 0.0,
    latency_ms: int = 0,
) -> S.OrderRow:
    reasons = as_list(rec.reasons)
    return S.OrderRow(
        order_id=rec.order_id,
        merchant_id=rec.merchant_id,
        decided_at=aware(rec.decided_at),
        created_at=aware(rec.created_at) or rec.created_at,
        phase=rec.phase,
        asset=rec.asset,
        fiat=rec.fiat,
        qty=rec.qty,
        price_inr=rec.price_inr,
        inr_value=rec.inr_value,
        buyer_user=rec.buyer_user,
        buyer_name=rec.buyer_name,
        buyer_country=rec.buyer_country,
        verdict=rec.verdict,
        action=rec.action,
        risk_score=rec.risk_score,
        confidence=rec.confidence,
        hard_rules=as_list(rec.hard_rules),
        reasons=reasons,
        degraded=bool(rec.degraded),
        evidence_ref=rec.evidence_ref,
        voucher_ref=voucher.voucher_ref if voucher else None,
        pool=voucher.pool if voucher else None,
        voucher_status=voucher.status if voucher else None,
        utr=rec.utr,
        payer_name=rec.payer_name,
        account_no_masked=rec.account_no_masked,
        payment_method=rec.payment_method,
        spend_usd=float(spend_usd or 0.0),
        latency_ms=int(latency_ms or 0),
        rules_total=len(reasons),
    )


def voucher_row(voucher: SettlementVoucher) -> S.VoucherRow:
    return S.VoucherRow(
        voucher_ref=voucher.voucher_ref,
        order_id=voucher.order_id,
        virtual_account=voucher.virtual_account,
        vpa=voucher.vpa,
        utr=voucher.utr,
        amount=voucher.amount,
        pool=voucher.pool,
        status=voucher.status,
        credited_at=aware(voucher.credited_at),
        sweep_after=aware(voucher.sweep_after),
        alerts=voucher_alerts(voucher),
    )


def voucher_alerts(voucher: SettlementVoucher) -> list[str]:
    """Re-derive the misroute alerts the guard would have raised at release."""
    alerts: list[str] = []
    if voucher.pool != "quarantine":
        alerts.append(f"credit for order {voucher.order_id} landed in pool '{voucher.pool}', not quarantine")
    if not voucher.utr:
        alerts.append(f"credit for order {voucher.order_id} has no UTR to trace")
    return alerts


def timeline(
    gates: Sequence[P2POrderRecord],
    calls: list[VendorCall],
    voucher: SettlementVoucher | None,
    payload: dict[str, Any],
    bundle: EvidenceBundle | None,
) -> list[S.TimelineNode]:
    """Order lifecycle with whatever timestamps each stage actually left.

    Every gate the order passed gets its own node: the two-gate design is the
    product, so a timeline that shows only the newest decision hides the point.
    """
    newest = gates[-1]
    nodes: list[S.TimelineNode] = []
    order_created = (payload.get("order") or {}).get("created_at")
    nodes.append(S.TimelineNode(name="order_created", at=coerce_dt(order_created) or newest.created_at))
    for gate in gates:
        nodes.append(
            S.TimelineNode(
                name=f"guard_{gate.phase}",
                at=coerce_dt(gate.decided_at),
                detail=f"{gate.verdict} ({gate.action}) risk {gate.risk_score:.2f}",
            )
        )
    if voucher:
        nodes.append(
            S.TimelineNode(
                name="voucher_issued",
                at=coerce_dt(voucher.created_at),
                detail=f"{voucher.voucher_ref} pool={voucher.pool}",
            )
        )
    if voucher and voucher.credited_at:
        nodes.append(
            S.TimelineNode(name="credit_observed", at=coerce_dt(voucher.credited_at), detail=voucher.utr or "")
        )
    if calls:
        first = coerce_dt(calls[0].created_at)
        nodes.append(
            S.TimelineNode(
                name="vendor_fanout",
                at=first,
                detail=f"{len(calls)} calls, max {max(call.latency_ms for call in calls)} ms",
            )
        )
    if bundle:
        nodes.append(
            S.TimelineNode(
                name="evidence_stored",
                at=coerce_dt(bundle.created_at),
                detail=f"{bundle.reference} immutable",
            )
        )
    return nodes


def coerce_dt(value: Any) -> datetime | None:
    """Accept naive/aware datetimes and ISO strings from JSON columns."""
    if isinstance(value, datetime):
        return aware(value)
    if isinstance(value, str):
        try:
            return aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def lien_row(case_row: LienCase, evidence_available: bool) -> S.LienRow:
    return S.LienRow(
        case_ref=case_row.case_ref,
        merchant_id=case_row.merchant_id,
        order_id=case_row.order_id,
        utr=case_row.utr,
        account_no_masked=case_row.account_no_masked,
        source=case_row.source,
        status=case_row.status,
        notice_text=case_row.notice_text,
        evidence_reference=case_row.evidence_reference,
        evidence_available=evidence_available,
        created_at=aware(case_row.created_at) or case_row.created_at,
        updated_at=aware(case_row.updated_at),
    )
