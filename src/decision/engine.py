"""Decision engine for real-time payment screening.

Aggregates trail analysis, AML screening, and verification signals
into a final APPROVE/REVIEW/BLOCK decision with confidence score.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── Policy Configuration ─────────────────────────────────────────────────────


class DecisionPolicy:
    """Configurable risk thresholds for decision enforcement."""

    BLOCK_THRESHOLD: float = 0.8
    REVIEW_THRESHOLD: float = 0.5
    HIGH_RISK_COUNTERPARTY_WEIGHT: float = 0.15
    SANCTIONS_MATCH_WEIGHT: float = 0.4
    CIRCULAR_FLOW_WEIGHT: float = 0.3
    STRUCTURING_WEIGHT: float = 0.2
    LAYERING_WEIGHT: float = 0.25
    SHELL_COMPANY_WEIGHT: float = 0.35

    def __init__(
        self,
        block_threshold: float | None = None,
        review_threshold: float | None = None,
        **weights: float,
    ) -> None:
        if block_threshold is not None:
            self.BLOCK_THRESHOLD = block_threshold
        if review_threshold is not None:
            self.REVIEW_THRESHOLD = review_threshold
        for key, value in weights.items():
            setattr(self, f"{key.upper()}_WEIGHT", value)


# ─── Decision Engine ──────────────────────────────────────────────────────────


class DecisionEngine:
    """Aggregates all risk signals and enforces policy to produce final decisions."""

    def __init__(self, policy: Optional[DecisionPolicy] = None) -> None:
        self._policy = policy or DecisionPolicy()

    async def decide(
        self,
        payment_id: str,
        trail_analysis: dict[str, Any],
        screening_result: dict[str, Any],
        verification_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the full decision pipeline.

        Args:
            payment_id: Unique payment identifier
            trail_analysis: Result from MoneyTrailEngine
            screening_result: Result from ScreeningEngine
            verification_result: Result from VerificationPipeline

        Returns:
            Decision dict with APPROVE/REVIEW/BLOCK, confidence, reasoning, evidence
        """
        logger.info("Running decision engine for payment %s", payment_id)

        # ── Phase 1: Score aggregation ──────────────────────────────────
        risk_score = self._aggregate_risk(
            trail_analysis=trail_analysis,
            screening_result=screening_result,
            verification_result=verification_result,
        )

        # ── Phase 2: Policy enforcement ─────────────────────────────────
        decision, confidence, reasoning = self._enforce_policy(risk_score, trail_analysis, screening_result, verification_result)

        # ── Phase 3: Evidence collection ────────────────────────────────
        evidence = self._collect_evidence(trail_analysis, screening_result, verification_result, decision)

        # ── Phase 4: Final output ───────────────────────────────────────
        result = {
            "payment_id": payment_id,
            "decision": decision,
            "confidence": round(confidence, 4),
            "risk_score": round(risk_score, 4),
            "reasoning": reasoning,
            "evidence": evidence,
            "policy": {
                "block_threshold": self._policy.BLOCK_THRESHOLD,
                "review_threshold": self._policy.REVIEW_THRESHOLD,
            },
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "Decision for %s: %s (score=%.4f, confidence=%.4f)",
            payment_id,
            decision,
            risk_score,
            confidence,
        )
        return result

    def _aggregate_risk(
        self,
        trail_analysis: dict[str, Any],
        screening_result: dict[str, Any],
        verification_result: dict[str, Any],
    ) -> float:
        """Combine risk signals from all sources into a single score."""
        score = 0.0

        # Trail risk (0-1)
        trail_score = trail_analysis.get("aggregated_risk_score", 0.0)
        score += trail_score * 0.35  # Trail is 35% of total

        # Screening risk (0-1)
        screening_score = screening_result.get("risk_score", 0.0)
        score += screening_score * 0.25  # Screening is 25% of total

        # Verification risk (from confidence inverse)
        ver_confidence = verification_result.get("confidence", 0.5)
        ver_risk = 1.0 - ver_confidence  # Low confidence = higher risk
        score += ver_risk * 0.15  # Verification is 15% of total

        # Policy-weighted flags
        trail_flags = trail_analysis.get("flags", {})
        if trail_flags.get("circular_flow"):
            score += self._policy.CIRCULAR_FLOW_WEIGHT
        if trail_flags.get("structuring"):
            score += self._policy.STRUCTURING_WEIGHT
        if trail_flags.get("layering_detected"):
            score += self._policy.LAYERING_WEIGHT
        if trail_flags.get("high_risk_counterparties"):
            score += min(self._policy.HIGH_RISK_COUNTERPARTY_WEIGHT * len(trail_flags["high_risk_counterparties"]), 0.3)
        if trail_flags.get("sanctions_matches"):
            score += self._policy.SANCTIONS_MATCH_WEIGHT

        screening_flags = screening_result.get("flags", [])
        if screening_flags:
            score += min(0.1 * len(screening_flags), 0.2)

        # Clamp to [0, 1]
        return min(1.0, max(0.0, score))

    def _enforce_policy(
        self,
        risk_score: float,
        trail_analysis: dict[str, Any],
        screening_result: dict[str, Any],
        verification_result: dict[str, Any],
    ) -> tuple[str, float, str]:
        """Apply policy thresholds to produce final decision."""
        block_threshold = self._policy.BLOCK_THRESHOLD
        review_threshold = self._policy.REVIEW_THRESHOLD

        # Hard block: sanctions match or very high risk
        trail_flags = trail_analysis.get("flags", {})
        if trail_flags.get("sanctions_matches"):
            return "BLOCK", 0.95, "Sanctions match detected — automatic block per policy"

        if risk_score >= block_threshold:
            return (
                "BLOCK",
                round(risk_score, 4),
                f"Risk score {risk_score:.4f} exceeds block threshold {block_threshold:.4f}",
            )

        if risk_score >= review_threshold:
            return (
                "REVIEW",
                round(1.0 - risk_score, 4),
                f"Risk score {risk_score:.4f} in review zone [{review_threshold:.4f}, {block_threshold:.4f}]",
            )

        return (
            "APPROVE",
            round(1.0 - risk_score, 4),
            f"Risk score {risk_score:.4f} within acceptable range",
        )

    def _collect_evidence(
        self,
        trail_analysis: dict[str, Any],
        screening_result: dict[str, Any],
        verification_result: dict[str, Any],
        decision: str,
    ) -> list[str]:
        """Collect evidence supporting the decision."""
        evidence = []

        # Trail evidence
        trail_flags = trail_analysis.get("flags", {})
        if trail_flags.get("circular_flow"):
            evidence.append("Circular money flow detected in transaction graph")
        if trail_flags.get("structuring"):
            evidence.append("Structuring pattern: multiple small transactions below threshold")
        if trail_flags.get("sanctions_matches"):
            evidence.append(f"Sanctions matches: {', '.join(trail_flags.get('sanctions_matches', []))}")
        if trail_flags.get("high_risk_counterparties"):
            evidence.append(f"High-risk counterparties: {len(trail_flags['high_risk_counterparties'])} identified")

        # Screening evidence
        screening_flags = screening_result.get("flags", [])
        if screening_flags:
            evidence.append(f"AML screening flags: {', '.join(screening_flags)}")

        screening_entities = screening_result.get("matched_entities", [])
        if screening_entities:
            names = [e.get("name", "") for e in screening_entities]
            evidence.append(f"Watchlist matches: {', '.join(names)}")

        # Verification evidence
        ver_questions = verification_result.get("questions_asked", 0)
        ver_answers = verification_result.get("questions_answered", 0)
        if ver_questions > 0:
            evidence.append(f"Verification: {ver_answers}/{ver_questions} questions resolved")

        return evidence


# Module-level singleton
_decision_engine = DecisionEngine()
