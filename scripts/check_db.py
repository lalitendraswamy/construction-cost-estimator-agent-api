"""Show what the configured MongoDB contains. `python -m scripts.check_db` / `make check-db`

Use it to confirm setup ran against the right cluster (local vs Atlas) before/after deploys.
"""

from __future__ import annotations

import asyncio
import re

from estimator_agent.core.config import get_settings
from estimator_agent.db import mongo


def _mask(uri: str) -> str:
    return re.sub(r"//[^@/]+@", "//***:***@", uri)  # hide credentials


async def main() -> None:
    settings = get_settings()
    client = mongo.create_client(settings)
    db = mongo.get_database(client, settings)
    print(f"cluster   : {_mask(settings.mongodb_uri)}")
    print(f"database  : {settings.mongodb_db}")
    if not await mongo.ping(db, timeout_s=10):
        print("status    : UNREACHABLE (check URI / Atlas Network Access)")
        await client.close()
        return

    rates = await db[mongo.RATES].count_documents({})
    chunks = await db[mongo.KB_CHUNKS].count_documents({})
    indexes: list[str] = []
    if mongo.KB_CHUNKS in await db.list_collection_names():
        cursor = await db[mongo.KB_CHUNKS].list_search_indexes()
        indexes = [f"{i['name']}={i.get('status')}" async for i in cursor]

    ok = rates >= 3 and chunks > 0 and any(s.endswith("READY") for s in indexes)
    print(f"rates     : {rates} rate cards {'OK' if rates >= 3 else '-> run: make seed'}")
    print(f"kb_chunks : {chunks} chunks {'OK' if chunks else '-> run: make ingest'}")
    print(f"vector idx: {indexes or 'none -> run: make indexes'}")
    print(f"verdict   : {'READY' if ok else 'NOT READY'}")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
