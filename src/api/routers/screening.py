"""FastAPI router for Transaction Screening endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from src.screening.engine import ScreeningEngine
from src.screening.schemas import ScreeningResponse, TransactionIngest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screening", tags=["screening"])

# Module-level engine instance
_engine = ScreeningEngine()


@router.post("/transactions", response_model=ScreeningResponse)
async def screen_transaction(txn: TransactionIngest) -> ScreeningResponse:
    """Submit a transaction for AML/sanctions screening."""
    result = _engine.screen(txn)
    logger.info("Screened txn=%s → %s (score=%.3f)", txn.transaction_id, result.recommendation, result.risk_score)
    return result


@router.get("/transactions/{transaction_id}", response_model=ScreeningResponse)
async def get_screening_result(transaction_id: str) -> dict[str, Any]:
    """Get screening result by transaction ID (placeholder — stores in-memory for now)."""
    # In production, query PostgreSQL for the result
    return {
        "transaction_id": transaction_id,
        "message": "Screening result storage coming in Phase 5",
        "status": "pending",
    }
