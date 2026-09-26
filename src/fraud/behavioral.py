"""Behavioral profiling engine for fraud detection."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class BehavioralProfiling:
    """Tracks and scores user behavioral anomalies."""

    def __init__(self) -> None:
        # user_id -> list of (timestamp, amount, country)
        self._history: dict[str, list[tuple[datetime, float, str]]] = {}

    def record_transaction(self, user_id: str, ts: datetime, amount: float, country: str) -> None:
        """Add a transaction to the user's history."""
        if user_id not in self._history:
            self._history[user_id] = []
        self._history[user_id].append((ts, amount, country))
        # Keep only last 30 days
        cutoff = ts - timedelta(days=30)
        self._history[user_id] = [
            (t, a, c) for t, a, c in self._history[user_id] if t > cutoff
        ]

    def get_profile(self, user_id: str, current_ts: datetime | None = None) -> dict[str, Any]:
        """Build a behavioral profile for a user."""
        if current_ts is None:
            current_ts = datetime.now(timezone.utc)

        txns = self._history.get(user_id, [])
        if not txns:
            return {"user_id": user_id, "txns": 0, "mean_amount": 0.0, "std_amount": 0.0}

        amounts = [a for _, a, _ in txns]
        mean_amt = sum(amounts) / len(amounts)
        variance = sum((a - mean_amt) ** 2 for a in amounts) / len(amounts) if len(amounts) > 1 else 0.0
        std_amt = math.sqrt(variance)

        # Count recent txns
        one_hour_ago = current_ts - timedelta(hours=1)
        one_day_ago = current_ts - timedelta(hours=24)
        txns_1h = sum(1 for t, _, _ in txns if t > one_hour_ago)
        txns_1d = sum(1 for t, _, _ in txns if t > one_day_ago)

        # Typical hours
        hours = [t.hour for t, _, _ in txns]
        typical_hours = sorted(set(hours))[:5] if hours else []

        # Typical countries
        countries = list(set(c for _, _, c in txns))

        return {
            "user_id": user_id,
            "txns": len(txns),
            "mean_amount": mean_amt,
            "std_amount": std_amt,
            "txns_1h": txns_1h,
            "txns_1d": txns_1d,
            "typical_hours": typical_hours,
            "typical_countries": countries,
        }

    def amount_z_score(self, user_id: str, amount: float) -> float:
        """Compute z-score for an amount against user's baseline."""
        profile = self.get_profile(user_id)
        std = profile.get("std_amount", 0.0)
        mean = profile.get("mean_amount", 0.0)
        if std == 0 or profile["txns"] < 3:
            return 0.0
        return abs(amount - mean) / std

    def velocity_check(self, user_id: str, current_ts: datetime | None = None) -> tuple[bool, float]:
        """Check if transaction frequency is anomalous."""
        if current_ts is None:
            current_ts = datetime.now(timezone.utc)
        profile = self.get_profile(user_id, current_ts)
        txns_1h = profile.get("txns_1h", 0)
        is_anomaly = txns_1h >= 5
        score = min(txns_1h / 10.0, 1.0) if is_anomaly else 0.0
        return is_anomaly, score

    def geo_impossibility_check(
        self,
        user_id: str,
        new_country: str,
        current_ts: datetime | None = None,
    ) -> tuple[bool, float]:
        """Check if a new country is geographically impossible."""
        txns = self._history.get(user_id, [])
        if len(txns) < 2:
            return False, 0.0
        if current_ts is None:
            current_ts = datetime.now(timezone.utc)

        # Find last transaction in a different country
        for ts, amt, country in sorted(txns, key=lambda x: x[0], reverse=True):
            if country != new_country:
                time_diff = (current_ts - ts).total_seconds() / 3600  # hours
                # Rough distance estimate: same continent ~2000km, different ~8000km
                distance = 8000.0  # worst case
                speed = distance / time_diff if time_diff > 0 else float("inf")
                # Commercial flight max ~900 km/h
                is_impossible = speed > 900 and time_diff < 4
                return is_impossible, min(speed / 900, 1.0) if time_diff > 0 else 0.0

        return False, 0.0

    def time_of_day_anomaly(self, user_id: str, current_ts: datetime | None = None) -> tuple[bool, float]:
        """Check if transaction hour is unusual for the user."""
        if current_ts is None:
            current_ts = datetime.now(timezone.utc)
        profile = self.get_profile(user_id)
        typical = profile.get("typical_hours", [])
        if not typical:
            return False, 0.0
        current_hour = current_ts.hour
        # Anomaly if hour is more than 4 slots away from any typical hour
        min_diff = min(abs(current_hour - h) for h in typical)
        is_anomaly = min_diff >= 4
        return is_anomaly, min_diff / 6.0
