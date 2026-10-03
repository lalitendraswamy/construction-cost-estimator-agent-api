"""ChatRunner: the application service between HTTP and the graph.

Owns the per-thread protocol:
  * new message, thread idle             -> run graph with {"messages": [HumanMessage]}
  * new message, thread paused (ask/confirm) -> Command(resume=message)
  * new message, thread paused for owner -> don't run; tell user it's under review
and turns LangGraph's stream into transport-neutral TurnEvents (the API maps them to SSE).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.types import Command, StreamMode

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.graph import EstimatorGraph
from estimator_agent.core.exceptions import ConflictError, NotFoundError
from estimator_agent.core.logging import get_logger
from estimator_agent.domain import InputMode, Intent, Language
from estimator_agent.observability.tracing import new_usage_tracker, turn_config
from estimator_agent.services.formatting import UNDER_REVIEW

log = get_logger(__name__)

OWNER_APPROVAL = "owner_approval"
STREAM_MODES: list[StreamMode] = ["updates", "messages", "custom"]


@dataclass(frozen=True)
class TurnEvent:
    event: str  # progress | token | interrupt | final
    data: dict[str, Any] = field(default_factory=dict)


class ChatRunner:
    def __init__(self, graph: EstimatorGraph, context: AgentContext) -> None:
        self.graph = graph
        self.context = context

    # ------------------------------------------------------------------ queries
    async def pending_interrupt(self, thread_id: str) -> dict[str, Any] | None:
        snapshot = await self.graph.aget_state(turn_config(thread_id))
        return snapshot.interrupts[0].value if snapshot.interrupts else None

    async def thread_view(self, thread_id: str) -> dict[str, Any]:
        snapshot = await self.graph.aget_state(turn_config(thread_id))
        values = snapshot.values or {}
        if not values:
            raise NotFoundError(f"Unknown thread {thread_id}")
        language = values.get("language", Language.EN)
        return {
            "thread_id": thread_id,
            "language": language,
            "spec": values.get("spec"),
            "missing_fields": values.get("missing_fields", []),
            "estimate": values.get("estimate"),
            "variants": values.get("variants", []),
            "approval": values.get("approval"),
            "lead": values.get("lead"),
            "messages": [
                {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.text}
                for m in values.get("messages", [])[-20:]
            ],
            "pending": _public_interrupt(snapshot.interrupts[0].value, language)
            if snapshot.interrupts
            else None,
        }

    # ------------------------------------------------------------------ commands
    async def stream_message(
        self,
        thread_id: str,
        message: str,
        *,
        input_mode: InputMode = InputMode.TEXT,
        language: Language | None = None,
    ) -> AsyncIterator[TurnEvent]:
        pending = await self.pending_interrupt(thread_id)
        if pending and pending.get("type") == OWNER_APPROVAL:
            lang = language or await self._language(thread_id)
            yield TurnEvent(
                "final", {"thread_id": thread_id, "reply": UNDER_REVIEW[lang], "language": lang}
            )
            return
        graph_input: Any
        if pending:  # the user is answering a question / confirmation
            graph_input = Command(resume=message, update={"input_mode": input_mode})
        else:
            graph_input = {
                "messages": [HumanMessage(content=message)],
                "input_mode": input_mode,
                "requested_language": language,
            }
        async for event in self._stream(thread_id, graph_input):
            yield event

    async def stream_resume(self, thread_id: str, value: Any) -> AsyncIterator[TurnEvent]:
        pending = await self.pending_interrupt(thread_id)
        if pending is None:
            raise ConflictError("Thread is not waiting for input")
        if pending.get("type") == OWNER_APPROVAL:
            raise ConflictError("Thread is waiting for owner approval")
        async for event in self._stream(thread_id, Command(resume=value)):
            yield event

    async def resume_owner_approval(
        self, thread_id: str, decision: dict[str, Any]
    ) -> dict[str, Any]:
        pending = await self.pending_interrupt(thread_id)
        if not pending or pending.get("type") != OWNER_APPROVAL:
            raise NotFoundError(f"Thread {thread_id} has no pending approval")
        await self.graph.ainvoke(
            Command(resume=decision), turn_config(thread_id, actor="owner"), context=self.context
        )
        await self.context.approvals.resolve(thread_id, decision)
        return await self.thread_view(thread_id)

    # ------------------------------------------------------------------ internals
    async def _stream(self, thread_id: str, graph_input: Any) -> AsyncIterator[TurnEvent]:
        usage = new_usage_tracker()
        config = turn_config(thread_id, callbacks=[usage])
        async for namespace, mode, chunk in self.graph.astream(
            graph_input,
            config,
            context=self.context,
            stream_mode=STREAM_MODES,
            subgraphs=True,  # also surface progress events from the estimator subgraph
        ):
            if mode == "custom" and isinstance(chunk, dict) and chunk.get("type") == "progress":
                yield TurnEvent("progress", {"stage": chunk["stage"], "label": chunk["label"]})
            elif mode == "messages":
                msg, meta = cast(tuple[BaseMessage, dict[str, Any]], chunk)
                # Stream only the Responder's tokens; other LLM calls are internal.
                is_responder = not namespace and meta.get("langgraph_node") == "responder"
                if is_responder and isinstance(msg, AIMessage) and msg.text:
                    yield TurnEvent("token", {"text": msg.text})

        snapshot = await self.graph.aget_state(config)
        values = snapshot.values
        language = values.get("language", Language.EN)
        log.info("turn_completed", thread_id=thread_id, usage=usage.usage_metadata)

        if snapshot.interrupts:
            yield TurnEvent(
                "interrupt",
                {
                    "thread_id": thread_id,
                    **_public_interrupt(snapshot.interrupts[0].value, language),
                },
            )
            return
        yield TurnEvent("final", _final_payload(thread_id, values))

    async def _language(self, thread_id: str) -> Language:
        snapshot = await self.graph.aget_state(turn_config(thread_id))
        return (snapshot.values or {}).get("language", Language.EN)  # type: ignore[no-any-return]


def _public_interrupt(value: dict[str, Any], language: Language) -> dict[str, Any]:
    """What the end user may see about a pause. Never leak an unapproved estimate."""
    if value.get("type") == OWNER_APPROVAL:
        return {"type": OWNER_APPROVAL, "message": UNDER_REVIEW[language], "language": language}
    return {**value, "language": language}


def _final_payload(thread_id: str, values: dict[str, Any]) -> dict[str, Any]:
    last_ai = next(
        (m for m in reversed(values.get("messages", [])) if isinstance(m, AIMessage)), None
    )
    intent = values.get("intent")
    return {
        "thread_id": thread_id,
        "reply": last_ai.text if last_ai else "",
        "language": values.get("language", Language.EN),
        "intent": intent,
        "estimate": values.get("estimate") if intent in {Intent.ESTIMATE, Intent.MODIFY} else None,
        "sources": values.get("sources", []),
        "audio_url": values.get("audio_url"),
    }
