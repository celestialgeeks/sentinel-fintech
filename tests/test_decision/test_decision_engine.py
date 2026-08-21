"""Tests for the decision engine."""

from __future__ import annotations

import pytest

from src.decision.engine import DecisionEngine, DecisionPolicy


class TestDecisionEngine:
    """Tests for DecisionEngine."""

    @pytest.mark.asyncio
    async def test_approve_low_risk(self) -> None:
        engine = DecisionEngine()
        result = await engine.decide(
            payment_id="low_risk_001",
            trail_analysis={
                "aggregated_risk_score": 0.1,
                "flags": {"circular_flow": False, "structuring": False, "sanctions_matches": []},
            },
            screening_result={
                "risk_score": 0.05,
                "flags": [],
                "matched_entities": [],
            },
            verification_result={
                "confidence": 0.9,
                "questions_asked": 0,
                "questions_answered": 0,
            },
        )
        assert result["decision"] == "APPROVE"
        assert result["risk_score"] < 0.5

    @pytest.mark.asyncio
    async def test_block_high_risk(self) -> None:
        engine = DecisionEngine()
        result = await engine.decide(
            payment_id="high_risk_001",
            trail_analysis={
                "aggregated_risk_score": 0.9,
                "flags": {"circular_flow": True, "structuring": False, "sanctions_matches": []},
            },
            screening_result={
                "risk_score": 0.85,
                "flags": ["high_risk_jurisdiction"],
                "matched_entities": [],
            },
            verification_result={
                "confidence": 0.3,
                "questions_asked": 2,
                "questions_answered": 1,
            },
        )
        assert result["decision"] == "BLOCK"
        assert result["risk_score"] >= 0.8

    @pytest.mark.asyncio
    async def test_block_on_sanctions(self) -> None:
        engine = DecisionEngine()
        result = await engine.decide(
            payment_id="sanctions_001",
            trail_analysis={
                "aggregated_risk_score": 0.3,
                "flags": {"sanctions_matches": ["AHMAD, Mohammed"]},
            },
            screening_result={"risk_score": 0.2, "flags": [], "matched_entities": []},
            verification_result={"confidence": 0.8, "questions_asked": 0, "questions_answered": 0},
        )
        assert result["decision"] == "BLOCK"
        assert "Sanctions match" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_review_mid_risk(self) -> None:
        engine = DecisionEngine()
        result = await engine.decide(
            payment_id="review_001",
            trail_analysis={
                "aggregated_risk_score": 0.8,
                "flags": {"circular_flow": False, "structuring": False, "sanctions_matches": []},
            },
            screening_result={
                "risk_score": 0.75,
                "flags": ["high_risk_country"],
                "matched_entities": [],
            },
            verification_result={
                "confidence": 0.4,
                "questions_asked": 1,
                "questions_answered": 1,
            },
        )
        assert result["decision"] == "REVIEW"

    @pytest.mark.asyncio
    async def test_custom_policy(self) -> None:
        policy = DecisionPolicy(block_threshold=0.9, review_threshold=0.7)
        engine = DecisionEngine(policy=policy)
        result = await engine.decide(
            payment_id="custom_001",
            trail_analysis={"aggregated_risk_score": 1.0, "flags": {}},
            screening_result={"risk_score": 1.0, "flags": ["high_risk_country"], "matched_entities": []},
            verification_result={"confidence": 0.1, "questions_asked": 0, "questions_answered": 0},
        )
        # Score ≈ 0.35 + 0.35 + 0.135 = 0.835, above review=0.7 but below block=0.9
        assert result["decision"] == "REVIEW"

    def test_evidence_collection(self) -> None:
        engine = DecisionEngine()
        evidence = engine._collect_evidence(
            trail_analysis={
                "flags": {
                    "circular_flow": True,
                    "sanctions_matches": ["Entity A"],
                    "high_risk_counterparties": ["Entity B"],
                }
            },
            screening_result={"flags": ["rule_triggered"], "matched_entities": [{"name": "Entity A"}]},
            verification_result={"questions_asked": 2, "questions_answered": 1},
            decision="BLOCK",
        )
        assert len(evidence) >= 3
        assert any("Circular" in e for e in evidence)
        assert any("Sanctions" in e for e in evidence)
