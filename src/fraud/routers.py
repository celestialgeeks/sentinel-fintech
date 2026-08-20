"""FastAPI router for Fraud Detection endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.fraud.alert_triage import MockTriageAgent
from src.fraud.behavioral import BehavioralProfiling
from src.fraud.schemas import FraudAlert, FraudScore
from src.fraud.scorer import FraudScorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["fraud"])

# Module-level state (in production, inject via Depends)
_profiler = BehavioralProfiling()
_scorer = FraudScorer(_profiler)
_triage_agent = MockTriageAgent()

# In-memory alert store (replace with PostgreSQL in production)
_alerts: dict[str, dict[str, Any]] = {}
_next_alert_id = 1


@router.post("/check", response_model=FraudScore)
async def check_fraud(
    transaction_id: str = Query(..., description="Transaction ID to check"),
    user_id: str = Query(..., description="User ID"),
    amount: float = Query(..., gt=0, description="Transaction amount"),
    country: str = Query("US", description="Transaction country"),
) -> FraudScore:
    """Submit a transaction for fraud scoring."""
    from datetime import datetime, timezone
    result = _scorer.score(transaction_id, user_id, amount, country, datetime.now(timezone.utc))

    # Create alert if score is high
    if result.combined_score >= 0.4:
        alert_id = f"alt_{_next_alert_id}"
        _next_alert_id += 1
        alert = FraudAlert(
            alert_id=alert_id,
            transaction_id=transaction_id,
            alert_type="ml_fraud" if result.ml_score > 0.5 else "behavioral",
            severity="CRITICAL" if result.combined_score > 0.8 else "HIGH" if result.combined_score > 0.6 else "MEDIUM",
            risk_score=result.combined_score,
        )
        _alerts[alert_id] = alert.model_dump()
        logger.info("Fraud alert created: %s for txn %s (score=%.3f)", alert_id, transaction_id, result.combined_score)

    return result


@router.get("/alerts", response_model=list[dict[str, Any]])
async def list_alerts(
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None, description="Filter by status: OPEN, INVESTIGATING, RESOLVED, DISMISSED"),
) -> list[dict[str, Any]]:
    """List fraud alerts with optional status filter."""
    alerts = list(_alerts.values())
    if status:
        alerts = [a for a in alerts if a.get("status") == status]
    return alerts[:limit]


@router.post("/alerts/{alert_id}/triage", response_model=dict[str, Any])
async def triage_alert(alert_id: str) -> dict[str, Any]:
    """Run agentic triage on a fraud alert."""
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert = _alerts[alert_id]
    report = _triage_agent.triage(
        alert_id=alert_id,
        transaction_id=alert.get("transaction_id", ""),
        severity=alert.get("severity", "MEDIUM"),
        context={"amount": alert.get("risk_score", 0) * 1000},
    )

    # Update alert status
    _alerts[alert_id]["triage_recommendation"] = report.recommendation
    _alerts[alert_id]["agent_notes"] = report.risk_dossier

    return report.model_dump()
