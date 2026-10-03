"""RateCard: one document per (city, tier) in the `rates` collection.

Ravikumar edits these via PUT /admin/rates (U9) so prices change without a deploy.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from estimator_agent.domain.enums import QualityTier


class RateCard(BaseModel):
    city: str
    tier: QualityTier
    base_rate_per_sqft: float = Field(gt=0, description="R in the PRD formula")
    band_min_per_sqft: float = Field(gt=0, description="Validator lower bound")
    band_max_per_sqft: float = Field(gt=0, description="Validator upper bound")
    shares: dict[str, float] = Field(description="Line-item split of A×R; must sum to 1.0")
    extras_inr: dict[str, float] = Field(default_factory=dict, description="Fixed-price add-ons")
    contingency_pct: float = Field(0.07, ge=0.05, le=0.10)
    source: str = "placeholder"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _check(self) -> RateCard:
        total = sum(self.shares.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"shares must sum to 1.0 (got {total:.3f})")
        if self.band_min_per_sqft >= self.band_max_per_sqft:
            raise ValueError("band_min_per_sqft must be < band_max_per_sqft")
        return self
