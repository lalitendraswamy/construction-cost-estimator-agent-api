"""Composition root: builds every long-lived dependency once per process.

`default_container` wires real infrastructure. Tests swap in a container of fakes via
`create_app(container_factory=...)`; nothing else in the app needs to know.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass

from langchain_core.retrievers import BaseRetriever

from estimator_agent.agent.checkpointer import checkpointer_from_settings
from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.graph import build_graph
from estimator_agent.agent.runner import ChatRunner
from estimator_agent.core.config import Settings, export_provider_env
from estimator_agent.core.llm import LangChainModelRegistry, ModelRegistry
from estimator_agent.core.logging import get_logger
from estimator_agent.db import mongo
from estimator_agent.db.repositories.mongo import (
    MongoApprovalRepository,
    MongoBookingRepository,
    MongoLeadRepository,
    MongoRateRepository,
)
from estimator_agent.rag.vectorstore import build_retriever, build_vector_store
from estimator_agent.services.notifications import build_notifier

log = get_logger(__name__)


@dataclass(frozen=True)
class Container:
    settings: Settings
    context: AgentContext
    runner: ChatRunner
    ready_check: Callable[[], Awaitable[bool]]


ContainerFactory = Callable[[Settings], AbstractAsyncContextManager[Container]]


def _try_build_retriever(settings: Settings, models: ModelRegistry) -> BaseRetriever | None:
    try:
        return build_retriever(build_vector_store(settings, models.embeddings()))
    except Exception as exc:  # missing extra / key: run without RAG rather than crash
        log.warning("rag_disabled", reason=str(exc))
        return None


@asynccontextmanager
async def default_container(settings: Settings) -> AsyncIterator[Container]:
    export_provider_env(settings)
    client = mongo.create_client(settings)
    db = mongo.get_database(client, settings)
    models = LangChainModelRegistry(settings)
    # Fail fast: a missing API key or a typo in LLM_*_MODEL should stop startup with a clear
    # error, not surface later as a 500 on the first chat message.
    models.chat("small")
    models.chat("strong")
    context = AgentContext(
        settings=settings,
        models=models,
        rates=MongoRateRepository(db),
        leads=MongoLeadRepository(db),
        bookings=MongoBookingRepository(db),
        approvals=MongoApprovalRepository(db),
        notifier=build_notifier(settings),
        retriever=_try_build_retriever(settings, models),
    )
    try:
        async with checkpointer_from_settings(settings) as checkpointer:
            graph = build_graph(
                checkpointer, approval_threshold_inr=settings.owner_approval_threshold_inr
            )
            yield Container(
                settings=settings,
                context=context,
                runner=ChatRunner(graph, context),
                ready_check=lambda: mongo.ping(db),
            )
    finally:
        await client.close()
