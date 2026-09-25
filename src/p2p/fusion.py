"""Decision fusion: blend vendor + behavioural signals into ALLOW / HOLD / BLOCK.

Design notes:
* Any hard-block vendor category (sanctions / confirmed mule / severe wallet)
  is an immediate BLOCK.
* A third-party payment (payer name != Binance-verified beneficiary) is a BLOCK
  at the release gate — it is the pattern most likely to freeze the merchant.
* A degraded run (a required vendor could not be reached) can never ALLOW; the
  worst it may say is HOLD, and any real risk pushes it to BLOCK.
* Otherwise a weighted blend of vendor max-risk and behavioural score is graded
  against BLOCK/REVIEW thresholds.
"""

from __future__ import annotations

from src.gateway.schemas import GuardPhase, GuardVerdict, P2POrder
from src.p2p.rules import P2pRuleHit
from src.p2p.schemas import GuardDecision
from src.screening.schemas import CounterpartyScreening

BLOCK_THRESHOLD = 0.8
HOLD_THRESHOLD = 0.5

_STEP_UP = [
    "Ask buyer for a bank statement screenshot showing the UTR and their own name.",
    "Re-confirm the credit via the Account Aggregator / bank feed (not the buyer screenshot).",
    "Hold 30 minutes and re-screen once the payer bank-account data is available.",
    "If the payer cannot prove same-person funds, reject and let the order expire.",
]

_ACTION = {
    GuardVerdict.ALLOW: "release",
    GuardVerdict.HOLD: "hold",
    GuardVerdict.BLOCK: "reject",
}


def _third_party(order: P2POrder, hits: list[P2pRuleHit]) -> bool:
    return any(h.name == "third_party_payment" and h.triggered for h in hits)


def decide(
    order: P2POrder,
    phase: GuardPhase,
    screening: CounterpartyScreening,
    hits: list[P2pRuleHit],
    behavioural: float,
) -> GuardDecision:
    hard_rules = [h.name for h in hits if h.triggered and h.hard]
    if screening.hard_block and not hard_rules:
        hard_rules.append("vendor_hard_block")

    reasons = [f"{h.name}: {h.detail}" for h in hits if h.triggered]
    evidence = [f"{v.provider}({v.category.value})={v.risk:.2f} {v.detail}" for v in screening.verdicts]

    vendor_max = screening.max_risk
    blend = 0.5 * vendor_max + 0.5 * behavioural
    composite = min(1.0, max(blend, vendor_max))

    # ── verdict ──────────────────────────────────────────────────────────
    if hard_rules:
        verdict = GuardVerdict.BLOCK
        confidence = 0.95
        reasons.insert(0, "Hard rule triggered: " + ", ".join(hard_rules))
    elif phase == GuardPhase.RELEASE_GATE and _third_party(order, hits):
        verdict = GuardVerdict.BLOCK
        confidence = 0.9
        reasons.insert(0, "Third-party payment (name mismatch) at release gate")
    elif screening.degraded:
        # Fail-closed: never ALLOW while a required vendor is unreachable.
        verdict = GuardVerdict.BLOCK if composite >= BLOCK_THRESHOLD else GuardVerdict.HOLD
        confidence = 0.6
        reasons.insert(0, "Required vendor unavailable - degraded, refusing to auto-allow")
    elif composite >= BLOCK_THRESHOLD:
        verdict = GuardVerdict.BLOCK
        confidence = round(composite, 4)
    elif composite >= HOLD_THRESHOLD:
        verdict = GuardVerdict.HOLD
        confidence = round(1.0 - abs(composite - 0.65), 4)
    else:
        verdict = GuardVerdict.ALLOW
        confidence = round(1.0 - composite, 4)

    step_up = _STEP_UP if verdict == GuardVerdict.HOLD else []

    return GuardDecision(
        order_id=order.order_id,
        merchant_id=order.merchant_id,
        phase=phase,
        verdict=verdict,
        action=_ACTION[verdict],
        risk_score=round(composite, 4),
        confidence=confidence,
        reasons=reasons,
        hard_rules=hard_rules,
        evidence=evidence,
        step_up=step_up,
        provider_verdicts=screening.verdicts,
        behavioural_score=round(behavioural, 4),
        degraded=screening.degraded,
    )
