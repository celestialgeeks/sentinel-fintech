"""PostgreSQL async connection layer using SQLAlchemy 2.0."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import AsyncGenerator

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment / .env."""

    database_url: str = "postgresql+asyncpg://sentinel:password@localhost:5432/sentinel"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class Database:
    """Manages the async SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings) -> None:
        self._engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=settings.database_url.endswith("echo=true"),
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def init(self) -> None:
        """Create tables on startup (development only — use Alembic in prod)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified")

    async def dispose(self) -> None:
        """Dispose the engine pool."""
        await self._engine.dispose()

    def session(self) -> AsyncSession:
        """Return a context-managed async session."""
        return self._session_factory()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield an async session that is committed on success, rolled back on exception."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Module-level singleton
_settings = get_settings()
engine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.database_pool_size,
    max_overflow=_settings.database_max_overflow,
    pool_pre_ping=True,
)
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
db = Database(_settings)


async def init_db() -> None:
    await db.init()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
