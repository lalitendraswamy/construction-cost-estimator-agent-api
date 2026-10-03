"""Repository interfaces (ports). Graph nodes and tools depend on THESE, not on pymongo,
so tests can pass in-memory fakes (tests/fakes.py) and the storage can change freely."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from estimator_agent.domain import Estimate, Lead, ProjectSpec, QualityTier, RateCard


class RateRepository(Protocol):
    async def get(self, city: str, tier: QualityTier) -> RateCard | None: ...

    async def upsert(self, card: RateCard) -> None: ...

    async def list_all(self) -> list[RateCard]: ...


class LeadRepository(Protocol):
    async def upsert_for_thread(
        self,
        thread_id: str,
        lead: Lead,
        *,
        language: str,
        spec: ProjectSpec | None,
        estimate: Estimate | None,
    ) -> str: ...

    async def get_by_thread(self, thread_id: str) -> Lead | None: ...


class BookingRepository(Protocol):
    async def booked_slots(self, start: datetime, end: datetime) -> set[datetime]: ...

    async def create(self, *, thread_id: str, slot: datetime, mode: str) -> str:
        """Returns booking id. Raises ConflictError if the slot is taken."""
        ...


class ApprovalRepository(Protocol):
    async def upsert_pending(self, thread_id: str, estimate: Estimate) -> bool:
        """Idempotent. Returns True only when a NEW pending request was created."""
        ...

    async def list_pending(self) -> list[dict[str, Any]]: ...

    async def resolve(self, thread_id: str, decision: dict[str, Any]) -> None: ...
