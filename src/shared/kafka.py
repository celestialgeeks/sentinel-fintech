"""Async Kafka producer / consumer wrapper for Sentinel event streams."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from typing import Any, Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

try:
    from confluent_kafka import Consumer, KafkaError, Producer, TopicPartition
except ImportError:  # pragma: no cover
    Consumer = None  # type: ignore
    KafkaError = None  # type: ignore
    Producer = None  # type: ignore
    TopicPartition = None  # type: ignore


class KafkaSettings(BaseSettings):
    bootstrap_servers: str = "localhost:9093"
    schema_registry_url: str = "http://localhost:8081"
    group_id: str = "sentinel"
    auto_offset_reset: str = "earliest"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# ── Producer ──────────────────────────────────────────────────────────────────

class KafkaProducerWrapper:
    """Async-safe Kafka producer with JSON serialisation."""

    def __init__(self, bootstrap_servers: str) -> None:
        self._servers = bootstrap_servers
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "compression.type": "lz4",
                "message.max.bytes": 1048576,
            }
        )
        self._dr_callback_count = 0

    def _delivery_report(self, err: Optional[KafkaError], msg: Any) -> None:
        if err:
            logger.error("Kafka delivery error: %s", str(err))
        else:
            self._dr_callback_count += 1
            logger.debug(
                "Delivered to %s [%d] offset %d",
                msg.topic(),
                msg.partition(),
                msg.offset(),
            )

    async def produce(
        self,
        topic: str,
        key: Optional[str] = None,
        value: Optional[dict[str, Any]] = None,
        headers: Optional[list[tuple[str, str]]] = None,
    ) -> None:
        """Produce a JSON-serialised event to *topic*."""
        payload = json.dumps(value, default=str).encode("utf-8") if value else None
        key_bytes = key.encode("utf-8") if key else None

        self._producer.produce(
            topic,
            value=payload,
            key=key_bytes,
            headers=headers,
            callback=self._delivery_report,
        )
        self._producer.poll(0)
        logger.info("Kafka produce → %s (key=%s)", topic, key)

    def flush(self, timeout: float = 10.0) -> None:
        self._producer.flush(timeout)

    def close(self) -> None:
        self.flush()
        logger.info("Kafka producer closed")


# ── Consumer ──────────────────────────────────────────────────────────────────

class KafkaConsumerWrapper:
    """Background Kafka consumer with a pluggable handler."""

    def __init__(
        self,
        bootstrap_servers: str,
        topics: list[str],
        group_id: str = "sentinel",
        handler: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        self._servers = bootstrap_servers
        self._topics = topics
        self._group_id = group_id
        self._handler = handler or self._default_handler
        self._consumer: Optional[Consumer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @staticmethod
    def _default_handler(topic: str, message: Any) -> None:
        logger.info("Received message on %s: %s", topic, message)

    def _poll_loop(self) -> None:
        while self._running:
            msg = self._consumer.poll(timeout=1.0)  # type: ignore[union-attr]
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug("End of partition reached")
                else:
                    logger.error("Kafka error: %s", str(msg.error()))
                continue
            try:
                payload = json.loads(msg.value().decode("utf-8")) if msg.value() else {}
            except json.JSONDecodeError:
                payload = {}
            self._handler(msg.topic(), payload)
            self._consumer.commit(msg)

    def start(self) -> None:
        if self._running:
            return
        self._consumer = Consumer(
            {
                "bootstrap.servers": self._servers,
                "group.id": self._group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self._consumer.subscribe(self._topics)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Kafka consumer started — topics: %s", self._topics)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        if self._consumer:
            self._consumer.close()
        logger.info("Kafka consumer stopped")


# ─── Module-level singletons ──────────────────────────────────────────────────

_settings = KafkaSettings()
_kafka_available = Producer is not None  # type: ignore

if _kafka_available:
    kafka_producer = KafkaProducerWrapper(_settings.bootstrap_servers)
    kafka_consumer = KafkaConsumerWrapper(
        bootstrap_servers=_settings.bootstrap_servers,
        topics=["sentinel.screening", "sentinel.fraud", "sentinel.merchant"],
        group_id=_settings.group_id,
    )
else:
    kafka_producer = None  # type: ignore[assignment]
    kafka_consumer = None  # type: ignore[assignment]
