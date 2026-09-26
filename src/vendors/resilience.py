# ruff: noqa: N818, PLC0415
"""Resilience primitives for vendor calls.

P2P release windows are short (often 15 minutes) and every vendor is an
external dependency, so screening must be fast, retried, and circuit-broken,
and must never wedge the whole pipeline when one provider is down. The cache
prefers Redis but transparently falls back to an in-process TTL cache so the
system is usable (and testable) without a live Redis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

try:  # tenacity is a project dependency; degrade gracefully if absent
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential_jitter,
    )
    _HAS_TENACITY = True
except ImportError:  # pragma: no cover
    _HAS_TENACITY = False


# ─── Circuit breaker ──────────────────────────────────────────────────────────


class CircuitOpen(RuntimeError):
    """Raised when a provider's breaker is open (fast-fail during an outage)."""


class CircuitBreaker:
    """Minimal async circuit breaker: closed -> open -> half-open -> closed."""

    def __init__(self, failure_threshold: int = 4, reset_timeout: float = 30.0) -> None:
        self._threshold = failure_threshold
        self._reset = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self._reset:
            # allow a single probe (half-open)
            self._opened_at = None
            self._failures = self._threshold - 1
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold and self._opened_at is None:
            self._opened_at = time.monotonic()
            logger.warning("Circuit breaker OPENED after %d failures", self._failures)

    async def call(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        if self.is_open:
            raise CircuitOpen("provider circuit breaker is open")
        try:
            result = await fn()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result


# ─── Retry ────────────────────────────────────────────────────────────────────


async def with_retry(
    fn: Callable[[], Awaitable[Any]],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> Any:
    """Run *fn* with bounded exponential backoff + jitter.

    Uses tenacity when available; otherwise a small hand-rolled loop with the
    same semantics so behaviour is identical in either environment.
    """
    if _HAS_TENACITY:
        @retry(
            retry=retry_if_exception_type(retry_on),
            stop=stop_after_attempt(attempts),
            wait=wait_exponential_jitter(initial=base_delay, max=max_delay),
            reraise=True,
        )
        async def _run() -> Any:
            return await fn()

        return await _run()

    delay = base_delay
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except retry_on as exc:  # noqa: PERF203
            last_exc = exc
            if attempt == attempts:
                break
            await asyncio.sleep(min(delay, max_delay))
            delay = min(delay * 2, max_delay)
    assert last_exc is not None
    raise last_exc


# ─── Cache (Redis with in-process fallback) ───────────────────────────────────


class _MemoryTTL:
    """Tiny in-process TTL cache used when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._store.clear()


_mem_cache = _MemoryTTL()


def _redis_or_none():
    try:  # imported lazily so tests without a live Redis still import this module
        from src.core.cache import redis_client

        return redis_client
    except Exception:  # pragma: no cover
        return None


async def cached_json(key: str, loader: Callable[[], Awaitable[Any]], ttl: int) -> Any:
    """Fetch-through cache returning JSON-decoded values.

    Prefers the shared Redis client; on any Redis error (including "not yet
    connected") it transparently uses the in-process TTL cache instead.
    """
    if ttl <= 0:
        return await loader()

    rc = _redis_or_none()
    if rc is not None:
        try:
            hit = await rc.get_json(key)
            if hit is not None:
                return hit
            value = await loader()
            await rc.set_json(key, value, ttl=ttl)
            return value
        except Exception:  # Redis down / not connected -> fall through to memory
            logger.debug("Redis unavailable for cache key %s; using memory cache", key)

    hit = _mem_cache.get(key)
    if hit is not None:
        return hit
    value = await loader()
    _mem_cache.set(key, json.loads(json.dumps(value, default=str)), ttl)
    return value
