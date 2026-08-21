"""FastAPI router for the Decision Engine."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.decision.engine import _decision_engine
from src.gateway.schemas import GatewayResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decision", tags=["decision"])


@router.post("/run", response_model=GatewayResponse)
async def run_decision(payload: dict[str, Any]) -> GatewayResponse:
    """Run the full decision pipeline on a payment.

    Expects: payment_id, trail_analysis, screening_result, verification_result
    """
    payment_id = payload.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id is required")

    try:
        result = await _decision_engine.decide(
            payment_id=payment_id,
            trail_analysis=payload.get("trail_analysis", {}),
            screening_result=payload.get("screening_result", {}),
            verification_result=payload.get("verification_result", {}),
        )
        return GatewayResponse(
            success=True,
            data=result,
            message=f"Decision: {result['decision']}",
        )
    except Exception as e:
        logger.error("Decision engine failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=GatewayResponse)
async def health() -> GatewayResponse:
    """Decision engine health check."""
    return GatewayResponse(
        success=True,
        data={"service": "sentinel-decision", "status": "healthy"},
        message="Decision engine is healthy",
    )
