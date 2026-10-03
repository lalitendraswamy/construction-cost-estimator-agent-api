from __future__ import annotations

from pydantic import BaseModel, Field

from estimator_agent.domain.enums import QualityTier

DISCLAIMER = "Indicative estimate, final quote after site visit by Sadhguru Associates."


class MaterialQuantities(BaseModel):
    cement_bags: float
    steel_kg: float
    sand_cft: float
    aggregate_cft: float
    bricks: float


class LineItem(BaseModel):
    code: str = Field(description="Stable machine key, e.g. 'steel'")
    label: str
    amount_inr: float
    quantity: float | None = None
    unit: str | None = None


class Estimate(BaseModel):
    city: str
    tier: QualityTier
    built_up_area_sqft: float
    line_items: list[LineItem]
    construction_cost_inr: float
    approval_fees_inr: float
    extras_inr: float
    contingency_inr: float
    total_inr: float
    range_low_inr: float
    range_high_inr: float
    cost_per_sqft_inr: float
    quantities: MaterialQuantities | None = None
    rates_source: str = "placeholder"
    approval_authority: str | None = None
    validation_flag: str | None = Field(None, description="Set when the sanity check failed")
    summary: str | None = Field(None, description="LLM plain-language explanation (no new numbers)")
    disclaimer: str = DISCLAIMER

    def top_line_items(self, n: int = 5) -> list[LineItem]:
        return sorted(self.line_items, key=lambda li: li.amount_inr, reverse=True)[:n]
