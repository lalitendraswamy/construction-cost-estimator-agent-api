from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Path

from estimator_agent.api.deps import RunnerDep
from estimator_agent.schemas.chat import THREAD_ID_PATTERN

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("/{thread_id}")
async def get_thread(
    runner: RunnerDep, thread_id: str = Path(pattern=THREAD_ID_PATTERN)
) -> dict[str, Any]:
    """Current checkpointed state: spec, estimate, lead, pending interrupt, recent messages."""
    return await runner.thread_view(thread_id)
