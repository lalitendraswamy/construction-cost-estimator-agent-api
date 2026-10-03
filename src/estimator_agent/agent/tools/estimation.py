"""Deterministic estimation tools: compute_quantities, get_rates, approval_fee_lookup,
price_estimate. Thin wrappers over services/*; the wrappers give them schemas, make them
show up as tool runs in LangSmith traces, and let an LLM call them if you ever want it to."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from estimator_agent.core.exceptions import RatesUnavailableError
from estimator_agent.db.repositories import RateRepository
from estimator_agent.domain import (
    MaterialQuantities,
    ProjectSpec,
    ProjectType,
    QualityTier,
    RateCard,
)
from estimator_agent.services import approval_fees, pricing, quantities
from estimator_agent.services.approval_fees import ApprovalFee


class ComputeQuantitiesInput(BaseModel):
    built_up_area_sqft: float = Field(gt=0)
    project_type: ProjectType


@tool("compute_quantities", args_schema=ComputeQuantitiesInput)
def compute_quantities(built_up_area_sqft: float, project_type: ProjectType) -> dict[str, Any]:
    """Material quantities (cement bags, steel kg, sand/aggregate cft, bricks) for an area."""
    return quantities.compute_quantities(built_up_area_sqft, project_type).model_dump()


class GetRatesInput(BaseModel):
    city: str = Field(description="Lower-case city, e.g. 'visakhapatnam'")
    tier: QualityTier


def make_get_rates(repo: RateRepository) -> BaseTool:
    @tool("get_rates", args_schema=GetRatesInput)
    async def get_rates(city: str, tier: QualityTier) -> dict[str, Any]:
        """Per-sqft rate card for a city and quality tier from the rates table."""
        card = await repo.get(city.lower(), tier)
        if card is None:
            raise RatesUnavailableError(f"No rate card for {city}/{tier}")
        return card.model_dump(mode="json")

    return get_rates


class ApprovalFeeInput(BaseModel):
    location: str
    built_up_area_sqft: float = Field(gt=0)


@tool("approval_fee_lookup", args_schema=ApprovalFeeInput)
def approval_fee_lookup(location: str, built_up_area_sqft: float) -> dict[str, Any]:
    """Approval authority (GVMC / VUDA / Panchayat) and estimated fee for a location."""
    fee = approval_fees.approval_fee(location, built_up_area_sqft)
    return {"authority": fee.authority, "fee_inr": fee.fee_inr, "source": fee.source}


class PriceEstimateInput(BaseModel):
    spec: ProjectSpec
    rate_card: RateCard
    built_up_area_sqft: float = Field(gt=0)
    quantities: MaterialQuantities | None = None
    approval_authority: str
    approval_fee_inr: float = Field(ge=0)


@tool("price_estimate", args_schema=PriceEstimateInput)
def price_estimate(
    spec: ProjectSpec | dict[str, Any],
    rate_card: RateCard | dict[str, Any],
    built_up_area_sqft: float,
    approval_authority: str,
    approval_fee_inr: float,
    quantities: MaterialQuantities | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Line items, contingency, total and low-high range (±8%)."""
    est = pricing.price_estimate(
        spec=ProjectSpec.model_validate(spec),
        card=RateCard.model_validate(rate_card),
        area_sqft=built_up_area_sqft,
        quantities=MaterialQuantities.model_validate(quantities) if quantities else None,
        approval=ApprovalFee(authority=approval_authority, fee_inr=approval_fee_inr),
    )
    return est.model_dump(mode="json")
