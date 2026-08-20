"""SQLAlchemy 2.0 ORM models for Sentinel FinTech."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.shared.db import Base


# ─── Enums ────────────────────────────────────────────────────────────────────


class RecommendationEnum(str, enum.Enum):
    """Screening result recommendation."""

    APPROVE = "APPROVE"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


class SeverityEnum(str, enum.Enum):
    """Fraud alert severity level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatusEnum(str, enum.Enum):
    """Fraud alert lifecycle status."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class TransactionStatusEnum(str, enum.Enum):
    """Transaction lifecycle status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DECLINED = "DECLINED"


class MerchantStatusEnum(str, enum.Enum):
    """Merchant onboarding status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"


class KYBStatusEnum(str, enum.Enum):
    """Know-Your-Business verification status."""

    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class KYCStatusEnum(str, enum.Enum):
    """Know-Your-Customer verification status."""

    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


# ─── Mixins ───────────────────────────────────────────────────────────────────


class TimestampMixin:
    """Auto-managed `created_at` column mixin."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default="now()",
        nullable=False,
    )


# ─── Models ───────────────────────────────────────────────────────────────────


class Transaction(Base, TimestampMixin):
    """A single payment/transfer transaction."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="now()",
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    sender_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    sender_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    receiver_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    receiver_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    receiver_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(TransactionStatusEnum),
        nullable=False,
        server_default="PENDING",
    )
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime]  # from TimestampMixin

    # Relationships
    screening_results: Mapped[list["ScreeningResult"]] = relationship(
        "ScreeningResult",
        back_populates="transaction",
        lazy="selectin",
    )
    fraud_alerts: Mapped[list["FraudAlert"]] = relationship(
        "FraudAlert",
        back_populates="transaction",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_txns_sender_country", "sender_country"),
        Index("ix_txns_receiver_country", "receiver_country"),
        Index("ix_txns_status_risk", "status", "risk_score"),
        Index("ix_txns_created_at", "created_at"),
    )


class ScreeningResult(Base, TimestampMixin):
    """Result of a sanction / risk screening check on a transaction."""

    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    matched_entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str] = mapped_column(
        Enum(RecommendationEnum),
        nullable=False,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]  # from TimestampMixin

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="screening_results",
    )

    __table_args__ = (
        Index("ix_screening_txn_id", "transaction_id"),
        Index("ix_screening_recommendation", "recommendation"),
        Index("ix_screening_created_at", "created_at"),
    )


class FraudAlert(Base, TimestampMixin):
    """Raised when a transaction or pattern triggers fraud detection."""

    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        Enum(SeverityEnum),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(AlertStatusEnum),
        nullable=False,
        server_default="OPEN",
        index=True,
    )
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    triage_recommendation: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    agent_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]  # from TimestampMixin
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction",
        back_populates="fraud_alerts",
    )

    __table_args__ = (
        Index("ix_alerts_severity_status", "severity", "status"),
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_transaction_id", "transaction_id"),
    )


class Merchant(Base, TimestampMixin):
    """Registered merchant / business entity."""

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_name: Mapped[str] = mapped_column(String(256), nullable=False)
    registration_number: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(MerchantStatusEnum),
        nullable=False,
        server_default="PENDING",
        index=True,
    )
    kyb_status: Mapped[str] = mapped_column(
        Enum(KYBStatusEnum),
        nullable=False,
        server_default="NOT_STARTED",
    )
    kyc_status: Mapped[str] = mapped_column(
        Enum(KYCStatusEnum),
        nullable=False,
        server_default="NOT_STARTED",
    )
    created_at: Mapped[datetime]  # from TimestampMixin

    __table_args__ = (
        UniqueConstraint("registration_number", name="uq_merchants_reg_number"),
        Index("ix_merchants_status", "status"),
        Index("ix_merchants_country", "country"),
        Index("ix_merchants_created_at", "created_at"),
    )


class UserProfile(Base, TimestampMixin):
    """User profile with baseline behavioural data for anomaly detection."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    typical_amount_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    typical_amount_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    typical_countries: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    profile_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]  # from TimestampMixin

    __table_args__ = (
        Index("ix_profiles_device_fp", "device_fingerprint"),
    )


class EntityGraph(Base, TimestampMixin):
    """Edge in a relationship graph linking entities (persons, accounts, devices, etc.)."""

    __tablename__ = "entity_graph"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime]  # from TimestampMixin

    __table_args__ = (
        Index(
            "ix_entity_graph_unique",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            unique=True,
        ),
        Index("ix_entity_graph_source", "source_entity_id", "relationship_type"),
        Index("ix_entity_graph_target", "target_entity_id", "relationship_type"),
    )


# ─── Module-level import guard ────────────────────────────────────────────────
# Ensure all models are registered with Base.metadata before migrations run.
# __import__ is used here rather than a direct import to avoid circular deps
# between db.py and this module during Alembic bootstrapping.

__all__ = [
    "Transaction",
    "ScreeningResult",
    "FraudAlert",
    "Merchant",
    "UserProfile",
    "EntityGraph",
]
