"""Pydantic schemas for the Verification Pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


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
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class VerificationContext(BaseModel):
    """Aggregated context for the verification agent."""
    payment_event: dict[str, Any]
    trail_analysis: Optional[dict[str, Any]] = None
    screening_result: Optional[dict[str, Any]] = None
    fraud_score: Optional[float] = None
    questions_asked: list[VerificationQuestion] = Field(default_factory=list)
    answers_received: list[VerificationAnswer] = Field(default_factory=list)


class VerificationDecision(BaseModel):
    """Final decision from the verification pipeline."""
    payment_id: str
    decision: str = Field(..., description="APPROVE | REVIEW | BLOCK")
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
