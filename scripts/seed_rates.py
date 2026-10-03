"""Seed placeholder rate cards (3 tiers × Visakhapatnam). `python -m scripts.seed_rates`

Every card is marked source="placeholder" so the UI shows a "sample rates" banner until
Ravikumar replaces them via PUT /api/v1/admin/rates.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from estimator_agent.core.config import get_settings
from estimator_agent.db import mongo
from estimator_agent.db.repositories.mongo import MongoRateRepository
from estimator_agent.domain import RateCard

SEED = Path(__file__).resolve().parents[1] / "data" / "seed" / "rate_cards.json"


async def main() -> None:
    settings = get_settings()
    client = mongo.create_client(settings)
    repo = MongoRateRepository(mongo.get_database(client, settings))
    cards = [RateCard.model_validate(c) for c in json.loads(SEED.read_text("utf-8"))]
    for card in cards:
        await repo.upsert(card)
        print(f"upserted {card.city}/{card.tier}: ₹{card.base_rate_per_sqft}/sqft ({card.source})")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
