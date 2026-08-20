"""Pydantic schemas for Merchant KYB/KYC module."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MerchantOnboardRequest(BaseModel):
    """Payload for merchant onboarding."""

    business_name: str = Field(..., min_length=1, max_length=256)
    registration_number: Optional[str] = Field(None, max_length=64)
    country: str = Field(..., min_length=2, max_length=2)
    industry: str = Field(..., max_length=128)
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    documents: list[dict] = Field(
        default_factory=list,
        description="Uploaded documents: [{type: 'INCORPORATION', file_url: '...'}]",
    )


class MerchantOnboardResponse(BaseModel):
    """Response after merchant onboarding submission."""

    merchant_id: str
    status: str = Field(..., description="PENDING / APPROVED / REJECTED / REVIEW")
    risk_score: float = Field(..., ge=0.0, le=1.0)
    kyb_status: str = Field(..., description="NOT_STARTED / PENDING / VERIFIED / REJECTED")
    kyc_status: str = Field(..., description="NOT_STARTED / PENDING / VERIFIED / REJECTED")
    ai_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class RiskScoreComponent(BaseModel):
    """Breakdown of a merchant's composite risk score."""

    component: str  # e.g. "kyb_completeness", "web_reputation", "sanctions", "geographic"
    score: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    detail: str = ""


class MerchantRiskReport(BaseModel):
    """Full risk assessment report for a merchant."""

    merchant_id: str
    composite_score: float = Field(..., ge=0.0, le=1.0)
    components: list[RiskScoreComponent] = Field(default_factory=list)
    recommendation: str = Field(..., description="APPROVE / REVIEW / REJECT")
    explanation: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
