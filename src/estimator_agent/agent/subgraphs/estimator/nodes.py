"""Estimator subgraph nodes (PRD §4): compute_quantities -> fetch_rates -> price_line_items
-> validate (retry fetch_rates once) -> explain. Only `explain` uses an LLM."""

from __future__ import annotations

import re
from typing import Any, Literal

from langchain_core.output_parsers import StrOutputParser
from langgraph.runtime import Runtime
from pymongo.errors import PyMongoError

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.prompts.explain import EXPLAIN_PROMPT
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.agent.subgraphs.estimator.state import EstimatorSubState
from estimator_agent.agent.tools.estimation import (
    approval_fee_lookup,
    compute_quantities,
    make_get_rates,
    price_estimate,
)
from estimator_agent.core.exceptions import RatesUnavailableError, SpecIncompleteError
from estimator_agent.core.logging import get_logger
from estimator_agent.domain import Estimate, MaterialQuantities, RateCard
from estimator_agent.services.approval_fees import city_for
from estimator_agent.services.pricing import validate_estimate
from estimator_agent.services.quantities import built_up_area_sqft

log = get_logger(__name__)
_DIGIT = re.compile(r"\d")


def is_transient(exc: Exception) -> bool:
    """RetryPolicy.retry_on: retry DB/network blips, never business errors."""
    return isinstance(exc, PyMongoError | ConnectionError | TimeoutError)


async def compute_quantities_node(state: EstimatorSubState) -> dict[str, Any]:
    spec = state["spec"]
    if not spec.is_complete:  # defence in depth: Intake should never let this happen
        raise SpecIncompleteError(f"missing: {spec.missing_fields()}")
    emit_progress("computing_quantities")
    area = built_up_area_sqft(spec)
    qty = await compute_quantities.ainvoke(
        {"built_up_area_sqft": area, "project_type": spec.project_type}
    )
    previous = state.get("estimate")
    return {
        "area_sqft": area,
        "quantities": MaterialQuantities.model_validate(qty),
        "attempts": 0,
        "validation_error": None,
        "variants": [previous] if previous else [],  # archive old estimate (F8 what-if)
    }


async def fetch_rates_node(
    state: EstimatorSubState, runtime: Runtime[AgentContext]
) -> dict[str, Any]:
    emit_progress("fetching_rates")
    ctx = runtime.context
    spec = state["spec"]
    default_city = ctx.settings.default_city
    # On a validation retry, fall back to the default city's (reviewed) rate card.
    city = (
        default_city
        if state.get("attempts", 0) > 0
        else city_for(spec.location or "", default_city)
    )
    get_rates = make_get_rates(ctx.rates)
    try:
        card = await get_rates.ainvoke({"city": city, "tier": spec.tier})
    except RatesUnavailableError:
        if city == default_city:
            raise
        log.warning("rates_fallback_default_city", city=city)
        city = default_city
        card = await get_rates.ainvoke({"city": city, "tier": spec.tier})
    return {"rate_card": RateCard.model_validate(card), "city": city}


async def price_line_items_node(state: EstimatorSubState) -> dict[str, Any]:
    emit_progress("pricing")
    spec, area, card = state["spec"], state["area_sqft"], state["rate_card"]
    fee = await approval_fee_lookup.ainvoke({"location": spec.location, "built_up_area_sqft": area})
    est = await price_estimate.ainvoke(
        {
            "spec": spec.model_dump(),
            "rate_card": card.model_dump(),
            "built_up_area_sqft": area,
            "quantities": state["quantities"].model_dump(),
            "approval_authority": fee["authority"],
            "approval_fee_inr": fee["fee_inr"],
        }
    )
    return {"estimate": Estimate.model_validate(est)}


def validate_node(state: EstimatorSubState) -> dict[str, Any]:
    emit_progress("validating")
    estimate, card = state["estimate"], state["rate_card"]
    assert estimate is not None
    result = validate_estimate(estimate, card)
    if result.ok:
        return {"validation_error": None}
    attempts = state.get("attempts", 0)
    if attempts < 1:
        log.warning("estimate_validation_retry", reason=result.reason)
        return {"validation_error": result.reason, "attempts": attempts + 1}
    log.error("estimate_validation_flagged", reason=result.reason)
    return {
        "validation_error": result.reason,
        "estimate": estimate.model_copy(update={"validation_flag": result.reason}),
    }


def route_after_validate(state: EstimatorSubState) -> Literal["fetch_rates", "explain"]:
    estimate = state["estimate"]
    if state.get("validation_error") and estimate is not None and not estimate.validation_flag:
        return "fetch_rates"  # the cycle: one retry with the default rate card
    return "explain"


async def explain_node(state: EstimatorSubState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
    emit_progress("explaining")
    estimate = state["estimate"]
    assert estimate is not None
    chain = EXPLAIN_PROMPT | runtime.context.models.chat("strong") | StrOutputParser()
    summary: str | None
    try:
        summary = await chain.ainvoke(
            {
                "estimate_json": estimate.model_dump_json(
                    exclude={"summary", "disclaimer", "quantities"}
                )
            }
        )
    except Exception:  # the explanation is nice-to-have; never fail the estimate over it
        log.exception("explain_failed")
        summary = None
    if summary and _DIGIT.search(summary):
        log.warning("explain_contained_numbers_dropped")  # guardrail: LLM may not add numbers
        summary = None
    return {"estimate": estimate.model_copy(update={"summary": summary})}
