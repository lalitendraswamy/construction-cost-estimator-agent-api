"""Owner approval gate (PRD F7) for estimates over the threshold (₹1 Cr).

Split in two nodes on purpose:
  request_approval: side effects (persist + notify owner). Runs once.
  await_approval:   only interrupt(). Re-runs on resume, so it must stay side-effect free.
The admin endpoint resumes the thread with Command(resume={"action": "approve" | "edit", ...}).
"""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.common import current_thread_id
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.domain import ApprovalStatus
from estimator_agent.services.formatting import format_lakhs
from estimator_agent.services.pricing import apply_owner_override


async def request_approval_node(
    state: EstimatorState, runtime: Runtime[AgentContext]
) -> dict[str, Any]:
    ctx = runtime.context
    estimate = state["estimate"]
    assert estimate is not None
    thread_id = current_thread_id()
    created = await ctx.approvals.upsert_pending(thread_id, estimate)  # idempotent
    if created:
        await ctx.notifier.send_email(
            ctx.settings.owner_email,
            f"Approval needed: {format_lakhs(estimate.total_inr)} estimate",
            f"Thread {thread_id} is waiting for your approval.\n"
            f"Total {format_lakhs(estimate.total_inr)}, tier {estimate.tier}, "
            f"{estimate.built_up_area_sqft:.0f} sqft in {estimate.city}.\n"
            f"Approve via POST /api/v1/admin/approve/{thread_id}",
        )
    return {"approval": ApprovalStatus.PENDING}


def await_approval_node(state: EstimatorState) -> dict[str, Any]:
    emit_progress("awaiting_owner")
    estimate = state["estimate"]
    assert estimate is not None
    decision: dict[str, Any] = interrupt(
        {"type": "owner_approval", "estimate": estimate.model_dump(mode="json")}
    )
    if decision.get("action") == "edit" and decision.get("total_inr"):
        return {
            "estimate": apply_owner_override(estimate, float(decision["total_inr"])),
            "approval": ApprovalStatus.EDITED,
        }
    return {"approval": ApprovalStatus.APPROVED}
