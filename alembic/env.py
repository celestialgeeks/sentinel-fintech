"""Alembic configuration for async SQLAlchemy 2.0."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.db import get_settings, engine, Base  # noqa: E402
from src.shared.models import *  # noqa: E402,F401 — register all models with Base.metadata

logger = logging.getLogger(__name__)

config = context.config
target_metadata = Base.metadata  # noqa: F821


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_settings().database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_settings().database_url
    target_metadata = target_metadata

    from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

    async_engine = create_async_engine(
        configuration["sqlalchemy.url"],
        poolclass=pool.NullPool,
    )

    async def run_async_migrations() -> None:
        async with async_engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()

    import asyncio  # noqa: E402
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
