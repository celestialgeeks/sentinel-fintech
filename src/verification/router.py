"""FastAPI router for the verification pipeline."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.verification.pipeline import _pipeline
from src.verification.schemas import VerificationDecision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/run", response_model=VerificationDecision)
async def run_verification(payment_event: dict[str, Any]) -> VerificationDecision:
    """Run full verification pipeline on a payment event."""
    try:
        result = await _pipeline.run(payment_event)
        return VerificationDecision(**result)
    except Exception as e:
        logger.error("Verification failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/question/{payment_id}")
async def ask_question(payment_id: str, question: dict[str, Any]) -> dict[str, Any]:
    """Ask a specific question about a payment."""
    return {"payment_id": payment_id, "question": question.get("text", ""), "answered": True}


@router.get("/status/{payment_id}")
async def get_verification_status(payment_id: str) -> dict[str, Any]:
    """Check verification status."""
    return {"payment_id": payment_id, "status": "completed", "has_decision": True}


@router.get("/decision/{payment_id}", response_model=VerificationDecision)
async def get_verification_decision(payment_id: str) -> VerificationDecision:
    """Get final verification decision."""
    # In production: lookup from DB
    return VerificationDecision(
        payment_id=payment_id,
        decision="REVIEW",
        confidence=0.75,
        reasoning="Sample decision for demonstration",
        risk_score=0.45,
    )
