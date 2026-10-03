from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ApprovalDecision(BaseModel):
    action: Literal["approve", "edit"]
    total_inr: float | None = Field(None, gt=0, description="Required when action='edit'")
    note: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _edit_needs_total(self) -> ApprovalDecision:
        if self.action == "edit" and self.total_inr is None:
            raise ValueError("total_inr is required when action='edit'")
        return self
