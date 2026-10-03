"""MongoDB implementations of the repository protocols."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from estimator_agent.core.exceptions import ConflictError
from estimator_agent.db import mongo
from estimator_agent.domain import Estimate, Lead, ProjectSpec, QualityTier, RateCard

Doc = dict[str, Any]


def _now() -> datetime:
    return datetime.now(UTC)


class MongoRateRepository:
    def __init__(self, db: AsyncDatabase[Doc]) -> None:
        self._col = db[mongo.RATES]

    async def get(self, city: str, tier: QualityTier) -> RateCard | None:
        doc = await self._col.find_one({"city": city.lower(), "tier": tier.value}, {"_id": 0})
        return RateCard.model_validate(doc) if doc else None

    async def upsert(self, card: RateCard) -> None:
        data = card.model_dump(mode="python")
        data["city"] = card.city.lower()
        data["updated_at"] = _now()
        await self._col.replace_one(
            {"city": data["city"], "tier": card.tier.value}, data, upsert=True
        )

    async def list_all(self) -> list[RateCard]:
        return [RateCard.model_validate(d) async for d in self._col.find({}, {"_id": 0})]


class MongoLeadRepository:
    def __init__(self, db: AsyncDatabase[Doc]) -> None:
        self._col = db[mongo.LEADS]

    async def upsert_for_thread(
        self,
        thread_id: str,
        lead: Lead,
        *,
        language: str,
        spec: ProjectSpec | None,
        estimate: Estimate | None,
    ) -> str:
        doc = await self._col.find_one_and_update(
            {"thread_id": thread_id},
            {
                "$set": {
                    **lead.model_dump(mode="json", exclude_none=True),
                    "language": language,
                    "spec": spec.model_dump(mode="json") if spec else None,
                    "estimate": estimate.model_dump(mode="json") if estimate else None,
                    "updated_at": _now(),
                },
                "$setOnInsert": {"status": "new", "created_at": _now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        assert doc is not None  # upsert=True + AFTER always returns a document
        return str(doc["_id"])

    async def get_by_thread(self, thread_id: str) -> Lead | None:
        doc = await self._col.find_one({"thread_id": thread_id})
        return Lead.model_validate(doc) if doc else None


class MongoBookingRepository:
    def __init__(self, db: AsyncDatabase[Doc]) -> None:
        self._col = db[mongo.BOOKINGS]

    async def booked_slots(self, start: datetime, end: datetime) -> set[datetime]:
        cursor = self._col.find(
            {"slot": {"$gte": start, "$lt": end}, "status": "booked"}, {"slot": 1}
        )
        return {d["slot"] async for d in cursor}

    async def create(self, *, thread_id: str, slot: datetime, mode: str) -> str:
        try:
            res = await self._col.insert_one(
                {
                    "thread_id": thread_id,
                    "slot": slot,
                    "mode": mode,
                    "status": "booked",
                    "created_at": _now(),
                }
            )
        except DuplicateKeyError as e:
            raise ConflictError(f"Slot {slot.isoformat()} is already booked") from e
        return str(res.inserted_id)


class MongoApprovalRepository:
    def __init__(self, db: AsyncDatabase[Doc]) -> None:
        self._col = db[mongo.APPROVALS]

    async def upsert_pending(self, thread_id: str, estimate: Estimate) -> bool:
        res = await self._col.update_one(
            {"thread_id": thread_id, "status": "pending"},
            {
                "$set": {"estimate": estimate.model_dump(mode="json"), "updated_at": _now()},
                "$setOnInsert": {"created_at": _now()},
            },
            upsert=True,
        )
        return res.upserted_id is not None

    async def list_pending(self) -> list[Doc]:
        cursor = self._col.find({"status": "pending"}, {"_id": 0}).sort("created_at", 1)
        return [d async for d in cursor]

    async def resolve(self, thread_id: str, decision: Doc) -> None:
        await self._col.update_one(
            {"thread_id": thread_id, "status": "pending"},
            {
                "$set": {
                    "status": decision.get("action", "approved"),
                    "decision": decision,
                    "resolved_at": _now(),
                }
            },
        )
