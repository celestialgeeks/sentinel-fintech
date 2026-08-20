"""Smoke tests for the Sentinel API health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """Health endpoint returns 200 with service name."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "sentinel-api"


def test_openapi_schema(client: TestClient) -> None:
    """OpenAPI spec is accessible."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "Sentinel FinTech API"
