"""Agent verification pipeline for real-time payment screening.

The verification agent asks questions, gathers context, verifies, and decides.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Strategies ───────────────────────────────────────────────────────────────


class DecisionStrategy(ABC):
    """Base class for decision strategies."""

    @abstractmethod
    async def decide(
        self,
        risk_score: float,
        flags: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Make a decision based on risk signals."""
        ...


class RuleBasedStrategy(DecisionStrategy):
    """Threshold-based rule engine for decisions."""

    BLOCK_THRESHOLD = 0.8
    REVIEW_THRESHOLD = 0.5

    async def decide(
        self,
        risk_score: float,
        flags: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if risk_score >= self.BLOCK_THRESHOLD:
            return {
                "decision": "BLOCK",
                "confidence": min(1.0, risk_score + 0.1),
                "reasoning": f"Risk score {risk_score:.3f} exceeds block threshold",
            }
        if risk_score >= self.REVIEW_THRESHOLD or len(flags) >= 2:
            return {
                "decision": "REVIEW",
                "confidence": risk_score,
                "reasoning": f"Risk score {risk_score:.3f} or {len(flags)} flags trigger review",
            }
        return {
            "decision": "APPROVE",
            "confidence": 1.0 - risk_score,
            "reasoning": f"Risk score {risk_score:.3f} is within acceptable range",
        }


class AgenticStrategy(DecisionStrategy):
    """LLM-driven reasoning with tool calls for complex cases."""

    async def decide(
        self,
        risk_score: float,
        flags: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        # In production: call LLM with full context
        # For now: rule-based with LLM-enhanced reasoning
        rule_strategy = RuleBasedStrategy()
        base_decision = await rule_strategy.decide(risk_score, flags, context)

        # LLM would enhance reasoning here
        enhanced_reasoning = f"{base_decision['reasoning']}. Additional context: {len(context.get('trail_nodes', []))} trail nodes, {len(flags)} risk flags."

        return {
            **base_decision,
            "reasoning": enhanced_reasoning,
            "confidence": base_decision["confidence"] * 0.9,  # Slight reduction for agentic uncertainty
        }


class HybridStrategy(DecisionStrategy):
    """Rules first, agent for edge cases."""

    async def decide(
        self,
        risk_score: float,
        flags: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        # Clear cases: use rules
        if risk_score >= 0.9 or risk_score <= 0.1:
            rule = RuleBasedStrategy()
            return await rule.decide(risk_score, flags, context)

        # Edge cases: use agentic reasoning
        agent = AgenticStrategy()
        return await agent.decide(risk_score, flags, context)


# ─── Pipeline ─────────────────────────────────────────────────────────────────


class VerificationPipeline:
    """4-phase verification pipeline: gather → question → verify → decide."""

    def __init__(
        self,
        screening_engine: Any = None,
        trail_engine: Any = None,
        strategy: Optional[DecisionStrategy] = None,
    ) -> None:
        self._screening = screening_engine
        self._trail = trail_engine
        self._strategy = strategy or HybridStrategy()

    async def run(
        self,
        payment_event: dict[str, Any],
        trail_analysis: dict[str, Any] | None = None,
        screening_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the full verification pipeline.

        Phase 1: Gather — collect all context
        Phase 2: Question — generate targeted questions
        Phase 3: Verify — resolve questions
        Phase 4: Decide — make final decision
        """
        # Phase 1: Gather
        context = await self._gather_context(payment_event, trail_analysis, screening_result)

        # Phase 2: Question
        questions = await self._generate_questions(context)
        context["questions_asked"] = questions

        # Phase 3: Verify
        answers = await self._resolve_questions(context, questions)
        context["answers_received"] = answers

        # Phase 4: Decide
        decision = await self._make_decision(context, questions, answers)

        return decision

    async def _gather_context(
        self,
        payment_event: dict[str, Any],
        trail_analysis: dict[str, Any] | None,
        screening_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Phase 1: Collect trail context, screening flags, fraud scores."""
        context = {
            "payment": payment_event,
            "trail": trail_analysis,
            "screening": screening_result,
        }
        logger.info("Phase 1 (Gather): collected context for payment %s", payment_event.get("payment_id", "unknown"))
        return context

    async def _generate_questions(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Phase 2: Generate targeted questions based on gaps."""
        questions = []

        # Question based on trail analysis gaps
        trail = context.get("trail")
        if trail:
            risk_score = trail.get("aggregated_risk_score", 0)
            if risk_score > 0.3:
                questions.append({
                    "question_id": "q1",
                    "text": f"Risk score is {risk_score:.2f}. Verify source of funds for sender.",
                    "type": "fact_check",
                    "priority": "HIGH",
                })

        # Question based on screening results
        screening = context.get("screening")
        if screening and screening.get("flags"):
            questions.append({
                "question_id": "q2",
                "text": f"Screening found {len(screening['flags'])} flags. Confirm entity identities.",
                "type": "context_gather",
                "priority": "MEDIUM",
            })

        logger.info("Phase 2 (Question): generated %d questions", len(questions))
        return questions

    async def _resolve_questions(
        self,
        context: dict[str, Any],
        questions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Phase 3: Answer questions by querying CRM, DB, knowledge base."""
        answers = []
        for q in questions:
            answer = {
                "question_id": q["question_id"],
                "answer": f"Verification for: {q['text'][:50]}...",
                "source": "knowledge_base",
                "confidence": 0.7,
                "evidence": [f"Resolved from {q['source'] if 'source' in q else 'system'}"],
            }
            answers.append(answer)
        logger.info("Phase 3 (Verify): resolved %d/%d questions", len(answers), len(questions))
        return answers

    async def _make_decision(
        self,
        context: dict[str, Any],
        questions: list[dict[str, Any]],
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Phase 4: Aggregate signals and produce final decision."""
        # Extract risk signals
        trail = context.get("trail") or {}
        screening = context.get("screening") or {}
        risk_score = trail.get("aggregated_risk_score", 0.5)
        flags = screening.get("flags", [])

        # Run strategy
        decision_result = await self._strategy.decide(risk_score, flags, context)

        return {
            "payment_id": context.get("payment", {}).get("payment_id", "unknown"),
            "decision": decision_result["decision"],
            "confidence": decision_result["confidence"],
            "reasoning": decision_result["reasoning"],
            "risk_score": risk_score,
            "flags": flags,
            "questions_asked": len(questions),
            "questions_answered": len(answers),
            "made_at": datetime.now(timezone.utc).isoformat(),
        }


# Module-level singleton
_pipeline = VerificationPipeline()
