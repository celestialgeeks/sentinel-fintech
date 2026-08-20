"""Screening engine — orchestrates rules + watchlist matching for AML checks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.screening.rules import RuleEngine, RuleResult
from src.screening.schemas import MatchedEntity, ScreeningResponse, TransactionIngest
from src.screening.watchlists import search_by_name

logger = logging.getLogger(__name__)

# Recommendation thresholds
REVIEW_THRESHOLD = 0.4
BLOCK_THRESHOLD = 0.7


class ScreeningEngine:
    """Runs AML rules and watchlist matching against an ingested transaction."""

    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self._rules = rule_engine or RuleEngine()

    def screen(self, txn: TransactionIngest) -> ScreeningResponse:
        """Run full screening pipeline and return a response."""
        # 1. Run deterministic rules
        rule_results, risk_score = self._rules.evaluate(
            amount=txn.amount,
            currency=txn.currency,
            sender_id=txn.sender.entity_id,
            sender_country=txn.sender.country,
            receiver_id=txn.receiver.entity_id,
            receiver_country=txn.receiver.country,
            current_ts=txn.timestamp,
        )

        # 2. Record for stateful rules
        self._rules.add_transaction(
            sender_id=txn.sender.entity_id,
            ts=txn.timestamp,
            amount=txn.amount,
        )

        # 3. Watchlist matching (exact + fuzzy via embeddings later)
        watchlist_matches = self._check_watchlists(txn)

        # 4. Update risk score with watchlist hits
        if watchlist_matches:
            max_match_weight = max(m.risk_weight for m in watchlist_matches)
            risk_score = max(risk_score, max_match_weight)

        # 5. Collect flags
        flags = [r.rule_name for r in rule_results if r.triggered]
        flags += [m.list_source for m in watchlist_matches]

        # 6. Build explanation
        explanation_parts: list[str] = []
        for r in rule_results:
            if r.triggered:
                explanation_parts.append(r.detail)
        for m in watchlist_matches:
            explanation_parts.append(f"Watchlist match: {m.name} ({m.list_source}, score={m.risk_weight:.2f})")
        explanation = "; ".join(explanation_parts) if explanation_parts else "No rules or watchlist matches triggered"

        # 7. Determine recommendation
        recommendation = self._recommend(risk_score, flags)

        logger.info(
            "Screening txn=%s score=%.3f rec=%s flags=%s",
            txn.transaction_id,
            risk_score,
            recommendation,
            flags,
        )

        return ScreeningResponse(
            transaction_id=txn.transaction_id,
            risk_score=round(risk_score, 4),
            flags=flags,
            matched_entities=[
                MatchedEntity(
                    entity_id=m.entity_id,
                    name=m.name,
                    match_score=m.risk_weight,
                    list_source=m.list_source,
                    reason="",
                )
                for m in watchlist_matches
            ],
            recommendation=recommendation,
            explanation=explanation,
            screened_at=datetime.now(timezone.utc),
        )

    def _check_watchlists(self, txn: TransactionIngest) -> list[Any]:
        """Check sender and receiver against watchlists."""
        matches: list[Any] = []
        for entity in (txn.sender, txn.receiver):
            for entry in search_by_name(entity.name):
                matches.append(entry)
        return matches

    @staticmethod
    def _recommend(risk_score: float, flags: list[str]) -> str:
        if risk_score >= BLOCK_THRESHOLD:
            return "BLOCK"
        if risk_score >= REVIEW_THRESHOLD or len(flags) >= 2:
            return "REVIEW"
        return "APPROVE"
