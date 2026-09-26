"""Redis cache for trail analysis results.

Caches trail analysis to avoid redundant Neo4j queries.
TTL-based eviction for stale data.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from src.core.cache import redis_client

logger = logging.getLogger(__name__)

TRAIL_CACHE_KEY_PREFIX = "trail:"
TRAIL_CACHE_TTL_SECONDS = 300  # 5 minutes


async def get_cached_trail(payment_id: str) -> Optional[dict[str, Any]]:
    """Get cached trail analysis if available."""
    try:
        raw = await redis_client.get(f"{TRAIL_CACHE_KEY_PREFIX}{payment_id}")
        if raw:
            data = json.loads(raw)
            logger.debug("Cache hit for trail: %s", payment_id)
            return data
    except Exception as e:
        logger.warning("Cache read failed for %s: %s", payment_id, str(e))
    return None


async def set_cached_trail(payment_id: str, analysis: dict[str, Any]) -> None:
    """Cache trail analysis with TTL."""
    try:
        key = f"{TRAIL_CACHE_KEY_PREFIX}{payment_id}"
        await redis_client.set(key, json.dumps(analysis), ttl=TRAIL_CACHE_TTL_SECONDS)
        logger.debug("Cached trail for %s (TTL=%ds)", payment_id, TRAIL_CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning("Cache write failed for %s: %s", payment_id, str(e))


async def invalidate_trail_cache(payment_id: str) -> None:
    """Remove trail cache entry."""
    try:
        key = f"{TRAIL_CACHE_KEY_PREFIX}{payment_id}"
        await redis_client.delete(key)
        logger.debug("Invalidated cache for trail: %s", payment_id)
    except Exception as e:
        logger.warning("Cache invalidation failed for %s: %s", payment_id, str(e))
