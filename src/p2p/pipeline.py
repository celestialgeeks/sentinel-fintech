# ruff: noqa: E501, PLC0415
"""Guard orchestrator - one code path for both the REST gates and Kafka.

Sequence: vendor fan-out -> durable state (velocity/trust) -> rules -> fusion ->
evidence bundle -> (release-gate) bank-credit reconciliation -> (pre-screen)
quarantine voucher -> persistence + compliance capture -> publish decision.

Persistence / publish are best-effort and guarded, so the verdict is produced
even when Postgres/Kafka are down (fail toward the safer verdict, never crash).
"""

from __future__ import annotations

import logging
import time

from src.gateway.schemas import GuardPhase, GuardVerdict, P2POrder
from src.p2p import compliance, evidence, fusion, metrics, rules, settlement, store
from src.p2p.schemas import GuardDecision
from src.p2p.state import guard_state
from src.vendors.aggregator import get_aggregator

logger = logging.getLogger(__name__)


def _buyer_key(order: P2POrder) -> str:
    return (order.buyer.binance_user or order.buyer.verified_name or "anon").strip().lower()


async def guard_order(
    order: P2POrder,
    phase: GuardPhase,
    *,
    persist: bool = True,
    publish: bool = True,
) -> GuardDecision:
    screening = await get_aggregator().screen(order, phase)

    key = _buyer_key(order)
    trust = await guard_state.get_trust(key)
    recent = await guard_state.recent_activity(key, window_s=3600)

    hits, behavioural = rules.evaluate(order, screening, trust, recent)
    decision = fusion.decide(order, phase, screening, hits, behavioural)

    # Fast-moving state: record this attempt + update counterparty trust.
    await guard_state.add_activity(key, time.time(), order.qty * order.price_inr)
    await guard_state.record_outcome(key, flagged=decision.verdict == GuardVerdict.BLOCK)

    bundle = evidence.build_bundle(order, phase, screening, decision)
    decision.evidence_ref = bundle["reference"]

    # Pre-screen issues an isolated settlement voucher before money is accepted.
    if phase == GuardPhase.PRE_SCREEN:
        voucher = settlement.build_voucher(order, decision)
        decision.reasons.append(f"Settlement voucher {voucher['voucher_ref']} issued (pool={voucher['pool']}).")
        if persist:
            await store.save_voucher(voucher)

    # Release-gate reconciliation: the credit must be confirmed against its UTR.
    if phase == GuardPhase.RELEASE_GATE and order.payment is not None:
        alerts = settlement.reconcile_credit(
            {"order_id": order.order_id}, order.payment.utr,
            observed_pool="quarantine" if order.payment.confirmed else "operating",
        )
        if alerts and decision.verdict != GuardVerdict.BLOCK:
            decision.verdict = GuardVerdict.HOLD
            decision.action = "hold"
            decision.step_up = decision.step_up or ["Confirm the credit against its UTR before releasing."]
            decision.reasons.extend(alerts)

    # Observability: decision mix + per-vendor latency/spend.
    metrics.record_decision(decision.verdict.value, phase.value, decision.degraded)
    for v in screening.verdicts:
        metrics.record_vendor(v.provider, v.category.value, v.status.value, v.latency_ms, v.cost_usd)

    if persist:
        await store.persist_outcome(order, phase, screening, decision, bundle)
        await compliance.record_compliance(order, decision)

    if publish:
        await _publish(order, decision)

    logger.info(
        "guard order=%s phase=%s verdict=%s risk=%.2f confidence=%.2f degraded=%s",
        order.order_id, phase.value, decision.verdict.value, decision.risk_score, decision.confidence, decision.degraded,
    )
    return decision


async def _publish(order: P2POrder, decision: GuardDecision) -> None:
    try:
        from src.shared.kafka import kafka_producer

        if kafka_producer is None:
            return
        await kafka_producer.produce(
            topic="sentinel.p2p.decision",
            key=order.order_id,
            value={
                "order_id": order.order_id,
                "merchant_id": order.merchant_id,
                "phase": decision.phase.value,
                "verdict": decision.verdict.value,
                "action": decision.action,
                "risk_score": decision.risk_score,
                "confidence": decision.confidence,
                "hard_rules": decision.hard_rules,
                "evidence_ref": decision.evidence_ref,
                "decided_at": decision.decided_at.isoformat(),
            },
        )
    except Exception:  # noqa: BLE001 - publishing must never break the verdict
        logger.warning("publish failed for %s", order.order_id, exc_info=True)
