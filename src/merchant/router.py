"""FastAPI router for Merchant Approval endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from src.merchant.kyb import KYBVerifier, RAGDocumentExtractor
from src.merchant.risk_scoring import RiskScorer
from src.merchant.schemas import MerchantOnboardRequest, MerchantOnboardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchant", tags=["merchant"])

_kyb_verifier = KYBVerifier()
_extractor = RAGDocumentExtractor()
_risk_scorer = RiskScorer()


@router.post("/onboard", response_model=MerchantOnboardResponse)
async def onboard_merchant(request: MerchantOnboardRequest) -> MerchantOnboardResponse:
    """Submit a merchant for KYB/KYC onboarding and risk assessment."""
    # Extract document info (placeholder — no documents uploaded yet)
    extracted = _extractor.extract("business_info", request.business_name)

    # Verify KYB
    verification = _kyb_verifier.verify(extracted, request.country)

    # Score risk
    risk = _risk_scorer.score(
        business_name=request.business_name,
        country=request.country,
        industry=request.industry,
        doc_verification=verification,
    )

    # Determine status
    status = "APPROVED" if risk["recommendation"] == "APPROVE" else "REVIEW"

    return MerchantOnboardResponse(
        merchant_id=f"merch_{len(router.routes)}",  # placeholder ID
        status=status,
        risk_score=risk["composite_score"],
        kyb_status="VERIFIED" if verification["verified"] else "PENDING",
        kyc_status="NOT_STARTED",
        ai_summary=risk["explanation"],
    )


@router.get("/status/{merchant_id}")
async def get_merchant_status(merchant_id: str) -> dict[str, Any]:
    """Get onboarding status for a merchant (placeholder)."""
    return {
        "merchant_id": merchant_id,
        "status": "PENDING",
        "message": "Merchant status tracking coming in Phase 5",
    }
