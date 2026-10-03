"""Create Mongo indexes + the Atlas Vector Search index. `python -m scripts.create_indexes`"""

from __future__ import annotations

import asyncio

from pymongo.errors import OperationFailure

from estimator_agent.core.config import get_settings
from estimator_agent.db import mongo
from estimator_agent.db.indexes import create_indexes, vector_index_model


async def main() -> None:
    settings = get_settings()
    client = mongo.create_client(settings)
    db = mongo.get_database(client, settings)
    await create_indexes(db)
    print("regular indexes ok")

    # Must equal the embedding size (EMBEDDINGS_DIMENSIONS). If you change the embeddings
    # model/dimensions later: drop the index, recreate it, and re-run `make ingest`.
    dims = settings.embeddings_dimensions
    if mongo.KB_CHUNKS not in await db.list_collection_names():
        await db.create_collection(mongo.KB_CHUNKS)
    try:
        await db[mongo.KB_CHUNKS].create_search_index(
            vector_index_model(settings.vector_index_name, dims)
        )
        print(f"vector index '{settings.vector_index_name}' ({dims} dims) requested")
    except OperationFailure as exc:
        print(f"vector index not created: {exc}")  # already exists / not Atlas
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
