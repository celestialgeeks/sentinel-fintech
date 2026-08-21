"""FastAPI application factory for Sentinel FinTech."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.shared.db import engine, init_db
from src.shared.cache import redis_client
from src.shared.kafka import kafka_producer, kafka_consumer
from src.fraud.routers import router as fraud_router
from src.api.routers.screening import router as screening_router
from src.api.routers.merchant import router as merchant_router

logger = logging.getLogger(__name__)


async def _startup() -> None:
    """Run startup tasks: DB migrations, cache warm-up, Kafka consumer bootstrap."""
    logger.info("Sentinel starting up — running database initialisation")
    await init_db()
    logger.info("Database initialised")

    logger.info("Connecting to Redis")
    await redis_client.ping()
    logger.info("Redis connection established")

    logger.info("Starting Kafka consumer")
    kafka_consumer.start()
    logger.info("Kafka consumer started")


async def _shutdown() -> None:
    """Clean up on shutdown: close DB pool, stop Kafka consumer."""
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-api"}


# ─── Mount routes ─────────────────────────────────────────────────────────────
from src.fraud.routers import router as fraud_router  # noqa: E402
from src.api.routers.screening import router as screening_router  # noqa: E402
from src.api.routers.merchant import router as merchant_router  # noqa: E402
from src.gateway.router import router as gateway_router  # noqa: E402
from src.verification.router import router as verification_router  # noqa: E402

app.include_router(fraud_router, prefix="/api/v1/fraud")
app.include_router(screening_router, prefix="/api/v1")
app.include_router(merchant_router, prefix="/api/v1")
app.include_router(gateway_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")


logger.info("FastAPI app factory loaded")
