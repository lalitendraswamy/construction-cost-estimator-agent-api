from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.subgraphs.estimator.nodes import (
    compute_quantities_node,
    explain_node,
    fetch_rates_node,
    is_transient,
    price_line_items_node,
    route_after_validate,
    validate_node,
)
from estimator_agent.agent.subgraphs.estimator.state import (
    EstimatorInput,
    EstimatorOutput,
    EstimatorSubState,
)


def build_estimator_subgraph() -> CompiledStateGraph[
    EstimatorSubState, AgentContext, EstimatorInput, EstimatorOutput
]:
    builder = StateGraph(
        EstimatorSubState,
        context_schema=AgentContext,
        input_schema=EstimatorInput,
        output_schema=EstimatorOutput,
    )
    builder.add_node("compute_quantities", compute_quantities_node)
    builder.add_node(
        "fetch_rates",
        fetch_rates_node,
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.5, retry_on=is_transient),
    )
    builder.add_node("price_line_items", price_line_items_node)
    builder.add_node("validate", validate_node)
    builder.add_node("explain", explain_node)

    builder.add_edge(START, "compute_quantities")
    builder.add_edge("compute_quantities", "fetch_rates")
    builder.add_edge("fetch_rates", "price_line_items")
    builder.add_edge("price_line_items", "validate")
    builder.add_conditional_edges("validate", route_after_validate, ["fetch_rates", "explain"])
    builder.add_edge("explain", END)

    # No checkpointer here: a subgraph added as a node inherits the parent's.
    return builder.compile(name="estimator")
