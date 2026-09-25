"""Pydantic v2 schemas for the Transaction Screening Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ─── Vendor / counterparty screening ─────────────────────────────────────────


class ProviderCategory(str, Enum):
    """Class of risk signal a vendor verdict describes."""
    WALLET = "wallet"          # on-chain exposure (sanctions/mixer/darknet/stolen)
    MULE = "mule"              # bank account is a suspected mule
    BANK_ACCOUNT = "bank"      # bank-account existence/ownership verification
    NAME_MATCH = "name"        # payer-name vs beneficiary-name match
    SANCTIONS = "sanctions"    # sanctions/PEP/adverse-media hit
    COMPLAINT = "complaint"    # linked to a registered complaint/FIR proxy
    TRUST = "trust"            # internal repeat-counterparty trust score
    OTHER = "other"


class ProviderStatus(str, Enum):
    """Outcome of a single vendor call."""
    OK = "ok"
    UNAVAILABLE = "unavailable"   # no API key / not configured
    ERROR = "error"               # call failed (outage / timeout)
    SKIPPED = "skipped"           # tiered execution decided not to call


class ProviderVerdict(BaseModel):
    """Uniform result emitted by every ScreeningProvider adapter."""
    provider: str
    category: ProviderCategory = ProviderCategory.OTHER
    status: ProviderStatus = ProviderStatus.OK
    risk: float = Field(0.0, ge=0.0, le=1.0, description="0..1 risk contribution")
    matched_list: str = Field("", description="Which list/entity matched, if any")
    detail: str = Field("", description="Human-readable explanation")
    evidence_ref: str = Field("", description="Pointer to stored raw evidence")
    raw_ref: str = Field("", description="Vendor-side reference/report id")
    cost_usd: float = Field(0.0, ge=0.0, description="Approx cost of this call")
    latency_ms: int = Field(0, ge=0)


class CounterpartyScreening(BaseModel):
    """Aggregated vendor screening result for one order's counterparty."""
    order_id: str
    verdicts: list[ProviderVerdict] = Field(default_factory=list)
    max_risk: float = Field(0.0, ge=0.0, le=1.0)
    hard_block: bool = Field(False, description="True if any verdict is a hard block (sanctions/confirmed mule)")
    degraded: bool = Field(False, description="True if a required provider failed (fail-closed applied)")
    screened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def by_category(self, category: ProviderCategory) -> list[ProviderVerdict]:
        return [v for v in self.verdicts if v.category == category]



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
