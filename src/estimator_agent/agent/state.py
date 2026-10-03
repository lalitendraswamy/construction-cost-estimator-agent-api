"""EstimatorState: the shared, checkpointed state of the parent graph (PRD §4).

Each key is a *channel*. A key without a reducer is overwritten by whichever node
writes it; a key with `Annotated[T, reducer]` is combined: reducer(old, new).
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict, TypeVar

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from estimator_agent.domain import (
    ApprovalStatus,
    Estimate,
    InputMode,
    Intent,
    Language,
    Lead,
    ProjectSpec,
)

M = TypeVar("M", bound=BaseModel)


def _merge_model(left: M | None, right: M | dict[str, Any] | None) -> M | None:
    """Custom reducer: shallow-merge only the fields the writer actually set.

    `ProjectSpec(tier="premium")` merged into a full spec changes tier and keeps the rest,
    which is exactly what a "what-if" re-estimate (F8) needs.
    """
    if right is None:
        return left
    if left is None:
        return right if isinstance(right, BaseModel) else None
    patch = (
        right.model_dump(exclude_unset=True, exclude_none=True)
        if isinstance(right, BaseModel)
        else {k: v for k, v in right.items() if v is not None}
    )
    if "extras" in patch and hasattr(left, "extras"):
        patch["extras"] = sorted(set(left.extras) | set(patch["extras"]))
    return left.model_copy(update=patch)


def merge_spec(left: ProjectSpec | None, right: ProjectSpec | dict[str, Any] | None) -> ProjectSpec:
    return _merge_model(left, right) or ProjectSpec()


def merge_lead(left: Lead | None, right: Lead | dict[str, Any] | None) -> Lead:
    return _merge_model(left, right) or Lead()


class EstimatorState(TypedDict, total=False):
    # conversation
    messages: Annotated[list[AnyMessage], add_messages]  # append / update-by-id
    language: Language
    requested_language: Language | None  # explicit UI toggle; consumed by Input node
    input_mode: InputMode
    # routing
    intent: Intent
    route_reason: str
    next_agent: str
    # intake
    spec: Annotated[ProjectSpec, merge_spec]  # custom merge reducer
    missing_fields: list[str]
    pending_question: str | None
    # estimation
    estimate: Estimate | None
    variants: Annotated[list[Estimate], operator.add]  # fan-in / history
    approval: ApprovalStatus
    # lead
    lead: Annotated[Lead, merge_lead]
    # per-turn scratch for the Responder
    draft: str | None  # agent output the Responder turns into the reply
    sources: list[str]
    audio_url: str | None
