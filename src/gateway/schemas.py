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
    BINANCE_P2P = "binance_p2p"
    UPI = "upi"
    IMPS = "imps"
    NEFT = "neft"
    RTGS = "rtgs"
    CUSTOM = "custom"


class GuardPhase(str, Enum):
    """Where in the P2P lifecycle a guard decision is being made."""
    PRE_SCREEN = "pre_screen"      # order created / buyer claims paid — before money is accepted
    RELEASE_GATE = "release_gate"  # bank credit confirmed — before USDT leaves escrow


class GuardVerdict(str, Enum):
    """Final ALLOW / HOLD / BLOCK verdict returned to the merchant bot."""
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class PaymentMethod(str, Enum):
    """Instrument the buyer used to pay INR."""
    UPI = "upi"
    IMPS = "imps"
    NEFT = "neft"
    RTGS = "rtgs"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


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


# ─── Binance P2P domain ───────────────────────────────────────────────────────


class BuyerProfile(BaseModel):
    """Buyer-side identity as exposed by the Binance P2P order."""
    binance_user: str = Field(..., description="Binance P2P display / merchant user id")
    verified_name: str = Field(..., description="Name verified on the buyer's Binance KYC")
    country: str = Field("IN", description="ISO alpha-2 buyer country")
    trade_count: int = Field(0, ge=0, description="Lifetime completed P2P trades")
    completion_rate: float = Field(1.0, ge=0.0, le=1.0, description="Buyer order completion rate")
    account_age_days: Optional[int] = Field(None, description="Days since Binance KYC was created")
    chat_snippet: Optional[str] = Field(None, description="Latest P2P chat text (deal red-flag NLP)")
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    risk_flags: list[str] = Field(default_factory=list, description="Bot-supplied raw signals")


class PayerPayment(BaseModel):
    """The actual INR credit observed in the merchant's bank account.

    Populated at RELEASE_GATE from the bank feed / Account Aggregator / UTR.
    Never store full account numbers — account_no_masked holds last 4 only.
    """
    method: PaymentMethod = PaymentMethod.OTHER
    payer_name_on_account: Optional[str] = Field(None, description="Beneficiary name on the credit")
    bank_name: Optional[str] = None
    account_no_masked: Optional[str] = Field(None, description="Last 4 digits only")
    ifsc: Optional[str] = None
    vpa: Optional[str] = Field(None, description="UPI VPA if paid via UPI")
    utr: Optional[str] = Field(None, description="Unique Transaction Reference for the credit")
    amount: float = Field(..., gt=0, description="INR amount actually credited")
    credit_ts: Optional[datetime] = Field(None, description="Timestamp credit landed")
    confirmed: bool = Field(False, description="Bank credit independently confirmed")


class TradeWallet(BaseModel):
    """On-chain / exchange wallet context relevant to the trade."""
    deposit_address: Optional[str] = Field(None, description="Merchant USDT receiving/trade address")
    withdrawal_address: Optional[str] = Field(None, description="Buyer payout address if known")
    chain: str = Field("TRC20", description="Tron/TRC20 is the dominant Binance P2P USDT rail")
    exchange: Optional[str] = Field(None, description="Exchange the address belongs to, if known")


class P2POrder(BaseModel):
    """Normalized Binance P2P order submitted by the merchant bot to the guard."""
    order_id: str = Field(..., description="Binance P2P order id")
    asset: str = Field("USDT", description="Crypto asset being sold")
    fiat: str = Field("INR", description="Fiat currency")
    qty: float = Field(..., gt=0, description="USDT quantity the merchant would release")
    price_inr: float = Field(..., gt=0, description="Agreed INR price")
    side: str = Field("SELL", description="Merchant side (SELL for a merchant)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    buyer: BuyerProfile
    payment: Optional[PayerPayment] = Field(None, description="Filled at release-gate time")
    wallet: Optional[TradeWallet] = None
    merchant_id: str = Field("default", description="Which merchant/account the bot serves")
