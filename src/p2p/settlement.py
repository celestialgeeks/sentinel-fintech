# ruff: noqa: PLC0415
"""Settlement isolation.

The freeze reaches the merchant through a *specific* INR credit. Issuing a
per-order virtual voucher so the credit is individually UTR-traceable lets a
single tainted payment be contained (and evidenced) without paralysing the
operating float. These helpers build the mapping and the sweep-delay timer;
persistence is best-effort via :mod:`src.p2p.store`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from src.gateway.schemas import P2POrder
from src.p2p.schemas import GuardDecision

# Keep suspect/clean funds quarantined for a complaint-window before sweeping.
SWEEP_DELAY_HOURS = 48


def _voucher_ref(order_id: str) -> str:
    return "VCH-" + hashlib.sha256(order_id.encode()).hexdigest()[:10].upper()


def build_voucher(order: P2POrder, decision: GuardDecision) -> dict:
    """Issue a quarantine voucher mapped to the order's expected credit."""
    now = datetime.now(UTC)
    clean = decision.verdict.value == "ALLOW"
    return {
        "order_id": order.order_id,
        "voucher_ref": _voucher_ref(order.order_id),
        "virtual_account": f"VA{abs(hash(order.order_id)) % (10**12):012d}",
        "vpa": f"sentinel+{order.order_id[-6:]}@okhdfcbank",
        "amount": round(order.qty * order.price_inr, 2),
        "pool": "quarantine",
        "status": "issued",
        "sweep_after": now + timedelta(hours=SWEEP_DELAY_HOURS) if clean else None,
    }


def reconcile_credit(voucher: dict, observed_utr: str | None, observed_pool: str = "quarantine") -> list[str]:
    """Return alert strings if an observed credit does not match its voucher.

    A credit that lands outside the quarantine pool (or a voucher that cannot
    be tied to a UTR) is exactly the situation that turns one bad buyer into a
    whole-account freeze, so it is surfaced loudly.
    """
    alerts: list[str] = []
    if observed_pool != "quarantine":
        alerts.append(f"credit for order {voucher['order_id']} landed in pool '{observed_pool}', not quarantine")
    if not observed_utr:
        alerts.append(f"credit for order {voucher['order_id']} has no UTR to trace")
    return alerts


async def record_voucher(order: P2POrder, decision: GuardDecision) -> dict:
    from src.p2p import store

    voucher = build_voucher(order, decision)
    await store.save_voucher(voucher)
    return voucher
