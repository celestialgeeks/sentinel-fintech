"""Decision strategies for the verification pipeline."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class DecisionStrategy(ABC):
    """Abstract base for decision strategies."""

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
        rule = RuleBasedStrategy()
        base = await rule.decide(risk_score, flags, context)
        return {
            **base,
            "reasoning": f"{base['reasoning']}. LLM-enhanced analysis.",
            "confidence": base["confidence"] * 0.9,
        }


class HybridStrategy(DecisionStrategy):
    """Rules first, agent for edge cases."""

    async def decide(
        self,
        risk_score: float,
        flags: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if risk_score >= 0.9 or risk_score <= 0.1:
            rule = RuleBasedStrategy()
            return await rule.decide(risk_score, flags, context)
        agent = AgenticStrategy()
        return await agent.decide(risk_score, flags, context)
