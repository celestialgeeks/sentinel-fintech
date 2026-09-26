# ruff: noqa: E501, PLC0415
"""Best-effort persistence for guard outcomes.

DB writes are deliberately non-fatal: a screening verdict must reach the bot
even if Postgres is temporarily unavailable. Every function imports the DB layer
lazily (so the guard package imports without SQLAlchemy in unit tests) and
swallows + logs failures. Fast-moving velocity/trust state lives in Redis
(:mod:`src.p2p.state`), not here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.gateway.schemas import GuardPhase, P2POrder
from src.p2p.schemas import GuardDecision
from src.screening.schemas import CounterpartyScreening

logger = logging.getLogger(__name__)


def _naive_utc(value: datetime | None) -> datetime | None:
    """Store timestamps as naive UTC.

    The columns are ``timestamp without time zone`` and the DB default is
    ``now()``, so writing tz-aware values would mix two clock representations in
    one column and make range filters dialect-dependent. Normalising on the way
    in keeps every stored value UTC, and the read layer re-attaches the offset
    when it renders a response.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


async def persist_outcome(  # noqa: PLR0913 - one decision's worth of inputs, all required together
    order: P2POrder,
    phase: GuardPhase,
    screening: CounterpartyScreening,
    decision: GuardDecision,
    bundle: dict | None,
    *,
    timing: dict | None = None,
) -> None:
    """Write the order record, vendor calls and evidence bundle in one session.

    Re-running a gate for the same order (clearing a HOLD, replaying a Kafka
    message) must update the ledger row rather than collide with it: the row is
    "this order at this gate, as last decided", while every individual decision
    keeps its own evidence bundle for history.
    """
    try:
        from sqlalchemy import select

        from src.core.db import session_factory
        from src.core.models import (
            Counterparty,
            EvidenceBundle,
            P2POrderRecord,
            VendorCall,
        )

        async with session_factory() as session:
            existing = (
                await session.execute(
                    select(P2POrderRecord).where(
                        P2POrderRecord.order_id == order.order_id, P2POrderRecord.phase == phase.value
                    )
                )
            ).scalar_one_or_none()
            fields = {
                "merchant_id": order.merchant_id,
                "asset": order.asset,
                "fiat": order.fiat,
                "qty": order.qty,
                "price_inr": order.price_inr,
                "inr_value": order.qty * order.price_inr,
                "buyer_user": order.buyer.binance_user,
                "buyer_name": order.buyer.verified_name,
                "buyer_country": order.buyer.country,
                "verdict": decision.verdict.value,
                "action": decision.action,
                "risk_score": decision.risk_score,
                "confidence": decision.confidence,
                "hard_rules": decision.hard_rules,
                "reasons": decision.reasons,
                "step_up": decision.step_up,
                "behavioural_score": decision.behavioural_score,
                "evidence_ref": decision.evidence_ref,
                "payment_method": order.payment.method.value if order.payment else None,
                "payer_name": order.payment.payer_name_on_account if order.payment else None,
                "account_no_masked": order.payment.account_no_masked if order.payment else None,
                "vpa": order.payment.vpa if order.payment else None,
                "utr": order.payment.utr if order.payment else None,
                "credit_confirmed": bool(order.payment.confirmed) if order.payment else False,
                "degraded": decision.degraded,
                "decided_at": _naive_utc(decision.decided_at),
            }
            if existing is None:
                session.add(
                    P2POrderRecord(order_id=order.order_id, phase=phase.value, **fields)
                )
            else:
                for key, value in fields.items():
                    setattr(existing, key, value)
            for v in screening.verdicts:
                session.add(
                    VendorCall(
                        order_id=order.order_id,
                        phase=phase.value,
                        provider=v.provider,
                        category=v.category.value,
                        status=v.status.value,
                        risk=v.risk,
                        cost_usd=v.cost_usd,
                        # The adapter's own number when it has one, otherwise the
                        # wall-clock the fan-out actually took (mocks report 0).
                        latency_ms=v.latency_ms or int((timing or {}).get("_fanout_ms", 0)),
                    )
                )
            if bundle:
                session.add(
                    EvidenceBundle(
                        reference=bundle["reference"],
                        order_id=order.order_id,
                        merchant_id=order.merchant_id,
                        phase=phase.value,
                        verdict=decision.verdict.value,
                        payload=bundle,
                    )
                )
            await _upsert_counterparty(session, Counterparty, order, decision)
            await session.commit()
    except Exception:  # noqa: BLE001 - persistence is best-effort
        logger.warning("persist_outcome failed for %s", order.order_id, exc_info=True)


