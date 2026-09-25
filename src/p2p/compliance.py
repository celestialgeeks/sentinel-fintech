# ruff: noqa: E501, PLC0415
"""Adjacent compliance capture (not a tax engine).

Records the data a reporting entity / CA needs later: an internal
suspicious-transaction context when the guard blocks something, and a 194S TDS
flag when a VDA transfer crosses the reporting threshold. Feature-flagged and
best-effort; it deliberately does NOT compute or file taxes.
"""

from __future__ import annotations

from src.gateway.schemas import P2POrder
from src.p2p.schemas import GuardDecision

# Section 194S: 1% TDS applies on consideration above Rs 50,000 (Rs 200,000 for
# non-salaried) on a VDA transfer. We only flag reportability here.
TDS_THRESHOLD_INR = 50_000


def evaluate_compliance(order: P2POrder, decision: GuardDecision) -> list[dict]:
    inr_value = round(order.qty * order.price_inr, 2)
    events: list[dict] = []

    if decision.verdict.value == "BLOCK":
        events.append(
            {
                "order_id": order.order_id,
                "event_type": "STR_CONTEXT",
                "amount": inr_value,
                "payload": {"reasons": decision.reasons, "hard_rules": decision.hard_rules},
            }
        )

    if inr_value >= TDS_THRESHOLD_INR:
        events.append(
            {
                "order_id": order.order_id,
                "event_type": "TDS_194S",
                "amount": inr_value,
                "payload": {"tds_rate": 0.01, "indicative_tds": round(inr_value * 0.01, 2), "advisory": True},
            }
        )

    events.append({"order_id": order.order_id, "event_type": "KYC_RETENTION", "amount": inr_value, "payload": {"buyer": order.buyer.binance_user}})
    return events


async def record_compliance(order: P2POrder, decision: GuardDecision) -> list[dict]:
    from src.p2p import store

    events = evaluate_compliance(order, decision)
    for event in events:
        await store.save_compliance(event)
    return events
