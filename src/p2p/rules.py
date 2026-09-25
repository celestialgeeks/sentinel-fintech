"""P2P-specific risk rules.

Combines vendor screening verdicts (mule / wallet / sanctions / name-match)
with behavioral signals derived from durable state (velocity, structuring,
repeat-counterparty trust) and the order itself. Produces weighted rule hits plus
a behavioural score that the fusion layer blends with the vendor max-risk.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.gateway.schemas import P2POrder
from src.screening.schemas import CounterpartyScreening, ProviderCategory

# Deal red-flag keywords seen in Indian P2P fraud chats (lowercased match).
_CHAT_REDFLAGS = [
    "urgent", "send from", "different account", "my friend paid", "brother paid",
    "wife paid", "cash back", "refund", "extra amount", "over pay", "overpay",
    "whatsapp me", "outside binance", "off platform", "payment done screenshot",
]

RELEASE_RISK = 50_000  # INR above which amount-deviation starts to matter


@dataclass
class P2pRuleHit:
    name: str
    weight: float
    triggered: bool
    hard: bool = False
    detail: str = ""


def _max_cat(screening: CounterpartyScreening, category: ProviderCategory) -> float:
    vals = [v.risk for v in screening.by_category(category) if v.status.value == "ok"]
    return max(vals, default=0.0)


def evaluate(
    order: P2POrder,
    screening: CounterpartyScreening,
    trust: dict,
    recent_hour: list[tuple[float, float]],
    now: float | None = None,
) -> tuple[list[P2pRuleHit], float]:
    """Return (rule_hits, behavioural_score 0..1)."""
    now = now or time.time()
    hits: list[P2pRuleHit] = []

    # ── vendor-backed signals ────────────────────────────────────────────
    sanctions = _max_cat(screening, ProviderCategory.SANCTIONS)
    hits.append(P2pRuleHit("sanctions_hit", 1.0, sanctions >= 0.7, hard=sanctions >= 0.9,
                           detail=f"sanctions risk {sanctions:.2f}"))

    mule = _max_cat(screening, ProviderCategory.MULE)
    hits.append(P2pRuleHit("mule_account", 1.0, mule >= 0.6, hard=mule >= 0.9,
                           detail=f"mule risk {mule:.2f}"))

    wallet = _max_cat(screening, ProviderCategory.WALLET)
    hits.append(P2pRuleHit("wallet_exposure", min(1.0, wallet), wallet >= 0.5, hard=wallet >= 0.9,
                           detail=f"wallet exposure {wallet:.2f}"))

    name_risk = _max_cat(screening, ProviderCategory.NAME_MATCH)
    hits.append(P2pRuleHit("third_party_payment", 0.9, name_risk >= 0.7,
                           hard=False,  # policy in fusion turns this into a block at release-gate
                           detail=f"name-match risk {name_risk:.2f}"))

    # ── behavioural signals ──────────────────────────────────────────────
    age = order.buyer.account_age_days
    fresh = order.buyer.trade_count == 0 or (age is not None and age < 30)
    hits.append(P2pRuleHit("freshness", 0.4, fresh,
                           detail=f"trades={order.buyer.trade_count} age_days={age}"))

    vcount = len(recent_hour)
    hits.append(P2pRuleHit("velocity", min(1.0, vcount / 8.0), vcount >= 5,
                           detail=f"{vcount} orders in last hour"))

    inr_value = order.price_inr * order.qty
    total_recent = sum(a for _, a in recent_hour)
    structured = vcount >= 3 and total_recent >= RELEASE_RISK
    hits.append(P2pRuleHit("structuring", 0.5, structured,
                           detail=f"{vcount} credits totalling INR {total_recent:.0f}"))

    deviation = inr_value >= RELEASE_RISK * 4
    hits.append(P2pRuleHit("amount_deviation", 0.3, deviation, detail=f"INR {inr_value:.0f} high for channel"))

    chat = (order.buyer.chat_snippet or "").lower()
    matched_flags = [k for k in _CHAT_REDFLAGS if k in chat]
    hits.append(P2pRuleHit("deal_red_flags", 0.5, bool(matched_flags), detail=", ".join(matched_flags)))

    flagged = int(trust.get("flagged", 0))
    clean_streak = int(trust.get("clean_streak", 0))
    hits.append(P2pRuleHit("repeat_flagged", 0.6, flagged > 0, detail=f"{flagged} prior flags"))

    # A proven clean streak is a mitigating signal (reduces behavioural score).
    mitigation = 0.2 if clean_streak >= 3 else 0.0

    behavioural = min(1.0, max(0.0, sum(h.weight for h in hits if h.triggered) / 4.0 - mitigation))
    return hits, behavioural
