"""Smoke tests for the Sentinel API health endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from src.api.main import app


def test_health_endpoint() -> None:
    """Health endpoint returns 200 without requiring DB/Redis/Kafka."""
    with patch("src.shared.db.init_db", new=AsyncMock()), \
         patch("src.shared.cache.RedisClient.ping", new=AsyncMock(return_value=True)), \
         patch("src.shared.kafka.kafka_consumer") as mock_consumer, \
         patch("src.shared.kafka.kafka_producer", None):
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "sentinel-api"


def test_openapi_schema() -> None:
    """OpenAPI spec is accessible."""
    with patch("src.shared.db.init_db", new=AsyncMock()), \
         patch("src.shared.cache.RedisClient.ping", new=AsyncMock(return_value=True)), \
         patch("src.shared.kafka.kafka_consumer") as mock_consumer, \
         patch("src.shared.kafka.kafka_producer", None):
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "Sentinel FinTech API"
