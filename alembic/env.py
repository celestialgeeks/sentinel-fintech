"""Alembic configuration for async SQLAlchemy 2.0."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Importing the package registers every table on Base.metadata; that is the whole
# point of the line, so Autogenerate can see the schema.
from src.core import models as _models  # noqa: E402,F401
from src.core.db import Base, get_settings  # noqa: E402

logger = logging.getLogger(__name__)

config = context.config
target_metadata = Base.metadata


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

    async_engine = create_async_engine(
        configuration["sqlalchemy.url"],
        poolclass=pool.NullPool,
    )

    def do_run_migrations(connection) -> None:
        # Migrations must see a *sync* connection: alembic introspects the
        # version table and any guard that calls sa.inspect(bind), neither of
        # which works against an AsyncConnection.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations() -> None:
        async with async_engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await async_engine.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
