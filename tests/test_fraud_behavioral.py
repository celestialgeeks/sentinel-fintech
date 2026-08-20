"""Unit tests for behavioral profiling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.fraud.behavioral import BehavioralProfiling


def test_amount_z_score_normal() -> None:
    """Normal transaction should have low z-score."""
    bp = BehavioralProfiling()
    base = datetime.now(timezone.utc)
    for i in range(10):
        bp.record_transaction("usr_1", base + timedelta(minutes=i * 10), 100.0, "US")
    z = bp.amount_z_score("usr_1", 105.0)
    assert z < 1.0


def test_amount_z_score_anomaly() -> None:
    """Large deviation from baseline should have high z-score."""
    bp = BehavioralProfiling()
    base = datetime.now(timezone.utc)
    # Record varied transactions around $100 mean
    for i, amt in enumerate([90, 110, 95, 105, 100, 88, 112, 97, 103, 99]):
        bp.record_transaction("usr_2", base + timedelta(minutes=i * 10), float(amt), "US")
    z = bp.amount_z_score("usr_2", 5000.0)
    assert z > 2.0


def test_velocity_check_normal() -> None:
    """Few transactions should not trigger velocity check."""
    bp = BehavioralProfiling()
    base = datetime.now(timezone.utc)
    bp.record_transaction("usr_3", base, 100.0, "US")
    bp.record_transaction("usr_3", base + timedelta(minutes=30), 150.0, "US")
    anomaly, score = bp.velocity_check("usr_3", base + timedelta(minutes=45))
    assert not anomaly
    assert score == 0.0


def test_velocity_check_anomaly() -> None:
    """Many transactions in short window should trigger velocity check."""
    bp = BehavioralProfiling()
    base = datetime.now(timezone.utc)
    for i in range(7):
        bp.record_transaction("usr_4", base + timedelta(minutes=i * 5), 100.0, "US")
    anomaly, score = bp.velocity_check("usr_4", base + timedelta(minutes=35))
    assert anomaly
    assert score > 0


def test_geo_impossibility_new_user() -> None:
    """New user with no history should not trigger geo anomaly."""
    bp = BehavioralProfiling()
    bp.record_transaction("usr_5", datetime.now(timezone.utc), 500.0, "US")
    anomaly, score = bp.geo_impossibility_check("usr_5", "JP")
    assert not anomaly


def test_time_anomaly_new_user() -> None:
    """New user with no typical hours should not trigger time anomaly."""
    bp = BehavioralProfiling()
    bp.record_transaction("usr_6", datetime.now(timezone.utc), 100.0, "US")
    anomaly, score = bp.time_of_day_anomaly("usr_6")
    assert not anomaly
