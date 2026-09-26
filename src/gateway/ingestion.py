"""Payment webhook ingestion for real-time screening.

Parses Stripe and Plaid webhook payloads, normalizes to PaymentEvent,
and publishes to Kafka for downstream processing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.core.kafka_client import kafka_producer
from src.gateway.schemas import EntityRef, PaymentEvent, PaymentSource

logger = logging.getLogger(__name__)


class PaymentWebhookIngestor:
    """Ingests payment webhooks from Stripe, Plaid, and custom sources."""

    async def ingest(self, webhook_payload: dict[str, Any]) -> PaymentEvent:
        """Parse webhook, normalize to PaymentEvent, publish to Kafka.

        Args:
            webhook_payload: Raw webhook JSON payload

        Returns:
            Normalized PaymentEvent

        Raises:
            ValueError: If payload cannot be parsed
        """
        event_type = webhook_payload.get("type", "")
        data = webhook_payload.get("data", {}).get("object", {})

        if "stripe" in event_type.lower() or "payment_intent" in event_type.lower():
            payment_event = self._parse_stripe(data, event_type)
        elif "plaid" in event_type.lower() or "transaction" in event_type.lower():
            payment_event = self._parse_plaid(data, event_type)
        else:
            payment_event = self._parse_custom(data, event_type)

        # Publish to Kafka
        await self._publish_to_kafka(payment_event)

        logger.info(
            "Ingested payment %s from %s: %.2f %s",
            payment_event.payment_id,
            payment_event.source.value,
            payment_event.amount,
            payment_event.currency,
        )
        return payment_event

    def _parse_stripe(self, data: dict[str, Any], event_type: str) -> PaymentEvent:
        """Parse Stripe webhook payload."""
        return PaymentEvent(
            payment_id=data.get("id", f"stripe_{event_type}_{datetime.now(timezone.utc).isoformat()}"),
            timestamp=datetime.fromtimestamp(data.get("created", 0), tz=timezone.utc) if data.get("created") else datetime.now(timezone.utc),
            amount=data.get("amount", 0) / 100,  # Convert cents to dollars
            currency=data.get("currency", "USD").upper(),
            sender=EntityRef(
                entity_id=data.get("source", {}).get("id", "unknown"),
                name=data.get("description", "Stripe payer"),
                country=data.get("metadata", {}).get("country", "US"),
            ),
            receiver=EntityRef(
                entity_id=data.get("destination", {}).get("id", "unknown"),
                name=data.get("description", "Stripe payee"),
                country=data.get("metadata", {}).get("destination_country", "US"),
            ),
            source=PaymentSource.STRIPE,
            metadata={"event_type": event_type, "raw": data},
        )

    def _parse_plaid(self, data: dict[str, Any], event_type: str) -> PaymentEvent:
        """Parse Plaid transaction payload."""
        return PaymentEvent(
            payment_id=data.get("transaction_id", f"plaid_{event_type}_{datetime.now(timezone.utc).isoformat()}"),
            timestamp=datetime.fromisoformat(data.get("date", datetime.now(timezone.utc).isoformat())),
            amount=data.get("amount", 0.0),
            currency=data.get("iso_currency_code", "USD").upper(),
            sender=EntityRef(
                entity_id=data.get("personal_finance_id", "unknown"),
                name=data.get("name", "Plaid user"),
                country=data.get("location", {}).get("country", "US"),
            ),
            receiver=EntityRef(
                entity_id=data.get("merchant_id", "unknown"),
                name=data.get("name", "Merchant"),
                country=data.get("location", {}).get("country", "US"),
            ),
            source=PaymentSource.PLAID,
            metadata={"event_type": event_type, "raw": data},
        )

    def _parse_custom(self, data: dict[str, Any], event_type: str) -> PaymentEvent:
        """Parse custom webhook payload."""
        return PaymentEvent(
            payment_id=data.get("payment_id", f"custom_{event_type}_{datetime.now(timezone.utc).isoformat()}"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
            amount=float(data.get("amount", 0)),
            currency=data.get("currency", "USD").upper(),
            sender=EntityRef(
                entity_id=data.get("sender_id", "unknown"),
                name=data.get("sender_name", "Unknown sender"),
                country=data.get("sender_country", "US"),
            ),
            receiver=EntityRef(
                entity_id=data.get("receiver_id", "unknown"),
                name=data.get("receiver_name", "Unknown receiver"),
                country=data.get("receiver_country", "US"),
            ),
            source=PaymentSource.CUSTOM,
            metadata={"event_type": event_type, "raw": data},
        )

    async def _publish_to_kafka(self, event: PaymentEvent) -> None:
        """Publish PaymentEvent to Kafka topic 'sentinel.payment'."""
        if kafka_producer is None:
            logger.warning("Kafka producer not available, skipping publish")
            return
        await kafka_producer.produce(
            topic="sentinel.payment",
            key=event.payment_id,
            value=event.model_dump(),
        )
        logger.info("Published payment event to Kafka: %s", event.payment_id)


# Module-level singleton
_ingestor = PaymentWebhookIngestor()
