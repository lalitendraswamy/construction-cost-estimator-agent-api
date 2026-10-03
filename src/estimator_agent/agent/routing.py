"""Pure routing functions used by conditional edges. No LLM, no I/O: unit-test these."""

from __future__ import annotations

from typing import Literal

from estimator_agent.agent.state import EstimatorState
from estimator_agent.domain import Intent

SupervisorRoute = Literal["intake", "knowledge", "contact", "responder"]


def route_for_intent(intent: Intent) -> SupervisorRoute:
    """Every estimate/modify request goes through Intake first. Intake is the ONLY node
    with an edge into the Estimator, and it only takes that edge when
    ProjectSpec.missing_fields() is empty: 'never estimate on guesses' enforced in code."""
    match intent:
        case Intent.ESTIMATE | Intent.MODIFY:
            return "intake"
        case Intent.QUESTION:
            return "knowledge"
        case Intent.CONTACT:
            return "contact"
        case _:
            return "responder"  # chit_chat / off_topic: Responder replies or refuses politely


def route_after_supervisor(state: EstimatorState) -> SupervisorRoute:
    return state["next_agent"]  # type: ignore[return-value]


def make_route_after_estimator(threshold_inr: float):  # type: ignore[no-untyped-def]
    def route_after_estimator(state: EstimatorState) -> Literal["request_approval", "responder"]:
        estimate = state.get("estimate")
        if estimate is not None and estimate.total_inr > threshold_inr:
            return "request_approval"
        return "responder"

    return route_after_estimator
