"""MongoDB client lifecycle. One AsyncMongoClient per process, created in the FastAPI lifespan."""

from __future__ import annotations

import asyncio
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from estimator_agent.core.config import Settings

# Collection names in one place.
RATES = "rates"
LEADS = "leads"
BOOKINGS = "bookings"
APPROVALS = "approvals"
KB_CHUNKS = "kb_chunks"
CHECKPOINTS = "checkpoints"
CHECKPOINT_WRITES = "checkpoint_writes"


def require_uri(settings: Settings) -> str:
    """Fail fast with a clear message instead of a 30 s server-selection timeout."""
    if not settings.mongodb_uri:
        raise RuntimeError(
            "MONGODB_URI is not set. Put your Atlas connection string "
            "(mongodb+srv://USER:PASSWORD@CLUSTER.xxxxx.mongodb.net/) in .env or the "
            "Render environment."
        )
    return settings.mongodb_uri


def create_client(settings: Settings) -> AsyncMongoClient[dict[str, Any]]:
    return AsyncMongoClient(
        require_uri(settings),
        appname=settings.app_name,
        serverSelectionTimeoutMS=5_000,
        tz_aware=True,
    )


def get_database(
    client: AsyncMongoClient[dict[str, Any]], settings: Settings
) -> AsyncDatabase[dict[str, Any]]:
    return client[settings.mongodb_db]


async def ping(db: AsyncDatabase[dict[str, Any]], timeout_s: float = 2.0) -> bool:
    """Readiness check. Bounded so a dead DB fails the probe fast instead of hanging it."""
    try:
        await asyncio.wait_for(db.command("ping"), timeout=timeout_s)
        return True
    except Exception:
        return False
