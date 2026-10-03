"""Owner-only endpoints (X-Admin-Key): approvals (U7/F7) and rate cards (U9)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path

from estimator_agent.api.deps import ApprovalsDep, RatesDep, RunnerDep, require_admin
from estimator_agent.domain import RateCard
from estimator_agent.schemas.admin import ApprovalDecision
from estimator_agent.schemas.chat import THREAD_ID_PATTERN

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/pending")
async def list_pending(approvals: ApprovalsDep) -> list[dict[str, Any]]:
    return await approvals.list_pending()


@router.post("/approve/{thread_id}")
async def approve(
    decision: ApprovalDecision,
    runner: RunnerDep,
    thread_id: str = Path(pattern=THREAD_ID_PATTERN),
) -> dict[str, Any]:
    """Resume the paused graph with Command(resume=decision). Returns the thread state,
    including the reply the user will now see."""
    return await runner.resume_owner_approval(thread_id, decision.model_dump(exclude_none=True))


@router.get("/rates")
async def list_rates(rates: RatesDep) -> list[RateCard]:
    return await rates.list_all()


@router.put("/rates")
async def upsert_rate(card: RateCard, rates: RatesDep) -> RateCard:
    """Create/replace the rate card for (city, tier). Validation (shares sum to 1, band
    sanity) lives on the RateCard model."""
    await rates.upsert(card)
    return card
