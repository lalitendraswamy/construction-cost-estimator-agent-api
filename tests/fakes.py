"""Test doubles: a scripted chat model and in-memory repositories.

The graph never knows it is under test: it receives these through AgentContext.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import Field

from estimator_agent.agent.checkpointer import build_serializer
from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.graph import build_graph
from estimator_agent.agent.runner import ChatRunner
from estimator_agent.api.container import Container
from estimator_agent.core.config import Settings
from estimator_agent.core.exceptions import ConflictError
from estimator_agent.domain import Estimate, Lead, ProjectSpec, QualityTier, RateCard

SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "seed" / "rate_cards.json"


# ----------------------------------------------------------------- LLM
class ScriptedChatModel(BaseChatModel):
    """Deterministic stand-in for an LLM.

    structured_outputs: schema class name -> queue of outputs for with_structured_output()
    responses:          queue of str | AIMessage for plain calls (AIMessage may carry tool_calls)
    """

    structured_outputs: dict[str, list[Any]] = Field(default_factory=dict)
    responses: list[Any] = Field(default_factory=list)
    default_text: str = "ok"

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kw: Any
    ) -> ChatResult:
        nxt = self.responses.pop(0) if self.responses else self.default_text
        msg = nxt if isinstance(nxt, AIMessage) else AIMessage(content=nxt)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools: Any, **kwargs: Any) -> Runnable[Any, Any]:
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Runnable[Any, Any]:
        name = schema.__name__

        def _pick(_: Any) -> Any:
            queue = self.structured_outputs.get(name)
            if not queue:
                raise AssertionError(f"No scripted structured output left for {name}")
            item = queue.pop(0)
            return item if isinstance(item, schema) else schema.model_validate(item)

        return RunnableLambda(_pick)


class FakeModelRegistry:
    def __init__(self, model: ScriptedChatModel) -> None:
        self.model = model

    def chat(self, tier: str) -> BaseChatModel:
        return self.model

    def embeddings(self) -> Embeddings:
        raise NotImplementedError


class FakeRetriever(BaseRetriever):
    docs: list[Document] = Field(default_factory=list)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return self.docs


# ----------------------------------------------------------------- repositories
class InMemoryRateRepository:
    def __init__(self, cards: list[RateCard] | None = None) -> None:
        self.cards = {(c.city, c.tier): c for c in (cards or [])}

    @classmethod
    def seeded(cls) -> InMemoryRateRepository:
        return cls([RateCard.model_validate(c) for c in json.loads(SEED_FILE.read_text("utf-8"))])

    async def get(self, city: str, tier: QualityTier) -> RateCard | None:
        return self.cards.get((city, tier))

    async def upsert(self, card: RateCard) -> None:
        self.cards[(card.city.lower(), card.tier)] = card

    async def list_all(self) -> list[RateCard]:
        return list(self.cards.values())


class InMemoryLeadRepository:
    def __init__(self) -> None:
        self.leads: dict[str, Lead] = {}

    async def upsert_for_thread(self, thread_id: str, lead: Lead, **_: Any) -> str:
        current = self.leads.get(thread_id, Lead())
        self.leads[thread_id] = current.model_copy(update=lead.model_dump(exclude_none=True))
        return thread_id

    async def get_by_thread(self, thread_id: str) -> Lead | None:
        return self.leads.get(thread_id)


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self.bookings: dict[datetime, str] = {}

    async def booked_slots(self, start: datetime, end: datetime) -> set[datetime]:
        return {s for s in self.bookings if start <= s < end}

    async def create(self, *, thread_id: str, slot: datetime, mode: str) -> str:
        if slot in self.bookings:
            raise ConflictError("taken")
        self.bookings[slot] = thread_id
        return f"bk-{len(self.bookings)}"


class InMemoryApprovalRepository:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    async def upsert_pending(self, thread_id: str, estimate: Estimate) -> bool:
        created = thread_id not in self.items or self.items[thread_id]["status"] != "pending"
        self.items[thread_id] = {
            "thread_id": thread_id,
            "status": "pending",
            "estimate": estimate.model_dump(mode="json"),
        }
        return created

    async def list_pending(self) -> list[dict[str, Any]]:
        return [v for v in self.items.values() if v["status"] == "pending"]

    async def resolve(self, thread_id: str, decision: dict[str, Any]) -> None:
        self.items[thread_id]["status"] = decision.get("action", "approved")


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send_email(self, to: str, subject: str, body: str) -> str:
        self.sent.append({"to": to, "subject": subject, "body": body})
        return f"msg-{len(self.sent)}"


# ----------------------------------------------------------------- wiring
def settings_for_tests(**overrides: Any) -> Settings:
    return Settings(_env_file=None, app_env="test", admin_api_key="test-admin-key", **overrides)  # type: ignore[call-arg]


def make_context(
    model: ScriptedChatModel, settings: Settings | None = None, **overrides: Any
) -> AgentContext:
    deps: dict[str, Any] = {
        "settings": settings or settings_for_tests(),
        "models": FakeModelRegistry(model),
        "rates": InMemoryRateRepository.seeded(),
        "leads": InMemoryLeadRepository(),
        "bookings": InMemoryBookingRepository(),
        "approvals": InMemoryApprovalRepository(),
        "notifier": RecordingNotifier(),
        "retriever": None,
    }
    deps.update(overrides)
    return AgentContext(**deps)


def make_runner(context: AgentContext) -> ChatRunner:
    from langgraph.checkpoint.memory import InMemorySaver

    graph = build_graph(
        InMemorySaver(serde=build_serializer()),
        approval_threshold_inr=context.settings.owner_approval_threshold_inr,
    )
    return ChatRunner(graph, context)


def fake_container_factory(context: AgentContext):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def factory(settings: Settings) -> AsyncIterator[Container]:
        async def ready() -> bool:
            return True

        yield Container(
            settings=settings, context=context, runner=make_runner(context), ready_check=ready
        )

    return factory


def spec(**kw: Any) -> ProjectSpec:
    return ProjectSpec(**kw)
