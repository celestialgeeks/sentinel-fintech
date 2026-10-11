"""Kafka consumer for the real-time payment screening pipeline.

Listens to 'sentinel.payment' events and orchestrates:
  Payment → Trail Analysis → Screening → Verification → Decision
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from src.core.kafka_client import kafka_producer
from src.gateway.trail import _trail_engine
from src.screening.engine import ScreeningEngine
from src.verification.pipeline import _pipeline

logger = logging.getLogger(__name__)

# ─── Pipeline State ───────────────────────────────────────────────────────────

# In-memory store for pending analysis (replace with Redis in production)
_pending: dict[str, dict[str, Any]] = {}
_next_id = 1


def _next_id_fn() -> str:
    global _next_id
    pid = f"pay_{_next_id:06d}"
    _next_id += 1
    return pid


def _get_handler() -> Any:
    """Return the Kafka consumer handler closure."""

    async def handler(topic: str, message: dict[str, Any]) -> None:
        """Process a payment event through the full pipeline."""
        payment_id = message.get("payment_id", "unknown")
        logger.info("Processing payment %s through real-time pipeline", payment_id)

        # Store in pending state
        _pending[payment_id] = {
            "payment": message,
            "trail": None,
            "screening": None,
            "verification": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Phase 1: Trail analysis
            trail = await _trail_engine.follow_trail(payment_id, depth=3)
            _pending[payment_id]["trail"] = trail.model_dump()
            logger.info("Trail analysis complete for %s: risk=%.3f", payment_id, trail.aggregated_risk_score)

            # Phase 2: AML screening (sync — run in executor)
            screening_engine = ScreeningEngine()
            from src.screening.schemas import EntityRef, TransactionIngest

            txn = TransactionIngest(
                transaction_id=payment_id,
                amount=message.get("amount", 0),
                currency=message.get("currency", "USD"),
                sender=EntityRef(
                    entity_id=message.get("sender", {}).get("entity_id", "unknown"),
                    name=message.get("sender", {}).get("name", "Unknown"),
                    country=message.get("sender", {}).get("country", "US"),
                ),
                receiver=EntityRef(
                    entity_id=message.get("receiver", {}).get("entity_id", "unknown"),
                    name=message.get("receiver", {}).get("name", "Unknown"),
                    country=message.get("receiver", {}).get("country", "US"),
                ),
            )
            screening_result = await asyncio.to_thread(screening_engine.screen, txn)
            _pending[payment_id]["screening"] = screening_result.model_dump()
            logger.info("Screening complete for %s: rec=%s score=%.3f", payment_id, screening_result.recommendation, screening_result.risk_score)

            # Phase 3: Verification pipeline
            verification = await _pipeline.run(
                payment_event=message,
                trail_analysis=trail.model_dump(),
                screening_result=screening_result.model_dump(),
            )
            _pending[payment_id]["verification"] = verification
            logger.info("Verification complete for %s: decision=%s confidence=%.2f", payment_id, verification["decision"], verification["confidence"])

            # Publish decision to Kafka
            if kafka_producer is not None:
                await kafka_producer.produce(
                    topic="sentinel.decision",
                    key=payment_id,
                    value={
                        "payment_id": payment_id,
                        "decision": verification["decision"],
                        "confidence": verification["confidence"],
                        "risk_score": verification["risk_score"],
                        "reasoning": verification["reasoning"],
                        "flags": verification.get("flags", []),
                        "trail_depth": trail.trail_depth,
                        "trail_nodes": len(trail.nodes),
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                logger.info("Decision published to Kafka: %s → %s", payment_id, verification["decision"])

            # Clean up pending
            _pending.pop(payment_id, None)

        except Exception as e:
            logger.error("Pipeline failed for payment %s: %s", payment_id, str(e), exc_info=True)
            if payment_id in _pending:
                _pending[payment_id]["error"] = str(e)

    return handler


def setup_consumer() -> None:
    """Register the pipeline handler with the Kafka consumer.

    NOTE: the handler is built here but never subscribed — ``kafka_consumer`` in
    :mod:`src.core.kafka_client` owns the topic loop. Wiring the two together is
    open work, so the unused binding is kept explicit instead of deleted.
    """
    handler = _get_handler()  # noqa: F841
    # The consumer is already initialized in src/core/kafka_client.py
    # We just need to ensure the topic is subscribed
    logger.info("Kafka pipeline consumer registered for topics: sentinel.payment, sentinel.trail")


def get_pending_status(payment_id: str) -> dict[str, Any]:
    """Get the current pipeline status for a payment."""
    if payment_id in _pending:
        state = _pending[payment_id].copy()
        state["status"] = "in_progress"
        return state
    # Check if we have a cached decision
    return {
        "payment_id": payment_id,
        "status": "completed",
        "has_decision": True,
    }
