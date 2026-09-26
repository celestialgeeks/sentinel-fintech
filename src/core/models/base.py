"""Shared ORM primitives for every Sentinel table.

``PkBigInt`` and ``_NOW`` exist because Sentinel has to run against PostgreSQL in
production and SQLite in tests/dev with one set of declarations.
"""


from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

# BIGSERIAL on PostgreSQL, plain INTEGER on SQLite. SQLite only auto-increments
# a column declared "INTEGER PRIMARY KEY", so a BIGINT id makes every id-less
# INSERT fail with "NOT NULL constraint failed" — which breaks the in-memory
# test harness and any SQLite-based local run.
PkBigInt = BigInteger().with_variant(Integer, "sqlite")


# Dialect-neutral equivalent of the migrations' now() default. SQLite has no
# now(); CURRENT_TIMESTAMP is valid on both.
_NOW = text("CURRENT_TIMESTAMP")


class TimestampMixin:
    """Auto-managed `created_at` column mixin."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=_NOW,
        nullable=False,
    )
