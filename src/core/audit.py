"""Structured audit logger — writes to both file and in-memory store.

In production, this extends to write audit events to PostgreSQL and/or Kafka
for regulatory compliance and audit trails.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """Structured audit logger for compliance tracking."""

    def __init__(self, log_file: str = "audit.log") -> None:
        self._log_file = log_file
        self._events: list[dict[str, Any]] = []

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user: str = "system",
        result: str = "success",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write an audit event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": time.time(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user": user,
            "result": result,
            "details": details or {},
        }

        # Write to structured log
        logger.info("%s", json.dumps(event, default=str))

        # Store in memory (replace with DB in production)
        self._events.append(event)

        return event

    def get_events(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit events (for debugging/testing)."""
        events = self._events
        if entity_type:
            events = [e for e in events if e["entity_type"] == entity_type]
        if entity_id:
            events = [e for e in events if e["entity_id"] == entity_id]
        return events[-limit:]


# Module-level singleton
audit = AuditLogger()
