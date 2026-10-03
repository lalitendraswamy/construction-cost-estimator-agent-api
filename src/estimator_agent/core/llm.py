"""Model registry: the ONE place that knows which concrete LLM backs each tier.

Nodes ask for a *tier* ("small" | "strong"), never a vendor class. That gives you:
  * model swap via env var (init_chat_model "provider:model" strings, e.g.
    "google_genai:gemini-3.5-flash-lite" vs "google_genai:gemini-3.8-flash")
  * cost/quality split (small model routes, strong model explains)
  * trivial test doubles (tests pass a registry that returns fake models)
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Literal, Protocol, TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel

from estimator_agent.core.config import Settings

ModelTier = Literal["small", "strong"]
T = TypeVar("T", bound=BaseModel)


def structured(model: BaseChatModel, schema: type[T]) -> Runnable[Any, T]:
    """Structured output via Gemini's native JSON-schema mode.

    The schema is enforced server-side (response_json_schema), so the model cannot return
    a malformed RouteDecision / SpecExtraction. More reliable than parsing tool calls.
    """
    return model.with_structured_output(schema, method="json_schema")  # type: ignore[return-value]


class ModelRegistry(Protocol):
    def chat(self, tier: ModelTier) -> BaseChatModel: ...

    def embeddings(self) -> Embeddings: ...


def _provider(model: str) -> str:
    return model.split(":", 1)[0] if ":" in model else ""


class LangChainModelRegistry:
    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def _build(
        self, model: str, temperature: float | None, thinking_level: str | None
    ) -> BaseChatModel:
        kwargs: dict[str, Any] = {
            "timeout": self._s.llm_timeout_seconds,
            "max_retries": self._s.llm_max_retries,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if thinking_level and _provider(model) == "google_genai":
            kwargs["thinking_level"] = thinking_level  # Gemini 3+ reasoning depth
        chat_model: BaseChatModel = init_chat_model(model, **kwargs)
        return chat_model

    @cached_property
    def _small(self) -> BaseChatModel:
        s = self._s
        return self._build(s.llm_small_model, s.llm_small_temperature, s.llm_small_thinking_level)

    @cached_property
    def _strong(self) -> BaseChatModel:
        s = self._s
        return self._build(s.llm_strong_model, None, s.llm_strong_thinking_level)

    def chat(self, tier: ModelTier) -> BaseChatModel:
        return self._small if tier == "small" else self._strong

    def embeddings(self) -> Embeddings:
        # gemini-embedding-2 auto-normalises truncated dimensions (768 is recommended).
        return GoogleGenerativeAIEmbeddings(
            model=self._s.embeddings_model,
            output_dimensionality=self._s.embeddings_dimensions,
        )
