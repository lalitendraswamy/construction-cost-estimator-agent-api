"""Index definitions. Run via `make indexes` (scripts/create_indexes.py), not at app start."""

from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.operations import SearchIndexModel

from estimator_agent.db import mongo

INDEXES: dict[str, list[IndexModel]] = {
    mongo.RATES: [IndexModel([("city", ASCENDING), ("tier", ASCENDING)], unique=True)],
    mongo.LEADS: [
        IndexModel([("thread_id", ASCENDING)], unique=True),
        IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
    ],
    mongo.BOOKINGS: [IndexModel([("slot", ASCENDING)], unique=True)],  # no double-booking
    mongo.APPROVALS: [
        IndexModel([("thread_id", ASCENDING)], unique=True),
        IndexModel([("status", ASCENDING), ("created_at", ASCENDING)]),
    ],
}


def vector_index_model(name: str, dimensions: int) -> SearchIndexModel:
    """Atlas Vector Search index on kb_chunks.embedding (+ filter on language/source)."""
    return SearchIndexModel(
        name=name,
        type="vectorSearch",
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "source_doc"},
                {"type": "filter", "path": "language"},
            ]
        },
    )


async def create_indexes(db: AsyncDatabase[dict[str, Any]]) -> None:
    for collection, models in INDEXES.items():
        await db[collection].create_indexes(models)
