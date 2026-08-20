"""Pydantic schemas for Fraud Detection module."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BehavioralProfile(BaseModel):
    """User behavioral baseline for anomaly detection."""

    user_id: str
    typical_amount_mean: float = 0.0
    typical_amount_std: float = 0.0
    txns_last_hour: int = 0
    txns_last_24h: int = 0
    typical_hours: list[int] = Field(default_factory=list)
    typical_countries: list[str] = Field(default_factory=list)
    device_fingerprint: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)


class FraudScore(BaseModel):
    """Result of fraud scoring for a transaction."""

    transaction_id: str
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    behavioral_z_score: float = 0.0
    velocity_score: float = 0.0
    geo_anomaly: bool = False
    time_anomaly: bool = False
    ml_score: float = 0.0
    combined_score: float = Field(..., ge=0.0, le=1.0)
    recommendation: str = Field(..., description="APPROVE / VERIFY / BLOCK")
    reason: str = ""
    scored_at: datetime = Field(default_factory=datetime.now)


class FraudAlert(BaseModel):
    """Alert raised by fraud detection."""

    alert_id: str
    transaction_id: str
    alert_type: str = Field(..., description="amount_anomaly / velocity / geo_impossible / synthetic / ml_fraud")
    severity: str = Field(..., description="LOW / MEDIUM / HIGH / CRITICAL")
    status: str = Field(default="OPEN", description="OPEN / INVESTIGATING / RESOLVED / DISMISSED")
    risk_score: float = 0.0
    triage_recommendation: Optional[str] = None
    agent_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None


class TriageReport(BaseModel):
    """Agent-generated triage report for a fraud alert."""

    alert_id: str
    transaction_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommendation: str = Field(..., description="ESCALATE / INVESTIGATE / DISMISS")
    risk_dossier: str = ""
    evidence: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
