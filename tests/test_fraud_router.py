"""Tests for the Fraud API router endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import app


def test_fraud_check_endpoint() -> None:
    """POST /api/v1/fraud/check returns a FraudScore."""
    with patch("src.shared.db.init_db", new=AsyncMock()), \
         patch("src.shared.cache.RedisClient.ping", new=AsyncMock(return_value=True)), \
         patch("src.shared.kafka.kafka_consumer") as mock_consumer, \
         patch("src.shared.kafka.kafka_producer", None):
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/fraud/check", params={
            "transaction_id": "tx_test", "user_id": "usr_1", "amount": 500.0, "country": "US"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "transaction_id" in data
    assert "combined_score" in data
    assert data["recommendation"] in ("APPROVE", "VERIFY", "BLOCK")


def test_fraud_check_high_amount() -> None:
    """High amount should return VERIFY or BLOCK."""
    with patch("src.shared.db.init_db", new=AsyncMock()), \
         patch("src.shared.cache.RedisClient.ping", new=AsyncMock(return_value=True)), \
         patch("src.shared.kafka.kafka_consumer") as mock_consumer, \
         patch("src.shared.kafka.kafka_producer", None):
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/fraud/check", params={
            "transaction_id": "tx_big", "user_id": "usr_2", "amount": 50000.0, "country": "US"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation"] in ("VERIFY", "BLOCK")


def test_fraud_alerts_list() -> None:
    """GET /api/v1/fraud/alerts returns a list."""
    with patch("src.shared.db.init_db", new=AsyncMock()), \
         patch("src.shared.cache.RedisClient.ping", new=AsyncMock(return_value=True)), \
         patch("src.shared.kafka.kafka_consumer") as mock_consumer, \
         patch("src.shared.kafka.kafka_producer", None):
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/fraud/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_fraud_triage_404() -> None:
    """Triage on non-existent alert returns 404."""
    with patch("src.shared.db.init_db", new=AsyncMock()), \
         patch("src.shared.cache.RedisClient.ping", new=AsyncMock(return_value=True)), \
         patch("src.shared.kafka.kafka_consumer") as mock_consumer, \
         patch("src.shared.kafka.kafka_producer", None):
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/fraud/alerts/nonexistent/triage")
    assert resp.status_code == 404
