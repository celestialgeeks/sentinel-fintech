"""Fraud scoring orchestrator — combines behavioral + ML + rules."""

from __future__ import annotations

import logging
from datetime import datetime

from src.fraud.behavioral import BehavioralProfiling
from src.fraud.model import score_transaction
from src.fraud.schemas import FraudScore

logger = logging.getLogger(__name__)

BLOCK_THRESHOLD = 0.7
VERIFY_THRESHOLD = 0.4


class FraudScorer:
    """Orchestrates behavioral analysis + ML scoring for fraud detection."""

    def __init__(self, profiler: BehavioralProfiling | None = None) -> None:
        self._profiler = profiler or BehavioralProfiling()

    def score(
        self,
        transaction_id: str,
        user_id: str,
        amount: float,
        country: str,
        current_ts: datetime | None = None,
    ) -> FraudScore:
        """Run full fraud scoring pipeline."""
        if current_ts is None:
            current_ts = datetime.now()

        # Record for profiling
        self._profiler.record_transaction(user_id, current_ts, amount, country)

        # Behavioral checks
        z_score = self._profiler.amount_z_score(user_id, amount)
        velocity_anomaly, velocity_score = self._profiler.velocity_check(user_id, current_ts)
        geo_anomaly, geo_score = self._profiler.geo_impossibility_check(user_id, country, current_ts)
        time_anomaly, time_score = self._profiler.time_of_day_anomaly(user_id, current_ts)

        # ML score
        features = [amount, z_score, velocity_score * 10, float(geo_anomaly), float(time_anomaly)]
        ml_score = score_transaction(features)

        # Combined score (weighted ensemble)
        combined = min(
            0.35 * ml_score
            + 0.25 * min(z_score / 3.0, 1.0)
            + 0.20 * velocity_score
            + 0.15 * geo_score
            + 0.05 * time_score,
            1.0,
        )

        # Recommendation
        if combined >= BLOCK_THRESHOLD:
            recommendation = "BLOCK"
        elif combined >= VERIFY_THRESHOLD:
            recommendation = "VERIFY"
        else:
            recommendation = "APPROVE"

        reasons = []
        if z_score > 2.0:
            reasons.append(f"Amount anomaly (z={z_score:.1f})")
        if velocity_anomaly:
            reasons.append("Velocity anomaly")
        if geo_anomaly:
            reasons.append("Geographic impossibility")
        if time_anomaly:
            reasons.append("Time-of-day anomaly")
        if ml_score > 0.7:
            reasons.append(f"ML fraud probability={ml_score:.2f}")

        return FraudScore(
            transaction_id=transaction_id,
            fraud_probability=round(ml_score, 4),
            behavioral_z_score=round(z_score, 4),
            velocity_score=round(velocity_score, 4),
            geo_anomaly=geo_anomaly,
            time_anomaly=time_anomaly,
            ml_score=round(ml_score, 4),
            combined_score=round(combined, 4),
            recommendation=recommendation,
            reason="; ".join(reasons) if reasons else "No anomalies detected",
        )
