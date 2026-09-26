"""One-command API for frontend work: ``python -m src.scripts.dev_server``.

The production app in :mod:`src.api.main` pings Redis, runs migrations and starts
a Kafka consumer in its lifespan, so it only boots inside ``docker compose``.
That is the right shape for production and the wrong shape for building screens:
a designer should not need three containers to render a ledger.

This server mounts the same routers — the bot gates, the portal reads, auth and
integration — on a SQLite file, with no external services. The guard degrades
exactly as designed here: vendors without an API key fall back to their
deterministic mocks, and ``guard_state`` uses its in-process cache instead of
Redis. Same verdicts, same fields, same errors; none of the infrastructure.

    python -m src.scripts.dev_server                  # http://localhost:8000
    python -m src.scripts.dev_server --seed           # plus a demo merchant
    python -m src.scripts.dev_server --port 9000 --reset-seed

Demo login after ``--seed``: ``demo@sentinel.dev`` / ``demo-passw0rd-123``.

Note the deferred router imports: ``src.core.db`` builds its engine at import
time from ``DATABASE_URL``, so the environment must be set before anything that
touches the database is imported.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

logger = logging.getLogger("portal.dev")

DESCRIPTION = """Sentinel merchant portal — development API.

Pre-settlement AML guard for Binance P2P merchants. This instance runs the real
guard pipeline with deterministic mock data sources and SQLite persistence, so the
portal surface behaves as it does in production without Postgres, Redis or Kafka.
See docs/PORTAL_API.md for the contract the frontend is built against.
"""

DEFAULT_DB = "sqlite+aiosqlite:///./sentinel_dev.db"


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
        return {"status": "ok", "service": "sentinel-portal-dev", "mode": "sqlite+mock-vendors"}

    return app


async def _prepare(*, seed: bool, reset_seed: bool) -> None:
    from src.core.db import init_db

    await init_db()
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Run the Sentinel portal API for frontend work")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--db", default=None, help="SQLAlchemy URL; defaults to a local SQLite file")
    parser.add_argument("--seed", action="store_true", help="create the demo merchant and a week of decisions")
    parser.add_argument("--reset-seed", action="store_true", help="wipe the demo workspace before re-seeding")
    args = parser.parse_args()

    if args.db:
        os.environ["DATABASE_URL"] = args.db
    os.environ.setdefault("DATABASE_URL", DEFAULT_DB)

    asyncio.run(_prepare(seed=args.seed, reset_seed=args.reset_seed))

    import uvicorn

    print(f"\nPortal API  http://{args.host}:{args.port}   docs http://{args.host}:{args.port}/docs")
    print(f"DB        {os.environ['DATABASE_URL']}")
    if args.seed:
        print("Login     demo@sentinel.dev / demo-passw0rd-123   (merchant_id: default)")
    print()
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
