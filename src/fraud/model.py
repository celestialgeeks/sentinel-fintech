"""XGBoost fraud scoring model with synthetic training data."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_model = None  # type: ignore


def get_model() -> Any:
    """Lazy-load the XGBoost model."""
    global _model
    if _model is None:
        try:
            import xgboost as xgb  # type: ignore
            _model = xgb.XGBClassifier(
                n_estimators=50,
                max_depth=4,
                learning_rate=0.1,
                scale_pos_weight=9,  # imbalanced: 90% legit, 10% fraud
                use_label_encoder=False,
                eval_metric="logloss",
            )
            _train_synthetic(_model)
            logger.info("XGBoost fraud model loaded (synthetic training)")
        except ImportError:
            logger.warning("xgboost not installed — using rule-based fallback")
            _model = _RuleBasedScorer()
    return _model


class _RuleBasedScorer:
    """Fallback scorer when XGBoost is unavailable."""

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        return [0.5] * len(X)


def _train_synthetic(model: Any) -> None:
    """Train on synthetic fraud data for demonstration."""
    import numpy as np  # type: ignore

    np.random.seed(42)
    n_samples = 1000
    n_fraud = n_samples // 10

    # Features: [amount, z_score, velocity_1h, geo_anomaly, time_anomaly]
    X_legit = np.random.randn(n_samples - n_fraud, 5) * 0.5
    X_legit[:, 0] = np.abs(X_legit[:, 0]) + 100  # amount: $100-300
    X_fraud = np.random.randn(n_fraud, 5) * 0.8
    X_fraud[:, 0] = np.abs(X_fraud[:, 0]) + 5000  # amount: $5K-7K
    X_fraud[:, 1] = np.abs(X_fraud[:, 1]) + 2  # high z-scores
    X_fraud[:, 2] = np.random.uniform(3, 10, n_fraud)  # high velocity
    X_fraud[:, 3] = np.random.choice([0, 1], n_fraud, p=[0.3, 0.7])  # geo anomaly
    X_fraud[:, 4] = np.random.choice([0, 1], n_fraud, p=[0.4, 0.6])  # time anomaly

    X = np.vstack([X_legit, X_fraud])
    y = np.array([0] * (n_samples - n_fraud) + [1] * n_fraud)

    model.fit(X, y)
    logger.info("Synthetic training complete: %d legit, %d fraud", n_samples - n_fraud, n_fraud)


def score_transaction(features: list[float]) -> float:
    """Score a single transaction. Features: [amount, z_score, velocity, geo_anomaly, time_anomaly]."""
    model = get_model()
    proba = model.predict_proba([features])
    return float(proba[0][1]) if hasattr(proba[0], "__getitem__") else float(proba[0])
