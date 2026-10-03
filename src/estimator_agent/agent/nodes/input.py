"""Input node: detect language (script first, small LLM only if needed) and reset
per-turn scratch fields."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime
from pydantic import BaseModel

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.prompts.input import LANGUAGE_DETECT_PROMPT
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.agent.tools.language import detect_language
from estimator_agent.core.llm import structured
from estimator_agent.domain import InputMode, Language


class LanguageGuess(BaseModel):
    language: Language
    confident: bool


async def input_node(state: EstimatorState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
    emit_progress("detecting_language")
    text = state["messages"][-1].text
    previous = state.get("language", Language.EN)

    if requested := state.get("requested_language"):
        language = requested
    elif script_lang := await detect_language.ainvoke({"text": text}):
        language = Language(script_lang)
    elif len(text.split()) < 3:
        language = previous  # "G+1, standard" says nothing about language: keep the old one
    else:
        chain = LANGUAGE_DETECT_PROMPT | structured(
            runtime.context.models.chat("small"), LanguageGuess
        )
        guess = await chain.ainvoke({"text": text})
        language = guess.language if guess.confident else previous

    return {
        "language": language,
        "requested_language": None,
        "input_mode": state.get("input_mode", InputMode.TEXT),
        # reset per-turn scratch
        "draft": None,
        "sources": [],
        "audio_url": None,
    }
