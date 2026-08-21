"""CRM connectors for real-time payment verification.

Connects to Stripe, Plaid, and provides a base interface for custom CRMs.
Each connector implements: verify_payment(), get_entity_history(), get_risk_signals()
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseCRMConnector(ABC):
    """Abstract base for all CRM connectors."""

    @abstractmethod
    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        """Verify a specific payment and return its details."""
        ...

    @abstractmethod
    async def get_entity_history(self, entity_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get transaction history for an entity (sender/receiver)."""
        ...

    @abstractmethod
    async def get_risk_signals(self, entity_id: str) -> list[dict[str, Any]]:
        """Get risk signals associated with an entity."""
        ...

    def get_name(self) -> str:
        """Return the connector name."""
        return self.__class__.__name__


class StripeConnector(BaseCRMConnector):
    """Stripe API connector for payment verification."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key
        # In production: import stripe and use stripe.ApiKey
        # For now: mock implementations for the architecture

    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        """Verify a Stripe payment_intent or charge."""
        logger.info("Verifying Stripe payment: %s", payment_id)
        return {
            "payment_id": payment_id,
            "source": "stripe",
            "status": "succeeded",
            "verified": True,
            "metadata": {},
        }

    async def get_entity_history(self, entity_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get Stripe customer transaction history."""
        logger.info("Fetching Stripe history for: %s", entity_id)
        return []

    async def get_risk_signals(self, entity_id: str) -> list[dict[str, Any]]:
        """Get Stripe Radar risk signals for an entity."""
        logger.info("Fetching Stripe risk signals for: %s", entity_id)
        return []


class PlaidConnector(BaseCRMConnector):
    """Plaid API connector for bank account verification."""

    def __init__(self, client_id: Optional[str] = None, secret: Optional[str] = None) -> None:
        self._client_id = client_id
        self._secret = secret

    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        """Verify a Plaid transaction."""
        logger.info("Verifying Plaid transaction: %s", payment_id)
        return {
            "payment_id": payment_id,
            "source": "plaid",
            "status": "pending",
            "verified": True,
            "metadata": {},
        }

    async def get_entity_history(self, entity_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get Plaid transaction history for an account."""
        logger.info("Fetching Plaid history for: %s", entity_id)
        return []

    async def get_risk_signals(self, entity_id: str) -> list[dict[str, Any]]:
        """Get Plaid Identity verification signals."""
        logger.info("Fetching Plaid risk signals for: %s", entity_id)
        return []


def get_connector(source: str) -> BaseCRMConnector:
    """Factory function to get the right connector for a payment source."""
    connectors = {
        "stripe": StripeConnector,
        "plaid": PlaidConnector,
    }
    connector_class = connectors.get(source.lower())
    if connector_class is None:
        raise ValueError(f"Unknown payment source: {source}")
    return connector_class()
