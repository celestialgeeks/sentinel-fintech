# ruff: noqa: E501, PLC0415
"""P2P order-event orchestrator (Kafka path).

The merchant bot may either call the REST gates (see :mod:`src.p2p.router`) or
publish order events to ``sentinel.p2p.order``. This module is the second path:
an idempotent handler that drives the exact same ``guard_order`` pipeline and,
if a release is approved, the decision is published to ``sentinel.p2p.decision``
for the bot to act on.

The shared Kafka consumer invokes handlers synchronously on a worker thread, so
we bridge onto a dedicated asyncio loop rather than the API's loop; this keeps
long vendor calls from blocking the web app.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from src.gateway.schemas import GuardPhase, P2POrder
from src.p2p.pipeline import guard_order

logger = logging.getLogger(__name__)

_seen: set[tuple[str, str]] = set()
_lock = threading.Lock()

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    if _loop is None:
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(target=_loop.run_forever, daemon=True)
        _thread.start()
    return _loop


def _idempotency_key(message: dict[str, Any]) -> tuple[str, str]:
    payment = message.get("payment") or {}
    return (message.get("order_id", "unknown"), payment.get("utr", ""))


async def process_order_event(message: dict[str, Any], *, persist: bool = True, publish: bool = True) -> dict[str, Any] | None:
    """Run one P2P order event through the guard. Re-delivery safe."""
    key = _idempotency_key(message)
    with _lock:
        if key in _seen:
            logger.info("skipping duplicate p2p order event %s", key)
            return None
        _seen.add(key)

    order = P2POrder.model_validate(message)
    phase = GuardPhase(message.get("_phase", "release_gate" if order.payment else "pre_screen"))
    decision = await guard_order(order, phase, persist=persist, publish=publish)
    return decision.model_dump(mode="json")


def _sync_handler(topic: str, payload: dict[str, Any]) -> None:
    try:
        fut = asyncio.run_coroutine_threadsafe(process_order_event(payload), _get_loop())
        fut.result(timeout=30)
    except Exception:  # noqa: BLE001 - consumer must keep running
        logger.error("p2p order handler failed on %s", topic, exc_info=True)


def start() -> None:
    """Subscribe to sentinel.p2p.order if Kafka libs are present."""
    try:
        from src.shared.kafka import KafkaConsumerWrapper, KafkaSettings

        wrapper = KafkaConsumerWrapper(
            bootstrap_servers=KafkaSettings().bootstrap_servers,
            topics=["sentinel.p2p.order"],
            group_id="sentinel-p2p-guard",
            handler=_sync_handler,
        )
        wrapper.start()
        logger.info("P2P guard consumer subscribed to sentinel.p2p.order")
    except Exception:  # noqa: BLE001 - optional path
        logger.info("P2P guard Kafka consumer not started (kafka unavailable/unconfigured)")


def reset_dedupe() -> None:
    with _lock:
        _seen.clear()
