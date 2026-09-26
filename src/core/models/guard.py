"""Persistence written by the P2P pre-settlement guard (``src.p2p``).

One row per gate decision, plus the evidence the verdict was built from:
counterparty profiles, vendor calls, evidence bundles, settlement vouchers,
lien cases and compliance events.
"""


from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base

from .base import PkBigInt, TimestampMixin


class P2POrderRecord(Base, TimestampMixin):
    """One guarded Binance-P2P order and its final verdict."""

    __tablename__ = "p2p_orders"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="default")
    asset: Mapped[str] = mapped_column(String(16), nullable=False, default="USDT")
    fiat: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    inr_value: Mapped[float] = mapped_column(Float, nullable=False)
    buyer_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    buyer_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    buyer_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    phase: Mapped[str] = mapped_column(String(16), nullable=False, default="release_gate")
    verdict: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hard_rules: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    reasons: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    step_up: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # clears a HOLD
    behavioural_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_ref: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    # Observed INR credit, flattened from PayerPayment so the ledger can filter on
    # it. Only the last four digits are ever kept — never the full account number.
    payment_method: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    payer_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    account_no_masked: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    vpa: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    utr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    credit_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]

    __table_args__ = (
        # One row per gate: the same order is decided at pre-screen and again at
        # release-gate, so order_id alone must not be unique.
        UniqueConstraint("order_id", "phase", name="uq_p2p_orders_order_phase"),
        Index("ix_p2p_orders_merchant_verdict", "merchant_id", "verdict"),
        Index("ix_p2p_orders_decided_at", "decided_at"),
        Index("ix_p2p_orders_merchant_decided", "merchant_id", "decided_at"),
        Index("ix_p2p_orders_buyer_user", "buyer_user"),
    )


class Counterparty(Base, TimestampMixin):
    """Persisted repeat-buyer risk state (trust with time-decay)."""

    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    buyer_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    binance_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verified_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flagged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clean_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_verdict: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]


class VendorCall(Base, TimestampMixin):
    """Audit + cost/latency record for each provider call."""

    __tablename__ = "vendor_calls"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Which gate made this call. Without it, a two-gate order merges both
    # fan-outs and the ledger reports double the spend and latency it cost.
    phase: Mapped[str] = mapped_column(String(16), nullable=False, default="release_gate")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime]

    __table_args__ = (Index("ix_vendor_calls_order_provider", "order_id", "provider"),)


class EvidenceBundle(Base, TimestampMixin):
    """Immutable per-order evidence snapshot for compliance / unfreezing."""

    __tablename__ = "evidence_bundles"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    verdict: Mapped[str] = mapped_column(String(8), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime]


class SettlementVoucher(Base, TimestampMixin):
    """Maps an order to an isolated receiving voucher/account for UTR traceability."""

    __tablename__ = "settlement_vouchers"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    voucher_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    virtual_account: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vpa: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    utr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pool: Mapped[str] = mapped_column(String(32), nullable=False, default="quarantine")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="issued")
    credited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sweep_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]

    __table_args__ = (Index("ix_vouchers_pool_status", "pool", "status"),)


class LienCase(Base, TimestampMixin):
    """A bank/legal freeze notice mapped to the offending credit + evidence pack."""

    __tablename__ = "lien_cases"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    case_ref: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"  # workspace the freeze belongs to
    )
    order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    utr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    account_no_masked: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    source: Mapped[str] = mapped_column(String(24), nullable=False, default="manual")
    notice_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ComplianceEvent(Base, TimestampMixin):
    """STR-context / 194S TDS / KYC-retention records (adjacent compliance)."""

    __tablename__ = "compliance_events"

    id: Mapped[int] = mapped_column(PkBigInt, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(16), nullable=False, default="release_gate")
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime]
