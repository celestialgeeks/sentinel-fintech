"""Pydantic v2 schemas for the Transaction Screening Engine."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


# ─── Request schemas ───────────────────────────────────────────────────────────


class EntityRef(BaseModel):
    """Sender or receiver in a transaction."""

    entity_id: str = Field(..., description="Internal entity ID")
    name: str = Field(..., description="Entity name (individual or organisation)")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")


class TransactionIngest(BaseModel):
    """Payload for POST /api/v1/screening/transactions."""

    transaction_id: str = Field(..., description="Unique transaction identifier", max_length=64)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    sender: EntityRef
    receiver: EntityRef
    metadata: dict = Field(default_factory=dict)

    @field_validator("transaction_id")
    @classmethod
    def transaction_id_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("transaction_id must not be empty")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


# ─── Response schemas ──────────────────────────────────────────────────────────


class MatchedEntity(BaseModel):
    """A watchlist match found during screening."""

    entity_id: str
    name: str
    match_score: float = Field(..., ge=0.0, le=1.0)
    list_source: str = Field(description="OFAC / UN / EU / etc.")
    reason: str


class ScreeningResponse(BaseModel):
    """Response from the screening engine."""

    transaction_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Aggregated risk score 0-1")
    flags: list[str] = Field(default_factory=list, description="Rule names that triggered")
    matched_entities: list[MatchedEntity] = Field(default_factory=list)
    recommendation: str = Field(..., description="APPROVE / BLOCK / REVIEW")
    explanation: str = Field(..., description="Human-readable reason for the decision")
    screened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
