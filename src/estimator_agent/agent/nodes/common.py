from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware.types import InputAgentState
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.config import get_config


def recent_dialogue(messages: Sequence[AnyMessage], n: int = 8) -> list[AnyMessage]:
    """Last n human/assistant turns, without tool-call plumbing. Keeps prompts small
    (cost + latency) and avoids leaking another agent's tool messages into a prompt."""
    dialogue: list[AnyMessage] = [
        m
        for m in messages
        if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and not m.tool_calls)
    ]
    return dialogue[-n:]


def agent_input(messages: Sequence[AnyMessage]) -> InputAgentState:
    """Input for a `create_agent` graph (its schema also accepts message dicts)."""
    history: list[AnyMessage | dict[str, Any]] = list(messages)
    return {"messages": history}


def current_thread_id() -> str:
    return str(get_config()["configurable"]["thread_id"])
