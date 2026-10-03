"""Runtime context: per-run dependencies injected into every node.

LangGraph separates **state** (serialised into checkpoints, changes every step) from
**context** (static for a run, never checkpointed: clients, repos, settings). Nodes
receive it as `runtime: Runtime[AgentContext]`; tests pass a context full of fakes.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.retrievers import BaseRetriever

from estimator_agent.core.config import Settings
from estimator_agent.core.llm import ModelRegistry
from estimator_agent.db.repositories import (
    ApprovalRepository,
    BookingRepository,
    LeadRepository,
    RateRepository,
)
from estimator_agent.services.notifications import Notifier


@dataclass(frozen=True)
class AgentContext:
    settings: Settings
    models: ModelRegistry
    rates: RateRepository
    leads: LeadRepository
    bookings: BookingRepository
    approvals: ApprovalRepository
    notifier: Notifier
    retriever: BaseRetriever | None = None
