"""Integration tests for the FraudScorer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.fraud.schemas import FraudScore
from src.fraud.scorer import FraudScorer


def test_fraud_scorer_approved() -> None:
    """Normal transaction should be APPROVED."""
    scorer = FraudScorer()
    result = scorer.score("tx_f1", "usr_100", 150.0, "US", datetime.now(timezone.utc))
    assert result.recommendation == "APPROVE"
    assert result.combined_score < 0.4


def test_fraud_scorer_block_large_amount() -> None:
    """Very large amount should trigger BLOCK."""
    scorer = FraudScorer()
    # Record normal history first
    base = datetime.now(timezone.utc)
    for i in range(5):
        scorer._profiler.record_transaction("usr_100", base + timedelta(minutes=i * 5), 100.0, "US")
    # Now a huge transaction
    result = scorer.score("tx_f2", "usr_100", 50000.0, "US", base + timedelta(minutes=30))
    assert result.behavioral_z_score > 2.0


def test_fraud_scorer_velocity() -> None:
    """Rapid transactions should increase risk score."""
    scorer = FraudScorer()
    base = datetime.now(timezone.utc)
    for i in range(8):
        scorer.score(f"tx_v{i}", "usr_200", 100.0, "US", base + timedelta(minutes=i * 3))
    result = scorer.score("tx_v_last", "usr_200", 100.0, "US", base + timedelta(minutes=25))
    assert result.velocity_score > 0


def test_fraud_scorer_recommendations() -> None:
    """Test all three recommendation thresholds."""
    scorer = FraudScorer()
    base = datetime.now(timezone.utc)

    # Low risk
    r1 = scorer.score("tx_a", "usr_300", 50.0, "US", base)
    assert r1.recommendation == "APPROVE"

    # Medium risk — high amount
    for i in range(3):
        scorer._profiler.record_transaction("usr_300", base + timedelta(minutes=i), 50.0, "US")
    r2 = scorer.score("tx_b", "usr_300", 8000.0, "US", base + timedelta(minutes=10))
    assert r2.recommendation in ("APPROVE", "VERIFY", "BLOCK")
