"""FastAPI application factory for Sentinel FinTech.

This module is the composition root and nothing more: it builds the app, wires
lifecycle hooks, installs middleware, and mounts each domain slice's router under
its ``/api/v1`` prefix. Domain logic lives in the slices themselves (``src.p2p``,
``src.portal``, ``src.fraud``, …); add an endpoint by editing the slice, not here.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.hmac_auth import HmacAuthMiddleware
from src.core.cache import redis_client
from src.core.db import engine, require_schema
from src.core.kafka_client import kafka_consumer
from src.decision.router import router as decision_router
from src.fraud.router import router as fraud_router
from src.gateway.router import router as gateway_router
from src.merchant.router import router as merchant_router
from src.messaging.consumer import setup_consumer
from src.p2p.router import router as p2p_router
from src.portal.auth.router import router as portal_auth_router
from src.portal.config import cors_origin_list
from src.portal.integrations.router import router as portal_integration_router
from src.portal.ledger.router import router as portal_data_router
from src.screening.router import router as screening_router
from src.verification.router import router as verification_router

logger = logging.getLogger(__name__)


async def _startup() -> None:
    """Run startup tasks: DB migration check, cache warm-up, Kafka consumer bootstrap.

    Only the schema is a hard dependency. Redis and Kafka are accelerators that a
    hosted deployment may not have: the guard keeps its order state in-process
    (``src/p2p/state.py``), the trail cache logs and misses
    (``src/gateway/trail_cache.py``), and ``kafka_client`` degrades to ``None``
    without the broker library installed. Failing the boot on those turns a
    working portal into a crash loop, so each is a warning instead.
    """
    logger.info("Sentinel starting up — verifying database schema")
    await require_schema()

    logger.info("Connecting to Redis")
    try:
        # connect() builds the client; ping() on the singleton before that is an
        # AttributeError on None, not a connection error.
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — continuing without the shared cache", exc)

    if kafka_consumer is None:
        logger.warning("confluent-kafka not installed — event streams disabled")
    else:
        try:
            logger.info("Starting Kafka consumer")
            kafka_consumer.start()
            setup_consumer()
            logger.info("Kafka consumer started")
        except Exception as exc:
            logger.warning("Kafka unavailable (%s) — event streams disabled", exc)


async def _shutdown() -> None:
    """Clean up on shutdown: close DB pool, stop Kafka consumer."""
    if kafka_consumer is not None:
        logger.info("Shutting down Kafka consumer")
        kafka_consumer.stop()

    logger.info("Closing Redis connection")
    await redis_client.aclose()

    logger.info("Disposing SQLAlchemy engine")
    await engine.dispose()
    logger.info("Sentinel shut down cleanly")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await _startup()
    yield
    await _shutdown()


app = FastAPI(
    title="Sentinel FinTech API",
    description="Entity Risk Intelligence Platform for AML/KYC/screening",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS. Origins come from CORS_ORIGINS (comma-separated). Credentialed requests
# are only allowed when the list is explicit: a wildcard plus cookies is a
# combination browsers reject anyway, so refusing it here is the honest default.
_origins = cors_origin_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=("*" not in _origins),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"],
)

# Guard bot-callback authentication (HMAC) - opt-in via GUARD_HMAC_SECRET.
app.add_middleware(HmacAuthMiddleware)


# ─── Health ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-api"}


# ─── Mount routes ─────────────────────────────────────────────────────────────
# Detection and decisioning slices. Each router already carries its own prefix
# (see ``prefix=`` in the slice), so the order here only affects /docs grouping.
app.include_router(fraud_router, prefix="/api/v1/fraud")
app.include_router(screening_router, prefix="/api/v1")
app.include_router(merchant_router, prefix="/api/v1")
app.include_router(gateway_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(decision_router, prefix="/api/v1")

# P2P pre-settlement guard (the bot-facing contract).
app.include_router(p2p_router, prefix="/api/v1")

# Merchant portal: /api/v1/auth/*, /api/v1/integration/*, /api/v1/portal/*
app.include_router(portal_auth_router, prefix="/api/v1")
app.include_router(portal_integration_router, prefix="/api/v1")
app.include_router(portal_data_router, prefix="/api/v1")

logger.info("FastAPI app factory loaded")
