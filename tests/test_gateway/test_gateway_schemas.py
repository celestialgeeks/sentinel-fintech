"""Tests for the gateway module."""

from __future__ import annotations

import pytest

from src.gateway.crm_connectors import PlaidConnector, StripeConnector, get_connector
from src.gateway.schemas import (
    EntityRef,
    GatewayResponse,
    MoneyTrailNode,
    PaymentEvent,
    PaymentSource,
    TrailAnalysis,
    TrailFlags,
)


class TestPaymentEvent:
    """Tests for PaymentEvent schema."""

    def test_create_payment_event(self) -> None:
        event = PaymentEvent(
            payment_id="test_001",
            amount=1500.00,
            currency="usd",
            sender=EntityRef(entity_id="s1", name="Alice", country="US"),
            receiver=EntityRef(entity_id="r1", name="Bob", country="UK"),
            source=PaymentSource.STRIPE,
        )
        assert event.payment_id == "test_001"
        assert event.currency == "USD"  # Should be uppercased
        assert event.source == PaymentSource.STRIPE

    def test_currency_validation(self) -> None:
        event = PaymentEvent(
            payment_id="test_002",
            amount=100.0,
            currency="USD",
            sender=EntityRef(entity_id="s1", name="Alice", country="US"),
            receiver=EntityRef(entity_id="r1", name="Bob", country="UK"),
            source=PaymentSource.PLAID,
        )
        assert event.currency == "USD"


class TestTrailSchemas:
    """Tests for trail analysis schemas."""

    def test_trail_flags(self) -> None:
        flags = TrailFlags(
            circular_flow=True,
            structuring=False,
            high_risk_counterparties=["entity_1", "entity_2"],
        )
        assert flags.circular_flow is True
        assert len(flags.high_risk_counterparties) == 2

    def test_trail_analysis(self) -> None:
        analysis = TrailAnalysis(
            payment_id="test_001",
            trail_depth=3,
            nodes=[MoneyTrailNode(entity_id="e1", entity_type="person", name="Alice", risk_score=0.8)],
            flags=TrailFlags(circular_flow=True),
            aggregated_risk_score=0.75,
        )
        assert analysis.payment_id == "test_001"
        assert analysis.aggregated_risk_score == 0.75

    def test_gateway_response(self) -> None:
        resp = GatewayResponse(success=True, data={"id": "123"}, message="ok")
        assert resp.success is True
        assert resp.error is None


class TestCRMConnectors:
    """Tests for CRM connectors."""

    @pytest.mark.asyncio
    async def test_stripe_connector(self) -> None:
        connector = StripeConnector()
        result = await connector.verify_payment("pi_test123")
        assert result["payment_id"] == "pi_test123"
        assert result["source"] == "stripe"

    @pytest.mark.asyncio
    async def test_plaid_connector(self) -> None:
        connector = PlaidConnector()
        result = await connector.verify_payment("txn_test123")
        assert result["payment_id"] == "txn_test123"
        assert result["source"] == "plaid"

    def test_get_connector(self) -> None:
        s = get_connector("stripe")
        assert isinstance(s, StripeConnector)
        p = get_connector("plaid")
        assert isinstance(p, PlaidConnector)

    def test_get_connector_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown payment source"):
            get_connector("unknown")
