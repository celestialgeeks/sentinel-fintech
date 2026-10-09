"""One-command API for frontend work: ``python -m src.scripts.dev_server``.

The production app in :mod:`src.api.main` pings Redis, runs migrations and starts
a Kafka consumer in its lifespan, so it only boots inside ``docker compose``.
That is the right shape for production and the wrong shape for building screens:
a designer should not need three containers to render a ledger.

This server mounts the same routers — the bot gates, the portal reads, auth and
integration — with no external services of Sentinel's own. The data layer is the
project's real PostgreSQL (Supabase, from ``DATABASE_URL`` in ``.env``) and
sign-in is the project's real Supabase Auth, so what you see while building
screens is the same schema and the same credential path production uses. The
guard still degrades exactly as designed here: vendors without an API key fall
back to their deterministic mocks, and ``guard_state`` uses its in-process cache
instead of Redis. Same verdicts, same fields, same errors; none of the
infrastructure.

    python -m src.scripts.dev_server                  # http://localhost:8000
    python -m src.scripts.dev_server --seed           # plus a demo merchant
    python -m src.scripts.dev_server --port 9000 --reset-seed
    python -m src.scripts.dev_server --no-migrate     # skip the upgrade-head step

Demo login after ``--seed``: ``demo@sentinel.dev`` / ``demo-passw0rd-123`` — that
password lives in Supabase, not in the database this server writes to.

Note the deferred router imports: ``src.core.db`` builds its engine at import
time from ``DATABASE_URL``, so the environment must be set before anything that
touches the database is imported.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger("portal.dev")

DESCRIPTION = """Sentinel merchant portal — development API.

Pre-settlement AML guard for Binance P2P merchants. This instance runs the real
guard pipeline with deterministic mock data sources against Supabase Postgres and
Supabase Auth, so the portal surface behaves as it does in production without
Redis or Kafka. See docs/PORTAL_API.md for the contract the frontend is built
against.
"""


def create_app():
    """The portal surface, minus anything that needs a container."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from src.portal.config import cors_origin_list

    app = FastAPI(title="Sentinel Portal (dev API)", description=DESCRIPTION, version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "Content-Type"],
    )

    from src.p2p.router import router as p2p_router
    from src.portal.auth.router import router as auth_router
    from src.portal.integrations.router import router as integration_router
    from src.portal.ledger.router import router as data_router

    app.include_router(p2p_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(integration_router, prefix="/api/v1")
    app.include_router(data_router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "sentinel-portal-dev", "mode": "supabase+mock-vendors"}

    return app


async def _prepare(*, seed: bool, reset_seed: bool) -> None:
    if not seed:
        return
    from src.scripts.seed_portal import seed as seed_demo

    # simulate_telemetry=True: mock vendors make no network call, so latency and
    # spend would be 0 and the Insights screen would render empty. The seeder
    # prints a line saying the numbers are demo-only.
    await seed_demo(
        email="demo@sentinel.dev",
        merchant_id="default",
        orders=14,
        reset=reset_seed,
        simulate_telemetry=True,
    )


def _require_environment() -> None:
    """Fail at boot, in one line, instead of failing at the first request.

    Both halves are needed now: the ledger reads Supabase Postgres, and auth
    calls GoTrue. A missing ``DATABASE_URL`` used to fall through to a localhost
    Postgres string and surface as a connection error three screens later.
    """
    from src.core.db import get_settings
    from src.portal import supabase

    if not (os.environ.get("DATABASE_URL") or Path(".env").exists()):
        raise SystemExit(
            "No DATABASE_URL and no .env. Copy .env.example to .env and point "
            "DATABASE_URL at the Supabase Postgres (session-mode pooler)."
        )
    if get_settings().database_url.startswith("sqlite"):
        raise SystemExit(
            "DATABASE_URL is still SQLite. The portal's schema and auth are "
            "PostgreSQL-only now — point it at Supabase and run 'alembic upgrade head'."
        )
    if not supabase.configured():
        raise SystemExit(
            "Supabase Auth is not configured. .env needs SUPABASE_URL, "
            "SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY — without them every "
            "signup and login returns 503."
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Run the Sentinel portal API for frontend work")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--db", default=None, help="Override DATABASE_URL for this run")
    parser.add_argument("--seed", action="store_true", help="create the demo merchant and a week of decisions")
    parser.add_argument("--reset-seed", action="store_true", help="wipe the demo workspace before re-seeding")
    parser.add_argument("--no-migrate", action="store_true", help="skip 'alembic upgrade head' on boot")
    args = parser.parse_args()

    if args.db:
        os.environ["DATABASE_URL"] = args.db
    _require_environment()

    if not args.no_migrate:
        # Alembic's env.py runs its own event loop, so this has to happen before
        # asyncio.run(_prepare(...)) starts one — and before the routers import.
        from src.scripts.migrate import run_upgrade

        run_upgrade("head")

    asyncio.run(_prepare(seed=args.seed, reset_seed=args.reset_seed))

    import uvicorn

    print(f"\nPortal API  http://{args.host}:{args.port}   docs http://{args.host}:{args.port}/docs")
    print(f"DB        {os.environ.get('DATABASE_URL') or 'from .env (Supabase Postgres)'}")
    if args.seed:
        print("Login     demo@sentinel.dev / demo-passw0rd-123   (merchant_id: default)")
    print()
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
