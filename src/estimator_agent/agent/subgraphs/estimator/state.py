"""Estimator subgraph state.

input_schema / output_schema control what crosses the parent<->subgraph boundary:
  IN : spec, language, estimate (the previous one, to be kept as a variant)
  OUT: estimate (new), variants (ONLY the newly archived one)
Private keys (rate_card, quantities, attempts…) never leak into the parent state.

Why output_schema matters: parent `variants` uses operator.add. If the subgraph returned
the full list, the parent would append it to itself and duplicate history.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from estimator_agent.domain import Estimate, Language, MaterialQuantities, ProjectSpec, RateCard


class EstimatorInput(TypedDict, total=False):
    spec: ProjectSpec
    language: Language
    estimate: Estimate | None


class EstimatorOutput(TypedDict, total=False):
    estimate: Estimate
    variants: list[Estimate]


class EstimatorSubState(TypedDict, total=False):
    # shared with parent
    spec: ProjectSpec
    language: Language
    estimate: Estimate | None
    variants: Annotated[list[Estimate], operator.add]
    # private
    area_sqft: float
    quantities: MaterialQuantities
    city: str
    rate_card: RateCard
    attempts: int
    validation_error: str | None
