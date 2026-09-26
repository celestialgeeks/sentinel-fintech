"""Alembic migration runner for Sentinel FinTech."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config

from alembic import command

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _cfg() -> Config:
    return Config(str(ALEMBIC_INI))


def run_upgrade(revision: str = "head") -> None:
    command.upgrade(_cfg(), revision)
    logger.info("Migration upgraded to %s", revision)


def run_downgrade(revision: str = "-1") -> None:
    command.downgrade(_cfg(), revision)
    logger.info("Migration downgraded to %s", revision)


def run_current() -> None:
    command.current(_cfg())


def run_check() -> None:
    command.check(_cfg())


def run_stamp(revision: str = "head") -> None:
    command.stamp(_cfg(), revision)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrate.py <upgrade|downgrade|current|check|stamp> [revision]")
        sys.exit(1)

    cmd = sys.argv[1]
    rev = sys.argv[2] if len(sys.argv) > 2 else "head"

    dispatch = {
        "upgrade": run_upgrade,
        "downgrade": run_downgrade,
        "current": run_current,
        "check": run_check,
        "stamp": run_stamp,
    }
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}. Available: {list(dispatch.keys())}")
        sys.exit(1)
    dispatch[cmd](rev)
