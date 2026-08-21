"""Tests for the verification pipeline."""

from __future__ import annotations

import pytest

from src.verification.pipeline import VerificationPipeline
from src.verification.strategies import RuleBasedStrategy, AgenticStrategy, HybridStrategy


class TestDecisionStrategies:
    """Tests for decision strategies."""

    @pytest.mark.asyncio
    async def test_rule_based_approve(self) -> None:
        strategy = RuleBasedStrategy()
        result = await strategy.decide(0.2, [], {})
        assert result["decision"] == "APPROVE"
        assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_rule_based_review(self) -> None:
        strategy = RuleBasedStrategy()
        result = await strategy.decide(0.6, ["flag1"], {})
        assert result["decision"] == "REVIEW"

    @pytest.mark.asyncio
    async def test_rule_based_block(self) -> None:
        strategy = RuleBasedStrategy()
        result = await strategy.decide(0.85, [], {})
        assert result["decision"] == "BLOCK"
        assert result["confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_agentic_strategy(self) -> None:
        strategy = AgenticStrategy()
        result = await strategy.decide(0.6, ["flag1"], {"trail_nodes": 5})
        assert result["decision"] == "REVIEW"
        assert "LLM-enhanced" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_hybrid_clear_case(self) -> None:
        strategy = HybridStrategy()
        # Clear case (score <= 0.1) should use rule-based
        result = await strategy.decide(0.05, [], {})
        assert result["decision"] == "APPROVE"

    @pytest.mark.asyncio
    async def test_hybrid_edge_case(self) -> None:
        strategy = HybridStrategy()
        # Edge case (0.1 < score < 0.9) should use agentic
        result = await strategy.decide(0.5, ["flag1"], {})
        assert result["decision"] == "REVIEW"


class TestVerificationPipeline:
    """Tests for the verification pipeline."""

    @pytest.mark.asyncio
    async def test_run_pipeline(self) -> None:
        pipeline = VerificationPipeline()
        result = await pipeline.run(
            payment_event={
                "payment_id": "test_001",
                "amount": 5000.0,
                "currency": "USD",
                "sender": {"entity_id": "s1", "name": "Alice", "country": "US"},
                "receiver": {"entity_id": "r1", "name": "Bob", "country": "UK"},
            },
            trail_analysis={
                "aggregated_risk_score": 0.3,
                "flags": {},
                "nodes": [],
            },
            screening_result={
                "risk_score": 0.2,
                "flags": [],
                "matched_entities": [],
            },
        )
        assert "decision" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert result["payment_id"] == "test_001"

    @pytest.mark.asyncio
    async def test_run_pipeline_high_risk(self) -> None:
        pipeline = VerificationPipeline()
        result = await pipeline.run(
            payment_event={
                "payment_id": "test_002",
                "amount": 50000.0,
                "currency": "USD",
                "sender": {"entity_id": "s1", "name": "Alice", "country": "IR"},
                "receiver": {"entity_id": "r1", "name": "Bob", "country": "KP"},
            },
            trail_analysis={
                "aggregated_risk_score": 0.8,
                "flags": {"circular_flow": True},
                "nodes": [],
            },
            screening_result={
                "risk_score": 0.9,
                "flags": ["sanctions_match", "high_risk_country"],
                "matched_entities": [{"name": "Entity X"}],
            },
        )
        assert result["decision"] in ("REVIEW", "BLOCK")
        assert result["risk_score"] > 0.5

    @pytest.mark.asyncio
    async def test_gather_context(self) -> None:
        pipeline = VerificationPipeline()
        context = await pipeline._gather_context(
            payment_event={"payment_id": "p1"},
            trail_analysis={"risk_score": 0.5},
            screening_result={"flags": ["f1"]},
        )
        assert context["payment"]["payment_id"] == "p1"
        assert context["trail"]["risk_score"] == 0.5

    @pytest.mark.asyncio
    async def test_generate_questions(self) -> None:
        pipeline = VerificationPipeline()
        context = {
            "trail": {"aggregated_risk_score": 0.6},
            "screening": {"flags": ["flag1", "flag2"]},
        }
        questions = await pipeline._generate_questions(context)
        assert len(questions) >= 1
        assert any(q["priority"] == "HIGH" for q in questions)
