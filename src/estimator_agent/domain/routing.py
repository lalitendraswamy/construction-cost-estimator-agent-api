from __future__ import annotations

from pydantic import BaseModel, Field

from estimator_agent.domain.enums import Intent


class RouteDecision(BaseModel):
    """Structured output of the Supervisor LLM.

    The LLM only classifies `intent`. Which agent runs next is decided by pure code
    (agent/routing.py) so routing stays predictable and unit-testable.
    """

    intent: Intent = Field(description="What the user wants in their latest message")
    reason: str = Field(description="One short sentence explaining the classification")
