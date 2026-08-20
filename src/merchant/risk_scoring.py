"""Merchant risk scoring engine — composite score from multiple signals."""

from __future__ import annotations

import logging
from typing import Any

from src.merchant.kyb import KYBVerifier

logger = logging.getLogger(__name__)

HIGH_RISK_COUNTRIES = {"IR", "KP", "SY", "CU", "MM", "VE", "BY", "AF", "YE", "SO"}


class RiskScorer:
    """Computes composite merchant risk score from multiple signals."""

    def __init__(self, kyb_verifier: KYBVerifier | None = None) -> None:
        self._kyb = kyb_verifier or KYBVerifier()

    def score(
        self,
        business_name: str,
        country: str,
        industry: str,
        doc_verification: dict[str, Any] | None = None,
        web_reputation_score: float = 0.5,
        sanctions_check: bool = True,
    ) -> dict[str, Any]:
        """Compute composite risk score."""
        components: list[dict[str, Any]] = []

        # 1. KYB verification score
        kyb_score = (doc_verification or {}).get("verification_score", 0.5)
        components.append({"name": "kyb_completeness", "score": 1.0 - kyb_score, "weight": 0.30})

        # 2. Geographic risk
        geo_risk = 0.8 if country.upper() in HIGH_RISK_COUNTRIES else 0.1
        components.append({"name": "geographic_risk", "score": geo_risk, "weight": 0.20})

        # 3. Industry risk
        high_risk_industries = {"crypto", "cryptocurrency", "gambling", "adult", "money service"}
        ind_risk = 0.7 if any(hri in industry.lower() for hri in high_risk_industries) else 0.1
        components.append({"name": "industry_risk", "score": ind_risk, "weight": 0.15})

        # 4. Web reputation
        components.append({"name": "web_reputation", "score": 1.0 - web_reputation_score, "weight": 0.15})

        # 5. Sanctions check
        san_score = 0.9 if sanctions_check else 0.0
        components.append({"name": "sanctions_screening", "score": san_score, "weight": 0.20})

        # Composite score (weighted sum)
        composite = sum(c["score"] * c["weight"] for c in components)
        composite = min(max(composite, 0.0), 1.0)

        # Recommendation
        if composite < 0.3:
            recommendation = "APPROVE"
        elif composite < 0.6:
            recommendation = "REVIEW"
        else:
            recommendation = "REJECT"

        explanation_parts = [f"Composite risk: {composite:.2f}"]
        for c in components:
            if c["score"] > 0.3:
                explanation_parts.append(f"{c['name']}: {c['score']:.2f}")

        return {
            "composite_score": round(composite, 4),
            "components": components,
            "recommendation": recommendation,
            "explanation": "; ".join(explanation_parts),
        }
