"""Checkpointer factory: InMemorySaver for dev/tests, MongoDBSaver for prod.

The checkpointer is what lets `interrupt()` pause a thread in one HTTP request and
resume it in another, and what gives each `thread_id` its memory.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pymongo import MongoClient

from estimator_agent.core.config import Settings
from estimator_agent.db import mongo
from estimator_agent.domain import CHECKPOINT_TYPES


def build_serializer() -> JsonPlusSerializer:
    # Explicit allow-list: only our domain types (plus LangGraph's built-in safe types)
    # may be revived from a checkpoint. Defends against code execution via a tampered DB.
    return JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_TYPES)


@asynccontextmanager
async def checkpointer_from_settings(settings: Settings) -> AsyncIterator[BaseCheckpointSaver[Any]]:
    serde = build_serializer()
    if settings.checkpointer == "mongodb":
        client: MongoClient[dict[str, Any]] = MongoClient(mongo.require_uri(settings))
        try:
            yield MongoDBSaver(  # sync driver; async methods run in a thread pool
                client,
                db_name=settings.mongodb_db,
                checkpoint_collection_name=mongo.CHECKPOINTS,
                writes_collection_name=mongo.CHECKPOINT_WRITES,
                serde=serde,
            )
        finally:
            client.close()
    else:
        yield InMemorySaver(serde=serde)