async def _upsert_counterparty(session, model, order: P2POrder, decision: GuardDecision) -> None:
    from sqlalchemy import select

    buyer_key = order.buyer.binance_user or order.buyer.verified_name
    existing = (await session.execute(select(model).where(model.buyer_key == buyer_key))).scalar_one_or_none()
    flagged = decision.verdict.value == "BLOCK"
    if existing is None:
        existing = model(buyer_key=buyer_key, binance_user=order.buyer.binance_user, verified_name=order.buyer.verified_name, seen=0, flagged=0, clean_streak=0)
        session.add(existing)
    existing.seen = (existing.seen or 0) + 1
    existing.flagged = (existing.flagged or 0) + (1 if flagged else 0)
    existing.clean_streak = 0 if flagged else (existing.clean_streak or 0) + 1
    existing.last_risk = decision.risk_score
    existing.last_verdict = decision.verdict.value
    existing.last_seen_at = _naive_utc(datetime.now(UTC))


async def save_voucher(voucher: dict) -> None:
    """Insert or refresh the voucher for an order (one voucher per order)."""
    try:
        from sqlalchemy import select

        from src.core.db import session_factory
        from src.core.models import SettlementVoucher

        async with session_factory() as session:
            existing = (
                await session.execute(
                    select(SettlementVoucher).where(SettlementVoucher.order_id == voucher["order_id"])
                )
            ).scalar_one_or_none()
            if existing is None:
                session.add(SettlementVoucher(**voucher))
            else:
                for key, value in voucher.items():
                    if key != "order_id":
                        setattr(existing, key, value)
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("save_voucher failed", exc_info=True)


async def save_lien(case: dict) -> None:
    """Insert or refresh a freeze case.

    ``case_ref`` is derived from the notice's own identifiers, so the same bank
    email arriving twice is the same case — forwarding it again should update it,
    not silently fail a UNIQUE constraint and leave the caller holding a case
    reference that was never written.
    """
    try:
        from sqlalchemy import select

        from src.core.db import session_factory
        from src.core.models import LienCase

        async with session_factory() as session:
            existing = (
                await session.execute(select(LienCase).where(LienCase.case_ref == case["case_ref"]))
            ).scalar_one_or_none()
            if existing is None:
                session.add(LienCase(**case))
            else:
                for key, value in case.items():
                    if key != "case_ref":
                        setattr(existing, key, value)
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("save_lien failed", exc_info=True)


async def save_compliance(event: dict) -> None:
    try:
        from src.core.db import session_factory
        from src.core.models import ComplianceEvent

        async with session_factory() as session:
            session.add(ComplianceEvent(**event))
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("save_compliance failed", exc_info=True)


async def get_evidence(order_id: str) -> dict | None:
    """Return the most recent evidence bundle payload for an order, if any."""
    try:
        from sqlalchemy import select

        from src.core.db import session_factory
        from src.core.models import EvidenceBundle

        async with session_factory() as session:
            row = (
                await session.execute(
                    select(EvidenceBundle)
                    .where(EvidenceBundle.order_id == order_id)
                    .order_by(EvidenceBundle.id.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            return row.payload if row else None
    except Exception:  # noqa: BLE001
        logger.warning("get_evidence failed for %s", order_id, exc_info=True)
        return None
