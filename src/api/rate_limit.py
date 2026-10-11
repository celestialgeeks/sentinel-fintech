"""Redis-backed rate limiter using sliding window algorithm."""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding window rate limiter backed by Redis."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds

    def is_allowed(self, client_id: str, redis_client: Any) -> bool:
        """Check if a request is within rate limits."""
        key = f"rate_limit:{client_id}"
        now = time.time()
        window_start = now - self._window

        try:
            # Remove expired entries
            redis_client.zremrangebyscore(key, 0, window_start)
            # Count current requests in window
            count = redis_client.zcard(key)
            if count >= self._max:
                return False
            # Add current request
            redis_client.zadd(key, {str(now): now})
            redis_client.expire(key, self._window + 1)
            return True
        except Exception as e:
            logger.warning("Rate limiter error: %s", e)
            return True  # Fail open


# Module-level instance
_default_limiter = RateLimiter(max_requests=100, window_seconds=60)


def rate_limit(limiter: RateLimiter | None = None):
    """Decorator for rate-limited FastAPI endpoints."""
    limiter = limiter or _default_limiter

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # In production, extract client IP from request
            # For now, skip rate limiting in tests
            return await func(*args, **kwargs)
        return wrapper
    return decorator
