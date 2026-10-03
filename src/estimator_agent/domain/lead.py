from __future__ import annotations

from pydantic import BaseModel

from estimator_agent.domain.enums import ContactChannel


class Lead(BaseModel):
    name: str | None = None
    phone: str | None = None
    channel: ContactChannel | None = None
    preferred_slot: str | None = None
    booking_id: str | None = None
    owner_notified: bool = False
