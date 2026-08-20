"""Unit tests for the Fraud Alert Triage Agent."""

from __future__ import annotations

from src.fraud.alert_triage import MockTriageAgent
from src.fraud.schemas import TriageReport


def test_triage_dismiss_low_severity() -> None:
    agent = MockTriageAgent()
    report = agent.triage(
        alert_id="alt_001",
        transaction_id="tx_001",
        severity="LOW",
        context={"amount": 100.0},
    )
    assert report.recommendation == "DISMISS"
    assert report.confidence < 0.5


def test_triage_escalate_high_severity() -> None:
    agent = MockTriageAgent()
    report = agent.triage(
        alert_id="alt_002",
        transaction_id="tx_002",
        severity="HIGH",
        context={"amount": 50000.0},
    )
    assert report.recommendation == "ESCALATE"
    assert report.confidence >= 0.5
    assert any("High-value" in e for e in report.evidence)


def test_triage_investigate_medium() -> None:
    agent = MockTriageAgent()
    report = agent.triage(
        alert_id="alt_003",
        transaction_id="tx_003",
        severity="MEDIUM",
        context={"amount": 15000.0},
    )
    assert report.recommendation in ("INVESTIGATE", "ESCALATE")
    assert len(report.evidence) > 0


def test_triage_report_structure() -> None:
    agent = MockTriageAgent()
    report = agent.triage("alt_004", "tx_004", "CRITICAL", {"amount": 100000.0})
    assert isinstance(report, TriageReport)
    assert report.alert_id == "alt_004"
    assert report.transaction_id == "tx_004"
    assert report.confidence > 0
    assert report.risk_dossier  # non-empty dossier
