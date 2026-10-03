"""LangSmith tracing + per-turn token accounting.

Tracing itself needs no code: with LANGSMITH_TRACING=true and LANGSMITH_API_KEY set
(exported in core.config.export_provider_env) every LangChain/LangGraph run is traced.
What we add: run names, tags and metadata so traces are searchable by thread, plus a
callback that totals tokens per model for each turn (cost per estimate, PRD §7).
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler, UsageMetadataCallbackHandler
from langchain_core.runnables import RunnableConfig


def turn_config(
    thread_id: str, *, callbacks: list[BaseCallbackHandler] | None = None, **metadata: Any
) -> RunnableConfig:
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": "estimator_turn",
        "tags": ["construction-estimator"],
        "metadata": {"thread_id": thread_id, **metadata},
        "callbacks": callbacks or [],
    }


def new_usage_tracker() -> UsageMetadataCallbackHandler:
    """Collects `usage_metadata` from every chat-model call, keyed by model name."""
    return UsageMetadataCallbackHandler()
