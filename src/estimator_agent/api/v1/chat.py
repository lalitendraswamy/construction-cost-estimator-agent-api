"""POST /chat (SSE stream of a turn) and POST /chat/resume (answer a pending interrupt).

SSE events: progress | token | interrupt | final | error
Pass ?stream=false to get just the final/interrupt event as JSON (handy for curl/tests).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from sse_starlette import EventSourceResponse

from estimator_agent.agent.runner import TurnEvent
from estimator_agent.api.deps import RunnerDep
from estimator_agent.api.rate_limit import chat_limit, limiter
from estimator_agent.core.exceptions import ConflictError, EstimatorError
from estimator_agent.core.logging import get_logger
from estimator_agent.schemas.chat import ChatRequest, ResumeRequest, TurnResponse

router = APIRouter(prefix="/chat", tags=["chat"])
log = get_logger(__name__)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, default=_default)


def _default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return str(obj)


async def _to_sse(events: AsyncIterator[TurnEvent]) -> AsyncIterator[dict[str, str]]:
    try:
        async for ev in events:
            yield {"event": ev.event, "data": _json(ev.data)}
    except EstimatorError as exc:
        yield {"event": "error", "data": _json({"title": exc.title, "detail": exc.detail})}
    except Exception:
        log.exception("chat_stream_failed")
        yield {"event": "error", "data": _json({"title": "Internal error"})}


async def _respond(events: AsyncIterator[TurnEvent], stream: bool) -> Any:
    if stream:
        return EventSourceResponse(_to_sse(events))
    last: TurnEvent | None = None
    async for ev in events:
        if ev.event in {"final", "interrupt"}:
            last = ev
    assert last is not None
    return TurnResponse(event=last.event, data=json.loads(_json(last.data)))


@router.post("", response_model=None)
@limiter.limit(chat_limit)
async def chat(request: Request, body: ChatRequest, runner: RunnerDep, stream: bool = True) -> Any:
    events = runner.stream_message(
        body.thread_id, body.message, input_mode=body.input_mode, language=body.language
    )
    return await _respond(events, stream)


@router.post("/resume", response_model=None)
@limiter.limit(chat_limit)
async def resume(
    request: Request, body: ResumeRequest, runner: RunnerDep, stream: bool = True
) -> Any:
    # Validate before streaming so conflicts surface as a proper 409, not an SSE error.
    if await runner.pending_interrupt(body.thread_id) is None:
        raise ConflictError("Thread is not waiting for input")
    return await _respond(runner.stream_resume(body.thread_id, body.value), stream)
