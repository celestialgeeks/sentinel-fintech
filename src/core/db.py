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
    database_pool_size: int = 5
    database_max_overflow: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}
    # case_sensitive=True would require an env var literally named "database_url";
    # the documented name is DATABASE_URL, so it silently fell back to the default.
    # extra="ignore": this class reads the shared .env, which also carries keys owned
    # by Supabase, Redis and the vendor SDKs. Forbidding extras made importing the app
    # raise as soon as any of those were set, for a settings class that only owns three.


@lru_cache
def get_settings() -> Settings:
    return Settings()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# Tables the request path cannot work without. Checked at boot by
# :func:`require_schema`; the full set lives in the migrations, this is the
# short list whose absence means "this database was never migrated".
_REQUIRED_TABLES = frozenset(
    {"alembic_version", "portal_users", "merchants", "p2p_orders", "screening_results", "lien_cases"}
)


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


async def require_schema() -> str:
    """Confirm the database has been migrated, and report which revision it is on.

    The app used to call ``Base.metadata.create_all`` at boot. On a real server
    that is the wrong tool twice over: it silently creates tables Alembic does
    not know about (so the next ``upgrade`` fails on a table that already exists),
    and it lets a deployment run on a schema that drifted from the migration
    history without anyone noticing. Production schema changes belong in
    revisions, applied deliberately.

    Returns the applied revision, or raises with the command to run.
    """
    from sqlalchemy import text  # noqa: PLC0415 - keeps the module's import list flat

    async with db.session() as session:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
        tables = {
            row[0]
            for row in await session.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
        }

    missing = sorted(_REQUIRED_TABLES - tables)
    if missing or not revision:
        detail = f" (missing tables: {', '.join(missing)})" if missing else " (no alembic_version row)"
        raise RuntimeError(
            f"database schema is not migrated{detail}. "
            "Run: python -m src.scripts.migrate upgrade head"
        )
    logger.info("Database schema at Alembic revision %s", revision)
    return str(revision)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
