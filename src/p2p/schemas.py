"""I/O schemas for the P2P taint guard."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.gateway.schemas import GuardPhase, GuardVerdict, P2POrder
from src.screening.schemas import ProviderVerdict


class GuardRequest(BaseModel):
    """Body accepted by both guard gates (pre-screen and release-gate)."""
    order: P2POrder
    phase: GuardPhase = GuardPhase.RELEASE_GATE


class GuardDecision(BaseModel):
    """Verdict returned to the merchant bot."""
    order_id: str
    merchant_id: str = "default"
    phase: GuardPhase
    verdict: GuardVerdict
    action: str = Field(..., description="release | hold | reject — what the bot must do")
    risk_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    hard_rules: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    step_up: list[str] = Field(default_factory=list, description="Actions to clear a HOLD")
    provider_verdicts: list[ProviderVerdict] = Field(default_factory=list)
    behavioural_score: float = 0.0
    degraded: bool = Field(False, description="A required vendor could not be reached")
    evidence_ref: str | None = Field(None, description="Reference of the stored evidence bundle")
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LienNotice(BaseModel):
    """A bank/legal notice reported to the guard (email/webhook/manual intake)."""
    order_id: str | None = None
    utr: str | None = None
    account_no_masked: str | None = None
    merchant_id: str = Field("default", description="Workspace the freeze case belongs to")
    source: str = Field("manual", description="bank_email | webhook | manual")
    notice_text: str = ""
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
