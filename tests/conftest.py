"""Pytest configuration and shared fixtures for Sentinel FinTech tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """In-memory SQLite engine for tests — avoids needing a real PostgreSQL."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        from src.shared.db import Base  # noqa: PLC0415 — avoid circular import at collection time
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test transactional session with rollback."""
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        session_factory = async_sessionmaker(conn, expire_on_commit=False)
        async with session_factory() as session:
            yield session
            await session.rollback()
        await transaction.rollback()


# ---------------------------------------------------------------------------
# Redis mock fixture
# ---------------------------------------------------------------------------

class _FakeRedis:
    """In-memory mock mimicking redis.asyncio.Redis for unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self._store.clear()

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> int:
        return int(key in self._store)

    async def ttl(self, key: str) -> int:
        return -1 if key not in self._store else 300

    async def incr(self, key: str, amount: int = 1) -> int:
        val = int(self._store.get(key, 0)) + amount
        self._store[key] = str(val)
        return val


@pytest_asyncio.fixture
async def mock_redis() -> _FakeRedis:
    return _FakeRedis()


# ---------------------------------------------------------------------------
# Milvus mock fixture
# ---------------------------------------------------------------------------

class _FakeMilvus:
    """In-memory mock mimicking the MilvusClient for unit tests."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self.connected = False
        self._search_handlers: list[callable] = []

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def upsert(
        self,
        id: str,
        entity_type: str,
        name: str,
        embedding: list[float],
        metadata: dict | None = None,
        score: float | None = None,
    ) -> None:
        self._data[id] = {
            "id": id,
            "entity_type": entity_type,
            "name": name,
            "embedding": embedding,
            "metadata": metadata or {},
            "score": score or 0.0,
        }

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        entity_type: str | None = None,
        score_threshold: float = 0.5,
    ) -> list[dict]:
        results = []
        for entry in self._data.values():
            if entity_type and entry["entity_type"] != entity_type:
                continue
            results.append(entry)
        return results[:limit]

    def reset(self) -> None:
        self._data.clear()


@pytest_asyncio.fixture
async def mock_milvus() -> _FakeMilvus:
    client = _FakeMilvus()
    await client.connect()
    yield client
    await client.disconnect()
    client.reset()


# ---------------------------------------------------------------------------
# Kafka mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kafka_producer():
    producer = MagicMock()
    producer.produce = AsyncMock()
    producer.flush = MagicMock()
    producer.close = MagicMock()
    return producer


@pytest.fixture
def mock_kafka_consumer():
    consumer = MagicMock()
    consumer.start = MagicMock()
    consumer.stop = MagicMock()
    consumer.poll = MagicMock(return_value=None)
    return consumer


# ---------------------------------------------------------------------------
# FastAPI test client (when app is available)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session, mock_redis, mock_milvus, mock_kafka_producer):
    """Override shared singletons and return an async TestClient."""
    # Patch module-level singletons for the test
    import src.shared.db as db_module  # noqa: PLC0415
    import src.shared.cache as cache_module  # noqa: PLC0415
    import src.shared.vector_db as vdb_module  # noqa: PLC0415
    import src.shared.kafka as kafka_module  # noqa: PLC0415

    db_module.engine = test_engine
    cache_module.redis_client = mock_redis
    vdb_module.milvus_client = mock_milvus
    kafka_module.kafka_producer = mock_kafka_producer

    from fastapi.testclient import TestClient  # noqa: PLC0415
    from src.api.main import app  # noqa: PLC0415

    with TestClient(app) as c:
        yield c
