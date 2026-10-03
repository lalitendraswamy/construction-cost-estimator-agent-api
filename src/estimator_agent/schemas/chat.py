from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from estimator_agent.domain import InputMode, Language

THREAD_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"


class ChatRequest(BaseModel):
    thread_id: str = Field(default_factory=lambda: uuid4().hex, pattern=THREAD_ID_PATTERN)
    message: str = Field(min_length=1, max_length=2000)
    input_mode: InputMode = InputMode.TEXT
    language: Language | None = Field(None, description="Force reply language (UI toggle)")


class ResumeRequest(BaseModel):
    thread_id: str = Field(pattern=THREAD_ID_PATTERN)
    value: Any = Field(
        description="Answer to the pending interrupt, e.g. 'yes' or {'confirmed': true}"
    )


class TurnResponse(BaseModel):
    """Non-streaming response (?stream=false): the final or interrupt event."""

    event: str
    data: dict[str, Any]
