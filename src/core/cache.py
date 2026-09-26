"""Async Redis cache client wrapper."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Optional

import redis.asyncio as redis
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class CacheSettings(BaseSettings):
    redis_url: str = "redis://:password@localhost:6379/0"
    default_ttl: int = 300  # seconds

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_cache_settings() -> CacheSettings:
    return CacheSettings()


class RedisClient:
    """Thin async wrapper around redis-py with JSON serialisation."""

    def __init__(self, redis_url: str, default_ttl: int = 300) -> None:
        self._url = redis_url
        self._default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self._client = redis.from_url(self._url, decode_responses=True)
        await self._client.ping()
        logger.info("Redis connected at %s", self._url)

    async def ping(self) -> bool:
        return await self._client.ping()  # type: ignore[union-attr]

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Core operations ─────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(key)  # type: ignore[union-attr]

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> None:
        ttl = ttl or self._default_ttl
        await self._client.set(key, value, ex=ttl)  # type: ignore[union-attr]

    async def delete(self, key: str) -> None:
        await self._client.delete(key)  # type: ignore[union-attr]

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))  # type: ignore[union-attr]

    async def ttl(self, key: str) -> int:
        return await self._client.ttl(key)  # type: ignore[union-attr]

    # ── JSON helpers ────────────────────────────────────────────────────────

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        await self.set(key, json.dumps(value, default=str), ttl=ttl)

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self._client.incr(key, amount)  # type: ignore[union-attr]

    async def incrbyfloat(self, key: str, amount: float) -> float:
        return await self._client.incrbyfloat(key, amount)  # type: ignore[union-attr]


# Module-level singleton
_settings = get_cache_settings()
redis_client = RedisClient(_settings.redis_url, _settings.default_ttl)


class Cacheable(BaseModel):
    """Mixin that adds cache serialisation to Pydantic models."""

    def to_cache_key(self, *parts: str) -> str:
        identifiers = "|".join(parts) if parts else str(self.id)  # type: ignore[attr-defined]
        return f"{self.__class__.__name__}:{identifiers}"
