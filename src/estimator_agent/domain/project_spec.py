"""ProjectSpec: everything we must know before pricing (PRD F2 checklist)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from estimator_agent.domain.enums import Extra, ProjectType, QualityTier


class ProjectSpec(BaseModel):
    project_type: ProjectType | None = None
    location: str | None = Field(None, description="Area / city, e.g. 'Madhurawada, Visakhapatnam'")
    plot_area_sqft: float | None = Field(None, gt=0)
    built_up_area_sqft: float | None = Field(None, gt=0)
    floors: int | None = Field(None, ge=1, le=10, description="Total floors incl. ground. G+1 = 2")
    tier: QualityTier | None = None
    # optional
    timeline_months: int | None = Field(None, ge=1)
    budget_ceiling_inr: float | None = Field(None, gt=0)
    extras: list[Extra] = Field(default_factory=list)

    def missing_fields(self) -> list[str]:
        """Deterministic completeness check. The 'ask before estimating' guarantee
        lives HERE (code), not in a prompt."""
        missing: list[str] = []
        if self.project_type is None:
            missing.append("project_type")
        if not self.location:
            missing.append("location")
        if self.built_up_area_sqft is None:
            if self.plot_area_sqft is None:
                missing.append("plot_area")
            if self.floors is None:
                missing.append("floors")
        if self.tier is None:
            missing.append("tier")
        return missing

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields()
