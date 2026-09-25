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


async def persist_outcome(
    order: P2POrder,
    phase: GuardPhase,
    screening: CounterpartyScreening,
    decision: GuardDecision,
    bundle: dict | None,
) -> None:
    """Write the order record, vendor calls and evidence bundle in one session."""
    try:
        from src.shared.db import session_factory
        from src.shared.models import (
            Counterparty,
            EvidenceBundle,
            P2POrderRecord,
            VendorCall,
        )

        async with session_factory() as session:
            session.add(
                P2POrderRecord(
                    order_id=order.order_id,
                    merchant_id=order.merchant_id,
                    asset=order.asset,
                    fiat=order.fiat,
                    qty=order.qty,
                    price_inr=order.price_inr,
                    inr_value=order.qty * order.price_inr,
                    buyer_user=order.buyer.binance_user,
                    buyer_name=order.buyer.verified_name,
                    buyer_country=order.buyer.country,
                    phase=phase.value,
                    verdict=decision.verdict.value,
                    action=decision.action,
                    risk_score=decision.risk_score,
                    confidence=decision.confidence,
                    hard_rules=decision.hard_rules,
                    reasons=decision.reasons,
                    degraded=decision.degraded,
                    decided_at=decision.decided_at,
                )
            )
            for v in screening.verdicts:
                session.add(
                    VendorCall(
                        order_id=order.order_id,
                        provider=v.provider,
                        category=v.category.value,
                        status=v.status.value,
                        risk=v.risk,
                        cost_usd=v.cost_usd,
                        latency_ms=v.latency_ms,
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
    existing.last_seen_at = datetime.now(UTC)


async def save_voucher(voucher: dict) -> None:
    try:
        from src.shared.db import session_factory
        from src.shared.models import SettlementVoucher

        async with session_factory() as session:
            session.add(SettlementVoucher(**voucher))
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("save_voucher failed", exc_info=True)


async def save_lien(case: dict) -> None:
    try:
        from src.shared.db import session_factory
        from src.shared.models import LienCase

        async with session_factory() as session:
            session.add(LienCase(**case))
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("save_lien failed", exc_info=True)


async def save_compliance(event: dict) -> None:
    try:
        from src.shared.db import session_factory
        from src.shared.models import ComplianceEvent

        async with session_factory() as session:
            session.add(ComplianceEvent(**event))
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("save_compliance failed", exc_info=True)


async def get_evidence(order_id: str) -> dict | None:
    """Return the most recent evidence bundle payload for an order, if any."""
    try:
        from sqlalchemy import select

        from src.shared.db import session_factory
        from src.shared.models import EvidenceBundle

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
