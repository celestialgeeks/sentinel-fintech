"""Dashboard aggregates: KPI strip, verdict mix, histogram, provider health.
"""


from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.portal.schemas.ledger import CounterpartyRow, OrderRow


class VerdictCounts(BaseModel):
    allow: int = 0
    hold: int = 0
    block: int = 0
    degraded: int = 0


class StatsSummary(BaseModel):
    merchant_keys: list[str] = Field(default_factory=list)
    window: str = "today"
    orders: int = 0
    verdicts: VerdictCounts = Field(default_factory=VerdictCounts)
    inr_blocked: float = 0.0
    inr_released: float = 0.0
    inr_on_hold: float = 0.0
    auto_cleared_pct: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    vendor_spend_usd: float = 0.0
    spend_per_order_usd: float = 0.0
    holds_open: int = 0
    holds_overdue: int = Field(0, description="HOLDs older than the 15-minute release window")
    quarantine_inr: float = 0.0
    awaiting_sweep_inr: float = 0.0
    unmatched_credits: int = 0
    lien_cases_open: int = 0


class TimeseriesPoint(BaseModel):
    bucket: datetime
    allow: int = 0
    hold: int = 0
    block: int = 0
    inr_blocked: float = 0.0
    decisions: int = 0


class RiskBucket(BaseModel):
    low: float
    high: float
    count: int = 0


class RuleStat(BaseModel):
    name: str
    triggers: int = 0
    led_to_block: int = 0


class ProviderStat(BaseModel):
    provider: str
    category: str
    calls: int = 0
    ok: int = 0
    errored: int = 0
    unavailable: int = 0
    skipped: int = 0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    cost_usd: float = 0.0
    status: str = "ok"


class TrendPoint(BaseModel):
    label: str
    value: float
    secondary: float | None = None


class Sparkline(BaseModel):
    values: list[float] = Field(default_factory=list)


class OverviewResponse(BaseModel):
    summary: StatsSummary
    mix: VerdictCounts
    mix_by_phase: dict[str, VerdictCounts] = Field(default_factory=dict)
    risk_histogram: list[RiskBucket] = Field(default_factory=list)
    timeseries: list[TimeseriesPoint] = Field(default_factory=list)
    top_rules: list[RuleStat] = Field(default_factory=list)
    top_buyers: list[CounterpartyRow] = Field(default_factory=list)
    providers: list[ProviderStat] = Field(default_factory=list)
    needs_action: list[OrderRow] = Field(default_factory=list)
    sparklines: dict[str, Sparkline] = Field(default_factory=dict)
