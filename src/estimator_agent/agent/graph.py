"""The parent graph (PRD §4): supervisor + 4 agents + 2 interrupt points.

START -> input -> supervisor -> {intake | knowledge | contact | responder}
intake  -> ask_user (interrupt) -> intake            (loop until spec complete)
intake  -> estimator (compiled subgraph)
estimator -> request_approval -> await_approval (interrupt) -> responder   (> ₹1 Cr)
estimator -> responder
knowledge | contact -> responder -> END
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.contact import contact_node
from estimator_agent.agent.nodes.input import input_node
from estimator_agent.agent.nodes.intake import ask_user_node, intake_node
from estimator_agent.agent.nodes.knowledge import knowledge_node
from estimator_agent.agent.nodes.owner_approval import await_approval_node, request_approval_node
from estimator_agent.agent.nodes.responder import responder_node
from estimator_agent.agent.nodes.supervisor import supervisor_node
from estimator_agent.agent.routing import make_route_after_estimator, route_after_supervisor
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.subgraphs.estimator import build_estimator_subgraph

DEFAULT_APPROVAL_THRESHOLD_INR = 1_00_00_000  # ₹1 Cr

# [state, context, input, output] — lets type checkers verify `context=` and inputs.
EstimatorGraph = CompiledStateGraph[EstimatorState, AgentContext, EstimatorState, EstimatorState]


def build_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    *,
    approval_threshold_inr: float = DEFAULT_APPROVAL_THRESHOLD_INR,
) -> EstimatorGraph:
    builder = StateGraph(EstimatorState, context_schema=AgentContext)

    builder.add_node("input", input_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("intake", intake_node)  # routes itself via Command
    builder.add_node("ask_user", ask_user_node)  # interrupt #1
    builder.add_node("estimator", build_estimator_subgraph())  # compiled subgraph as a node
    builder.add_node("request_approval", request_approval_node)
    builder.add_node("await_approval", await_approval_node)  # interrupt #2
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("contact", contact_node)  # interrupts inside its tools
    builder.add_node("responder", responder_node)

    builder.add_edge(START, "input")
    builder.add_edge("input", "supervisor")
    builder.add_conditional_edges(
        "supervisor", route_after_supervisor, ["intake", "knowledge", "contact", "responder"]
    )
    builder.add_edge("ask_user", "intake")
    builder.add_conditional_edges(
        "estimator",
        make_route_after_estimator(approval_threshold_inr),
        ["request_approval", "responder"],
    )
    builder.add_edge("request_approval", "await_approval")
    builder.add_edge("await_approval", "responder")
    builder.add_edge("knowledge", "responder")
    builder.add_edge("contact", "responder")
    builder.add_edge("responder", END)

    return builder.compile(checkpointer=checkpointer, name="construction_estimator")
