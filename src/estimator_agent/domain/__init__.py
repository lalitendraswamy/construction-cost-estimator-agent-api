"""Pure domain models (Pydantic). No I/O, no LangChain imports: easy to test and reuse."""

from estimator_agent.domain.enums import (
    ApprovalStatus,
    ContactChannel,
    Extra,
    InputMode,
    Intent,
    Language,
    ProjectType,
    QualityTier,
)
from estimator_agent.domain.estimate import Estimate, LineItem, MaterialQuantities
from estimator_agent.domain.lead import Lead
from estimator_agent.domain.project_spec import ProjectSpec
from estimator_agent.domain.rates import RateCard
from estimator_agent.domain.routing import RouteDecision

# Every custom type that can end up inside a checkpoint. Registered with the checkpoint
# serializer so deserialization is allow-listed (see agent/checkpointer.py).
CHECKPOINT_TYPES: tuple[type, ...] = (
    ProjectSpec,
    Estimate,
    LineItem,
    MaterialQuantities,
    Lead,
    RateCard,
    RouteDecision,
    Intent,
    Language,
    InputMode,
    ProjectType,
    QualityTier,
    Extra,
    ApprovalStatus,
    ContactChannel,
)

__all__ = [
    "CHECKPOINT_TYPES",
    "ApprovalStatus",
    "ContactChannel",
    "Estimate",
    "Extra",
    "InputMode",
    "Intent",
    "Language",
    "Lead",
    "LineItem",
    "MaterialQuantities",
    "ProjectSpec",
    "ProjectType",
    "QualityTier",
    "RateCard",
    "RouteDecision",
]
