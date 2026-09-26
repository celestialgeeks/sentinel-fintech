"""AML screening rules — deterministic, stateless, scored 0-1."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.screening.watchlists import HIGH_RISK_JURISDICTIONS

logger = logging.getLogger(__name__)


# ─── Rule result ───────────────────────────────────────────────────────────────


@dataclass
class RuleResult:
    """Output of a single AML rule."""

    rule_name: str
    triggered: bool
    weight: float  # 0.0-1.0 contribution to overall risk
    detail: str = ""


# ─── Rule implementations ──────────────────────────────────────────────────────


class AmountThresholdRule:
    """Flag transactions exceeding the reporting threshold."""

    RULE_NAME = "amount_threshold"
    DEFAULT_THRESHOLD = 10_000.0  # USD equivalent

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold

    def evaluate(self, amount: float, currency: str) -> RuleResult:
        # Simplified: treat all currencies as comparable for threshold
        if currency != "USD":
            # In production, convert via FX rate feed
            converted = amount * 1.0  # placeholder — use real FX in prod
        else:
            converted = amount

        triggered = converted >= self._threshold
        weight = min(converted / (self._threshold * 5), 1.0) if triggered else 0.0
        return RuleResult(
            rule_name=self.RULE_NAME,
            triggered=triggered,
            weight=weight,
            detail=f"Amount {amount} {currency} exceeds threshold ${self._threshold}",
        )


class StructuringRule:
    """Detect structuring (smurfing): many small transactions just below threshold."""

    RULE_NAME = "structuring"
    DEFAULT_THRESHOLD = 9_000.0
    DEFAULT_WINDOW_MINUTES = 1440  # 24 hours
    DEFAULT_MAX_COUNT = 3

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        window_minutes: int = DEFAULT_WINDOW_MINUTES,
        max_count: int = DEFAULT_MAX_COUNT,
    ) -> None:
        self._threshold = threshold
        self._window = timedelta(minutes=window_minutes)
        self._max_count = max_count
        # In production, query PostgreSQL for sender's recent transactions
        self._recent_txns: list[tuple[datetime, float]] = []

    def add_transaction(self, ts: datetime, amount: float) -> None:
        """Track a transaction for structuring analysis."""
        self._recent_txns.append((ts, amount))
        # Prune old entries
        self._recent_txns = [
            (t, a) for t, a in self._recent_txns if ts - t <= self._window
        ]

    def evaluate(self, sender_id: str, current_amount: float, current_ts: datetime) -> RuleResult:
        """Check if current transaction is part of a structuring pattern."""
        # Sum transactions just below threshold in the window
        below_threshold = [
            a for t, a in self._recent_txns
            if t <= current_ts and 0 < a < self._threshold
        ]
        total_below = sum(below_threshold) + current_amount
        count = len(below_threshold) + 1  # includes current

        triggered = count >= self._max_count and total_below >= self._threshold
        weight = min(count / (self._max_count * 2), 1.0) if triggered else 0.0
        return RuleResult(
            rule_name=self.RULE_NAME,
            triggered=triggered,
            weight=weight,
            detail=f"{count} transactions below ${self._threshold} in 24h, total ${total_below:.2f}",
        )


class HighRiskJurisdictionRule:
    """Flag transactions involving high-risk / sanctioned jurisdictions."""

    RULE_NAME = "high_risk_jurisdiction"

    def evaluate(self, countries: list[str]) -> RuleResult:
        flagged = [c for c in countries if c.upper() in HIGH_RISK_JURISDICTIONS]
        if flagged:
            weight = min(len(flagged) * 0.5, 1.0)
            return RuleResult(
                rule_name=self.RULE_NAME,
                triggered=True,
                weight=weight,
                detail=f"High-risk jurisdiction(s): {', '.join(flagged)}",
            )
        return RuleResult(rule_name=self.RULE_NAME, triggered=False, weight=0.0)


class VelocityRule:
    """Detect unusually high transaction frequency."""

    RULE_NAME = "velocity"
    DEFAULT_MAX_PER_HOUR = 5
    DEFAULT_MAX_PER_DAY = 10

    def __init__(
        self,
        max_per_hour: int = DEFAULT_MAX_PER_HOUR,
        max_per_day: int = DEFAULT_MAX_PER_DAY,
    ) -> None:
        self._max_hour = max_per_hour
        self._max_day = max_per_day
        self._txns_by_sender: dict[str, list[datetime]] = {}

    def add_transaction(self, sender_id: str, ts: datetime) -> None:
        if sender_id not in self._txns_by_sender:
            self._txns_by_sender[sender_id] = []
        self._txns_by_sender[sender_id].append(ts)
        # Prune
        cutoff_24h = ts - timedelta(days=1)
        self._txns_by_sender[sender_id] = [
            t for t in self._txns_by_sender[sender_id] if t > cutoff_24h
        ]

    def evaluate(self, sender_id: str, current_ts: datetime) -> RuleResult:
        txns = self._txns_by_sender.get(sender_id, [])
        one_hour_ago = current_ts - timedelta(hours=1)
        hour_count = sum(1 for t in txns if t > one_hour_ago)
        day_count = len(txns)

        triggered = hour_count >= self._max_hour or day_count >= self._max_day
        if triggered:
            weight = max(hour_count / self._max_hour, day_count / self._max_day)
            weight = min(weight, 1.0)
            return RuleResult(
                rule_name=self.RULE_NAME,
                triggered=True,
                weight=weight,
                detail=f"Velocity: {hour_count}/hr, {day_count}/day (limits: {self._max_hour}/{self._max_day})",
            )
        return RuleResult(rule_name=self.RULE_NAME, triggered=False, weight=0.0)


class RoundTripRule:
    """Detect round-trip transactions: sender and receiver are the same entity."""

    RULE_NAME = "round_trip"

    def evaluate(self, sender_id: str, receiver_id: str) -> RuleResult:
        if sender_id and receiver_id and sender_id == receiver_id:
            return RuleResult(
                rule_name=self.RULE_NAME,
                triggered=True,
                weight=0.9,
                detail=f"Same entity as sender and receiver: {sender_id}",
            )
        return RuleResult(rule_name=self.RULE_NAME, triggered=False, weight=0.0)


# ─── Rule Registry ─────────────────────────────────────────────────────────────


@dataclass
class RuleEngine:
    """Collection of all AML screening rules."""

    amount_rule: AmountThresholdRule = field(default_factory=AmountThresholdRule)
    structuring_rule: StructuringRule = field(default_factory=StructuringRule)
    jurisdiction_rule: HighRiskJurisdictionRule = field(default_factory=HighRiskJurisdictionRule)
    velocity_rule: VelocityRule = field(default_factory=VelocityRule)
    roundtrip_rule: RoundTripRule = field(default_factory=RoundTripRule)

    def add_transaction(
        self,
        sender_id: str,
        ts: datetime,
        amount: float,
    ) -> None:
        """Record a transaction for stateful rules (structuring, velocity)."""
        self.structuring_rule.add_transaction(ts, amount)
        self.velocity_rule.add_transaction(sender_id, ts)

    def evaluate(
        self,
        amount: float,
        currency: str,
        sender_id: str,
        sender_country: str,
        receiver_id: str,
        receiver_country: str,
        current_ts: datetime | None = None,
    ) -> tuple[list[RuleResult], float]:
        """Run all rules and return (results, aggregate risk_score)."""
        if current_ts is None:
            current_ts = datetime.now(timezone.utc)
        results: list[RuleResult] = []

        results.append(self.amount_rule.evaluate(amount, currency))
        results.append(self.jurisdiction_rule.evaluate([sender_country, receiver_country]))
        results.append(self.roundtrip_rule.evaluate(sender_id, receiver_id))
        results.append(self.velocity_rule.evaluate(sender_id, current_ts))
        results.append(self.structuring_rule.evaluate(sender_id, amount, current_ts))

        # Aggregate: weighted sum, capped at 1.0
        total = sum(r.weight for r in results if r.triggered)
        risk_score = min(total, 1.0)

        return results, risk_score
