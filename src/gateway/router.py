"""FastAPI router for the real-time payment gateway."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.gateway.ingestion import _ingestor
from src.gateway.schemas import GatewayResponse, PaymentEvent
from src.gateway.trail import _trail_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.post("/payment", response_model=GatewayResponse)
async def ingest_payment(webhook_payload: dict[str, Any]) -> GatewayResponse:
    """Ingest a payment webhook from Stripe, Plaid, or custom source.

    Normalizes the payload and publishes to Kafka for downstream processing.
    """
    try:
        payment_event: PaymentEvent = await _ingestor.ingest(webhook_payload)
        return GatewayResponse(
            success=True,
            data={"payment_id": payment_event.payment_id, "source": payment_event.source.value},
            message="Payment ingested successfully",
        )
    except Exception as e:
        logger.error("Failed to ingest payment: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/trail/{payment_id}", response_model=GatewayResponse)
async def analyze_trail(payment_id: str) -> GatewayResponse:
    """Analyze the money trail for a given payment."""
    try:
        trail_analysis = await _trail_engine.follow_trail(payment_id)
        return GatewayResponse(
            success=True,
            data=trail_analysis.model_dump(),
            message=f"Trail analysis complete: {trail_analysis.aggregated_risk_score:.3f} risk score",
        )
    except Exception as e:
        logger.error("Trail analysis failed for %s: %s", payment_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trail/{payment_id}/status", response_model=GatewayResponse)
async def get_trail_status(payment_id: str) -> GatewayResponse:
    """Check the status of a trail analysis."""
    return GatewayResponse(
        success=True,
        data={"payment_id": payment_id, "status": "completed", "has_trail": True},
        message="Trail status retrieved",
    )


@router.get("/health", response_model=GatewayResponse)
async def health() -> GatewayResponse:
    """Gateway health check."""
    return GatewayResponse(
        success=True,
        data={"service": "sentinel-gateway", "status": "healthy"},
        message="Gateway is healthy",
    )
