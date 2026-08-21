"""Pydantic v2 schemas for the Real-Time Payment Gateway."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────


class PaymentSource(str, Enum):
    """Where the payment originated."""
    STRIPE = "stripe"
    PLAID = "plaid"
    CUSTOM = "custom"


class TrailFlag(str, Enum):
    """Risk flags detected in money trail analysis."""
    CIRCULAR_FLOW = "circular_flow"
    STRUCTURING = "structuring"
    HIGH_RISK_COUNTERPARTY = "high_risk_counterparty"
    SANCTIONS_MATCH = "sanctions_match"
    VELOCITY_ANOMALY = "velocity_anomaly"
    GEO_ANOMALY = "geo_anomaly"
    LAYERING_PATTERN = "layering_pattern"
    SHELL_COMPANY = "shell_company"


class ScreeningRecommendation(str, Enum):
    """Final decision from verification pipeline."""
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


# ─── Payment Event ────────────────────────────────────────────────────────────


class EntityRef(BaseModel):
    """Sender or receiver in a transaction."""
    entity_id: str = Field(..., description="Internal entity ID")
    name: str = Field(..., description="Entity name")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    email: Optional[str] = None
    phone: Optional[str] = None


class PaymentEvent(BaseModel):
    """Normalized payment event from any CRM source."""
    payment_id: str = Field(..., description="Unique payment identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    sender: EntityRef
    receiver: EntityRef
    source: PaymentSource
    metadata: dict = Field(default_factory=dict, description="Raw webhook metadata")
    risk_signals: list[str] = Field(default_factory=list, description="Pre-screening risk signals")

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


# ─── Money Trail ──────────────────────────────────────────────────────────────


class MoneyTrailNode(BaseModel):
    """A single node in the money trail."""
    entity_id: str
    entity_type: str  # "person", "account", "merchant", "blockchain_wallet"
    name: str
    risk_score: float = 0.0
    attributes: dict[str, Any] = Field(default_factory=dict)
    distance: int = 1  # hops from origin


class TrailFlags(BaseModel):
    """Risk flags detected during trail analysis."""
    circular_flow: bool = False
    structuring: bool = False
    high_risk_counterparties: list[str] = Field(default_factory=list)
    sanctions_matches: list[str] = Field(default_factory=list)
    layering_detected: bool = False
    shell_company_indicators: list[str] = Field(default_factory=list)


class TrailAnalysis(BaseModel):
    """Result of following the money trail."""
    payment_id: str
    trail_depth: int
    nodes: list[MoneyTrailNode] = Field(default_factory=list)
    flags: TrailFlags = Field(default_factory=TrailFlags)
    aggregated_risk_score: float = 0.0
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str = ""


# ─── Verification ─────────────────────────────────────────────────────────────


class VerificationQuestion(BaseModel):
    """A question the verification agent asks."""
    question_id: str
    text: str
    question_type: str = Field(..., description="fact_check | document_request | context_gather")
    priority: str = Field("MEDIUM", description="HIGH | MEDIUM | LOW")
    related_entity: Optional[str] = None


class VerificationAnswer(BaseModel):
    """An answer to a verification question."""
    question_id: str
    answer: str
    source: str = Field(..., description="entity | knowledge_base | user | crm | llm")
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class VerificationContext(BaseModel):
    """Aggregated context for the verification agent."""
    payment_event: PaymentEvent
    trail_analysis: Optional[TrailAnalysis] = None
    screening_result: Optional[dict[str, Any]] = None
    fraud_score: Optional[float] = None
    questions_asked: list[VerificationQuestion] = Field(default_factory=list)
    answers_received: list[VerificationAnswer] = Field(default_factory=list)


class VerificationDecision(BaseModel):
    """Final decision from the verification pipeline."""
    payment_id: str
    decision: ScreeningRecommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list)
    risk_score: float = 0.0
    flags: list[str] = Field(default_factory=list)
    made_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationRound(BaseModel):
    """One round of Q&A in the verification pipeline."""
    round_number: int
    questions: list[VerificationQuestion]
    answers: list[VerificationAnswer]
    new_flags: list[str] = Field(default_factory=list)


# ─── Gateway Response ─────────────────────────────────────────────────────────


class GatewayResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: str = ""
