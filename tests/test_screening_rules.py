"""Unit tests for AML screening rules."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.screening.rules import (
    AmountThresholdRule,
    HighRiskJurisdictionRule,
    RoundTripRule,
    RuleEngine,
    StructuringRule,
    VelocityRule,
)


def test_amount_threshold_below() -> None:
    rule = AmountThresholdRule(threshold=10_000.0)
    result = rule.evaluate(5_000.0, "USD")
    assert not result.triggered
    assert result.weight == 0.0


def test_amount_threshold_above() -> None:
    rule = AmountThresholdRule(threshold=10_000.0)
    result = rule.evaluate(15_000.0, "USD")
    assert result.triggered
    assert result.weight > 0


def test_high_risk_jurisdiction() -> None:
    rule = HighRiskJurisdictionRule()
    result = rule.evaluate(["US", "IR"])
    assert result.triggered
    assert "IR" in result.detail


def test_no_high_risk_jurisdiction() -> None:
    rule = HighRiskJurisdictionRule()
    result = rule.evaluate(["US", "GB"])
    assert not result.triggered
    assert result.weight == 0.0


def test_round_trip() -> None:
    rule = RoundTripRule()
    result = rule.evaluate("usr_123", "usr_123")
    assert result.triggered
    assert result.weight == 0.9


def test_no_round_trip() -> None:
    rule = RoundTripRule()
    result = rule.evaluate("usr_123", "usr_456")
    assert not result.triggered


def test_structuring_detection() -> None:
    rule = StructuringRule(threshold=9_000.0, max_count=3, window_minutes=1440)
    base = datetime.utcnow()
    # Add 3 transactions just below threshold
    for i in range(3):
        rule.add_transaction(base + timedelta(minutes=i * 10), 8_500.0)
    result = rule.evaluate("usr_123", 8_500.0, base + timedelta(minutes=40))
    assert result.triggered


def test_velocity_detection() -> None:
    rule = VelocityRule(max_per_hour=5, max_per_day=10)
    base = datetime.utcnow()
    for i in range(6):
        rule.add_transaction("usr_123", base + timedelta(minutes=i * 5))
    result = rule.evaluate("usr_123", base + timedelta(minutes=35))
    assert result.triggered


def test_rule_engine_aggregation() -> None:
    engine = RuleEngine()
    base = datetime.utcnow()
    results, score = engine.evaluate(
        amount=15_000.0,
        currency="USD",
        sender_id="usr_123",
        sender_country="IR",
        receiver_id="usr_456",
        receiver_country="US",
        current_ts=base,
    )
    triggered = [r for r in results if r.triggered]
    assert len(triggered) >= 2  # amount + jurisdiction
    assert score > 0


def test_full_engine_no_trigger() -> None:
    engine = RuleEngine()
    results, score = engine.evaluate(
        amount=500.0,
        currency="USD",
        sender_id="usr_123",
        sender_country="US",
        receiver_id="usr_456",
        receiver_country="GB",
        current_ts=datetime.utcnow(),
    )
    triggered = [r for r in results if r.triggered]
    assert len(triggered) == 0
    assert score == 0.0
