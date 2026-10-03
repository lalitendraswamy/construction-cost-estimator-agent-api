"""Supervisor: small LLM classifies intent (structured output); code picks the agent."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.common import recent_dialogue
from estimator_agent.agent.prompts.supervisor import SUPERVISOR_PROMPT
from estimator_agent.agent.routing import route_for_intent
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.core.llm import structured
from estimator_agent.domain import RouteDecision


async def supervisor_node(state: EstimatorState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
    emit_progress("routing")
    chain = SUPERVISOR_PROMPT | structured(runtime.context.models.chat("small"), RouteDecision)
    spec = state.get("spec")
    decision: RouteDecision = await chain.ainvoke(
        {
            "messages": recent_dialogue(state["messages"], 8),
            "last_agent": state.get("next_agent", "none"),
            "has_estimate": state.get("estimate") is not None,
            "spec": spec.model_dump_json(exclude_none=True) if spec else "{}",
        }
    )
    return {
        "intent": decision.intent,
        "route_reason": decision.reason,
        "next_agent": route_for_intent(decision.intent),
    }
