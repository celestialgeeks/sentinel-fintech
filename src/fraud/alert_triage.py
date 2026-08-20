"""Agentic fraud alert triage — LangChain-style investigation agent."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.fraud.schemas import TriageReport

logger = logging.getLogger(__name__)


class TriageAgent:
    """Investigates fraud alerts by querying multiple data sources."""

    def __init__(
        self,
        profiler: Any = None,
        graph_client: Any = None,
        ip_reputation: dict[str, float] | None = None,
    ) -> None:
        self._profiler = profiler
        self._graph = graph_client
        self._ip_rep = ip_reputation or {}

    def triage(
        self,
        alert_id: str,
        transaction_id: str,
        severity: str,
        context: dict[str, Any] | None = None,
    ) -> TriageReport:
        """Run full triage investigation and return a risk dossier."""
        context = context or {}
        evidence: list[str] = []

        # 1. Check behavioral profile
        user_id = context.get("user_id", "")
        if self._profiler and user_id:
            profile = self._profiler.get_profile(user_id)
            z = self._profiler.amount_z_score(user_id, context.get("amount", 0))
            if z > 2.0:
                evidence.append(f"Amount z-score: {z:.1f} (high anomaly)")
            vel_anom, vel_score = self._profiler.velocity_check(user_id)
            if vel_anom:
                evidence.append(f"Velocity anomaly detected (score={vel_score:.2f})")
            geo_anom, geo_score = self._profiler.geo_impossibility_check(
                user_id, context.get("country", "")
            )
            if geo_anom:
                evidence.append("Geographic impossibility detected")

        # 2. Check graph for connected entities
        if self._graph and user_id:
            try:
                rings = self._graph.find_fraud_rings(user_id, depth=2)
                if rings:
                    evidence.append(f"Connected to {len(rings)} entities in fraud graph")
            except Exception:
                pass  # Graph unavailable

        # 3. Check IP reputation
        ip = context.get("ip_address", "")
        if ip and ip in self._ip_rep:
            rep_score = self._ip_rep[ip]
            if rep_score > 0.7:
                evidence.append(f"IP reputation score: {rep_score:.2f} (high risk)")

        # 4. Check transaction context
        amount = context.get("amount", 0)
        if amount > 10000:
            evidence.append(f"Large transaction: ${amount:,.0f}")

        # 5. Synthesize recommendation
        confidence = self._compute_confidence(evidence, severity)
        recommendation = self._recommend(confidence, severity, evidence)

        dossier = (
            f"Alert {alert_id} for txn {transaction_id} "
            f"(severity={severity}, amount=${amount:,.0f}). "
            + "; ".join(evidence) if evidence else "No additional risk signals found."
        )

        logger.info(
            "Triage alert=%s rec=%s confidence=%.2f evidence=%d",
            alert_id,
            recommendation,
            confidence,
            len(evidence),
        )

        return TriageReport(
            alert_id=alert_id,
            transaction_id=transaction_id,
            confidence=round(confidence, 4),
            recommendation=recommendation,
            risk_dossier=dossier,
            evidence=evidence,
            generated_at=datetime.now(),
        )

    def _compute_confidence(self, evidence: list[str], severity: str) -> float:
        """Compute triage confidence from evidence count and alert severity."""
        base = {"LOW": 0.3, "MEDIUM": 0.5, "HIGH": 0.7, "CRITICAL": 0.9}.get(severity, 0.5)
        evidence_bonus = min(len(evidence) * 0.05, 0.3)
        return min(base + evidence_bonus, 1.0)

    @staticmethod
    def _recommend(confidence: float, severity: str, evidence: list[str]) -> str:
        if confidence >= 0.8 or severity == "CRITICAL":
            return "ESCALATE"
        if confidence >= 0.5 or len(evidence) >= 2:
            return "INVESTIGATE"
        return "DISMISS"


class MockTriageAgent(TriageAgent):
    """Agent that works without external dependencies (for testing)."""

    def __init__(self) -> None:
        super().__init__()

    def triage(
        self,
        alert_id: str,
        transaction_id: str,
        severity: str,
        context: dict[str, Any] | None = None,
    ) -> TriageReport:
        context = context or {}
        amount = context.get("amount", 0)
        evidence = []
        if amount > 10000:
            evidence.append(f"High-value transaction: ${amount:,.0f}")
        if severity in ("HIGH", "CRITICAL"):
            evidence.append(f"Alert severity: {severity}")

        confidence = min(0.3 + len(evidence) * 0.25, 1.0)
        return TriageReport(
            alert_id=alert_id,
            transaction_id=transaction_id,
            confidence=round(confidence, 4),
            recommendation=self._recommend(confidence, severity, evidence),
            risk_dossier=f"Mock triage for {alert_id}: {'; '.join(evidence) or 'No signals'}",
            evidence=evidence,
            generated_at=datetime.now(),
        )
