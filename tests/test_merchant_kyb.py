"""Unit tests for KYB verification and risk scoring."""

from __future__ import annotations

from src.merchant.kyb import KYBVerifier
from src.merchant.risk_scoring import RiskScorer


def test_kyb_verify_clean_document() -> None:
    """Clean document with all fields should pass verification."""
    verifier = KYBVerifier()
    extracted = {
        "business_name": "Acme Corp",
        "registration_number": "U12345MH2020PTC123456",
        "address": "123 Main St, Mumbai",
        "risk_indicators": [],
        "industry": "technology",
    }
    result = verifier.verify(extracted, "IN")
    assert result["verified"] is True
    assert result["risk_level"] == "LOW"


def test_kyb_verify_missing_fields() -> None:
    """Document missing critical fields should fail verification."""
    verifier = KYBVerifier()
    extracted = {
        "business_name": "",
        "risk_indicators": ["sanction"],
        "industry": "crypto",
    }
    result = verifier.verify(extracted, "US")
    assert result["verified"] is False
    assert result["risk_level"] == "HIGH"


def test_risk_scorer_low_risk() -> None:
    """Low-risk merchant should get APPROVE recommendation."""
    scorer = RiskScorer()
    result = scorer.score(
        business_name="Acme Corp",
        country="US",
        industry="Technology",
        doc_verification={"verification_score": 0.9, "verified": True},
        web_reputation_score = 0.8,
        sanctions_check=False,
    )
    assert result["recommendation"] == "APPROVE"
    assert result["composite_score"] < 0.3


def test_risk_scorer_high_risk() -> None:
    """High-risk merchant should get REJECT recommendation."""
    scorer = RiskScorer()
    result = scorer.score(
        business_name="Suspicious Ltd",
        country="IR",
        industry="Crypto",
        doc_verification={"verification_score": 0.2, "verified": False},
        web_reputation_score=0.2,
        sanctions_check=True,
    )
    assert result["recommendation"] == "REJECT"
    assert result["composite_score"] > 0.6


def test_risk_scorer_medium_risk() -> None:
    """Medium-risk merchant should get REVIEW or APPROVE recommendation."""
    scorer = RiskScorer()
    result = scorer.score(
        business_name="MidRisk Inc",
        country="US",
        industry="E-commerce",
        doc_verification={"verification_score": 0.6, "verified": True},
        web_reputation_score=0.5,
        sanctions_check=False,
    )
    # Score depends on weights — could be APPROVE or REVIEW
    assert result["recommendation"] in ("APPROVE", "REVIEW")
    assert result["composite_score"] > 0


def test_risk_components_breakdown() -> None:
    """Risk report should contain all component breakdowns."""
    scorer = RiskScorer()
    result = scorer.score("Test Co", "US", "Retail")
    names = {c["name"] for c in result["components"]}
    assert "geographic_risk" in names
    assert "industry_risk" in names
    assert "sanctions_screening" in names
