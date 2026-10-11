"""Order, buyer, settlement, freeze-case and compliance models.

This is the evidence a merchant shows a bank or a compliance officer, so the
verdict, the reasons and the timeline are all first-class fields rather than a
rendered string.
"""


from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OrderRow(BaseModel):
    """One guarded order as it appears in the transaction history table."""

    order_id: str
    merchant_id: str
    decided_at: datetime | None = None
    created_at: datetime
    phase: str
    asset: str
    fiat: str
    qty: float
    price_inr: float
    inr_value: float
    buyer_user: str | None = None
    buyer_name: str | None = None
    buyer_country: str | None = None
    verdict: str
    action: str
    risk_score: float
    confidence: float
    hard_rules: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    degraded: bool = False
    evidence_ref: str | None = None
    voucher_ref: str | None = None
    pool: str | None = None
    voucher_status: str | None = None
    utr: str | None = None
    payer_name: str | None = None
    account_no_masked: str | None = None
    payment_method: str | None = None
    spend_usd: float = 0.0
    latency_ms: int = 0
    rules_total: int = 0


class DecisionBlock(BaseModel):
    verdict: str
    action: str
    risk_score: float
    confidence: float
    hard_rules: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    step_up: list[str] = Field(default_factory=list)
    behavioural_score: float = 0.0
    vendor_max_risk: float = 0.0
    composite: float = 0.0
    degraded: bool = False
    decided_at: datetime | None = None


class BuyerBlock(BaseModel):
    binance_user: str | None = None
    verified_name: str | None = None
    country: str | None = None
    trade_count: int = 0
    completion_rate: float = 0.0
    account_age_days: int | None = None
    chat_snippet: str | None = None
    chat_red_flags: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class PaymentBlock(BaseModel):
    method: str | None = None
    utr: str | None = None
    vpa: str | None = None
    account_no_masked: str | None = None
    ifsc: str | None = None
    bank_name: str | None = None
    payer_name_on_account: str | None = None
    amount: float | None = None
    credit_ts: datetime | None = None
    confirmed: bool = False


class WalletBlock(BaseModel):
    chain: str | None = None
    deposit_address: str | None = None
    withdrawal_address: str | None = None
    exchange: str | None = None


class VendorCallRow(BaseModel):
    provider: str
    category: str
    status: str
    risk: float
    detail: str = ""
    matched_list: str = ""
    raw_ref: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


class EvidenceMeta(BaseModel):
    reference: str
    phase: str
    verdict: str
    created_at: datetime | None = None
    formats: list[str] = Field(default_factory=lambda: ["markdown", "json"])
    download_path: str = ""


class VoucherRow(BaseModel):
    voucher_ref: str
    order_id: str
    virtual_account: str | None = None
    vpa: str | None = None
    utr: str | None = None
    amount: float | None = None
    pool: str
    status: str
    credited_at: datetime | None = None
    sweep_after: datetime | None = None
    alerts: list[str] = Field(default_factory=list)


class ComplianceRow(BaseModel):
    event_type: str
    order_id: str
    amount: float | None = None
    created_at: datetime
    payload: dict = Field(default_factory=dict)


class OverrideRow(BaseModel):
    actor_email: str
    action: str
    from_verdict: str
    reason: str
    created_at: datetime


class TimelineNode(BaseModel):
    name: str
    at: datetime | None = None
    detail: str = ""


class OrderDetail(BaseModel):
    """Everything the order-detail screen shows, in one call."""

    order: OrderRow
    decision: DecisionBlock
    buyer: BuyerBlock
    payment: PaymentBlock | None = None
    wallet: WalletBlock | None = None
    vendor_calls: list[VendorCallRow] = Field(default_factory=list)
    evidence: EvidenceMeta | None = None
    voucher: VoucherRow | None = None
    compliance: list[ComplianceRow] = Field(default_factory=list)
    overrides: list[OverrideRow] = Field(default_factory=list)
    timeline: list[TimelineNode] = Field(default_factory=list)
    not_screened: bool = Field(False, description="True when this order exists outside Sentinel")


class OverrideRequest(BaseModel):
    action: str = Field(..., description="release | hold | reject")
    reason: str = Field(min_length=10, max_length=2000)


class CounterpartyRow(BaseModel):
    """Repeat-buyer state, aggregated from this merchant's own orders."""

    buyer_key: str
    binance_user: str | None = None
    verified_name: str | None = None
    seen: int = 0
    flagged: int = 0
    clean_streak: int = 0
    allow: int = 0
    hold: int = 0
    block: int = 0
    inr_traded: float = 0.0
    inr_blocked: float = 0.0
    last_risk: float | None = None
    last_verdict: str | None = None
    last_seen_at: datetime | None = None
    first_seen_at: datetime | None = None
    watch: bool = False


class LienRow(BaseModel):
    case_ref: str
    merchant_id: str
    order_id: str | None = None
    utr: str | None = None
    account_no_masked: str | None = None
    source: str
    status: str
    notice_text: str | None = None
    evidence_reference: str | None = None
    evidence_available: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class LienCreateRequest(BaseModel):
    order_id: str | None = None
    utr: str | None = None
    account_no_masked: str | None = None
    source: str = Field("manual", description="bank_email | webhook | manual")
    notice_text: str = ""


class LienUpdateRequest(BaseModel):
    status: str = Field(..., description="open | awaiting_bank | submitted | lifted | rejected")
    note: str | None = None


class LienCaseFile(BaseModel):
    case: LienRow
    assembled: bool
    evidence_markdown: str | None = None
    missing: list[str] = Field(default_factory=list)
