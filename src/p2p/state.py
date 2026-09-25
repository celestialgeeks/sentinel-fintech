# ruff: noqa: PLC0415
"""Durable guard state (velocity, structuring, repeat-counterparty trust).

The generic screening engine keeps velocity/structuring state in-process, which
is wrong for a multi-worker deployment. This module externalises the P2P guard's
fast-moving state into Redis with a transparent in-process fallback, so the same
code runs in a single test process and across many workers.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_WINDOW_S = 48 * 3600  # keep 48h of activity


def _redis_or_none():
    try:
        from src.shared.cache import redis_client

        if getattr(redis_client, "_client", None) is None:
            return None  # not connected yet -> use memory fallback
        return redis_client
    except Exception:  # pragma: no cover
        return None


class GuardState:
    """Async key-value store for short-lived guard counters."""

    def __init__(self) -> None:
        self._mem: dict[str, tuple[float, Any]] = {}

    async def _get(self, key: str) -> Any | None:
        rc = _redis_or_none()
        if rc is not None:
            try:
                raw = await rc.get(key)
                return json.loads(raw) if raw else None
            except Exception:  # noqa: BLE001
                logger.debug("redis get failed, using memory", exc_info=True)
        item = self._mem.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.monotonic() > expires_at:
            self._mem.pop(key, None)
            return None
        return value

    async def _set(self, key: str, value: Any, ttl: int) -> None:
        rc = _redis_or_none()
        if rc is not None:
            try:
                await rc.set(key, json.dumps(value, default=str), ttl=ttl)
                return
            except Exception:  # noqa: BLE001
                logger.debug("redis set failed, using memory", exc_info=True)
        self._mem[key] = (time.monotonic() + ttl, value)

    # ── activity (velocity / structuring / seller-exposure) ──────────────────

    async def add_activity(self, subject_key: str, ts: float, amount: float) -> None:
        events = await self._get(f"act:{subject_key}") or []
        events = [e for e in events if ts - e[0] <= _WINDOW_S]
        events.append([ts, amount])
        await self._set(f"act:{subject_key}", events, ttl=_WINDOW_S + 60)

    async def recent_activity(self, subject_key: str, window_s: int = 3600) -> list[tuple[float, float]]:
        events = await self._get(f"act:{subject_key}") or []
        now = time.time()
        return [(t, a) for (t, a) in events if now - t <= window_s]

    # ── repeat-counterparty trust with decay ────────────────────────────────

    async def get_trust(self, buyer_key: str) -> dict[str, Any]:
        return await self._get(f"trust:{buyer_key}") or {"seen": 0, "flagged": 0, "clean_streak": 0, "last_ts": 0}

    async def record_outcome(self, buyer_key: str, flagged: bool) -> dict[str, Any]:
        t = await self.get_trust(buyer_key)
        t["seen"] = int(t.get("seen", 0)) + 1
        t["flagged"] = int(t.get("flagged", 0)) + (1 if flagged else 0)
        t["clean_streak"] = 0 if flagged else int(t.get("clean_streak", 0)) + 1
        t["last_ts"] = time.time()
        # keep trust history for 90 days
        await self._set(f"trust:{buyer_key}", t, ttl=90 * 24 * 3600)
        return t


# Module-level singleton
guard_state = GuardState()
