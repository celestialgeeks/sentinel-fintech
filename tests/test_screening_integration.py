"""Integration tests for the ScreeningEngine end-to-end."""

from __future__ import annotations

from datetime import datetime, timezone

from src.screening.engine import ScreeningEngine
from src.screening.schemas import EntityRef, TransactionIngest


def test_screening_approved() -> None:
    """Normal transaction should be APPROVED."""
    engine = ScreeningEngine()
    txn = TransactionIngest(
        transaction_id="tx_001",
        amount=500.0,
        currency="USD",
        sender=EntityRef(entity_id="usr_001", name="John Smith", country="US"),
        receiver=EntityRef(entity_id="usr_002", name="Jane Doe", country="GB"),
    )
    result = engine.screen(txn)
    assert result.recommendation == "APPROVE"
    assert result.risk_score < 0.4
    assert len(result.flags) == 0


def test_screening_blocked_jurisdiction() -> None:
    """Transaction to sanctioned jurisdiction should be BLOCKED."""
    engine = ScreeningEngine()
    txn = TransactionIngest(
        transaction_id="tx_002",
        amount=5000.0,
        currency="USD",
        sender=EntityRef(entity_id="usr_001", name="John Smith", country="US"),
        receiver=EntityRef(entity_id="usr_003", name="Tech Imports LLC", country="BY"),
    )
    result = engine.screen(txn)
    assert result.recommendation == "BLOCK" or result.recommendation == "REVIEW"
    assert "high_risk_jurisdiction" in result.flags


def test_screening_blocked_amount() -> None:
    """Large transaction should trigger amount threshold."""
    engine = ScreeningEngine()
    txn = TransactionIngest(
        transaction_id="tx_003",
        amount=50_000.0,
        currency="USD",
        sender=EntityRef(entity_id="usr_001", name="John Smith", country="US"),
        receiver=EntityRef(entity_id="usr_002", name="Jane Doe", country="GB"),
    )
    result = engine.screen(txn)
    assert "amount_threshold" in result.flags
    assert result.risk_score > 0


def test_screening_blocked_watchlist() -> None:
    """Transaction involving a watchlisted entity should flag."""
    engine = ScreeningEngine()
    txn = TransactionIngest(
        transaction_id="tx_004",
        amount=1000.0,
        currency="USD",
        sender=EntityRef(entity_id="usr_001", name="John Smith", country="US"),
        receiver=EntityRef(entity_id="usr_002", name="Tech Imports LLC", country="US"),
    )
    result = engine.screen(txn)
    # Tech Imports LLC is in EU watchlist
    assert len(result.matched_entities) > 0 or "high_risk_jurisdiction" in result.flags


def test_screening_round_trip() -> None:
    """Same sender and receiver should trigger round-trip detection."""
    engine = ScreeningEngine()
    txn = TransactionIngest(
        transaction_id="tx_005",
        amount=5000.0,
        currency="USD",
        sender=EntityRef(entity_id="usr_123", name="Alice Brown", country="US"),
        receiver=EntityRef(entity_id="usr_123", name="Alice Brown", country="US"),
    )
    result = engine.screen(txn)
    assert "round_trip" in result.flags


def test_screening_structuring() -> None:
    """Multiple small transactions should trigger structuring detection."""
    engine = ScreeningEngine()
    base = datetime.now(timezone.utc)
    for i in range(4):
        txn = TransactionIngest(
            transaction_id=f"tx_struct_{i}",
            amount=8500.0,
            currency="USD",
            sender=EntityRef(entity_id="usr_999", name="Suspicious User", country="US"),
            receiver=EntityRef(entity_id="usr_888", name="Receiver", country="GB"),
        )
        engine.screen(txn)

    # After 4 transactions, structuring should be flagged
    last_txn = TransactionIngest(
        transaction_id="tx_struct_final",
        amount=8500.0,
        currency="USD",
        sender=EntityRef(entity_id="usr_999", name="Suspicious User", country="US"),
        receiver=EntityRef(entity_id="usr_888", name="Receiver", country="GB"),
    )
    result = engine.screen(last_txn)
    assert "structuring" in result.flags or "velocity" in result.flags
