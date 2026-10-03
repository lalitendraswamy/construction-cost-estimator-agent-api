"""The estimate formula (PRD §9):

    Total = A × R + F_approvals + C_extras + k × subtotal
    range = Total ± 8%

Line items split A × R using the share percentages on the RateCard.
"""

from __future__ import annotations

from dataclasses import dataclass

from estimator_agent.domain import (
    Estimate,
    LineItem,
    MaterialQuantities,
    ProjectSpec,
    RateCard,
)
from estimator_agent.services.approval_fees import ApprovalFee

RANGE_PCT = 0.08

LABELS = {
    "cement": "Cement",
    "steel": "Steel (TMT)",
    "sand": "Sand",
    "aggregate": "Aggregate",
    "bricks": "Bricks / blocks",
    "labour": "Labour",
    "finishing": "Finishing (flooring, paint, doors)",
    "electrical": "Electrical",
    "plumbing": "Plumbing & sanitary",
}

# share code -> (quantity field on MaterialQuantities, unit)
_QTY = {
    "cement": ("cement_bags", "bags"),
    "steel": ("steel_kg", "kg"),
    "sand": ("sand_cft", "cft"),
    "aggregate": ("aggregate_cft", "cft"),
    "bricks": ("bricks", "nos"),
}


def _round_to(x: float, step: int) -> float:
    return float(round(x / step) * step)


def price_estimate(
    *,
    spec: ProjectSpec,
    card: RateCard,
    area_sqft: float,
    quantities: MaterialQuantities | None,
    approval: ApprovalFee,
) -> Estimate:
    construction = area_sqft * card.base_rate_per_sqft

    line_items: list[LineItem] = []
    for code, share in card.shares.items():
        qty_field, unit = _QTY.get(code, (None, None))
        line_items.append(
            LineItem(
                code=code,
                label=LABELS.get(code, code.title()),
                amount_inr=round(construction * share),
                quantity=getattr(quantities, qty_field) if quantities and qty_field else None,
                unit=unit,
            )
        )

    extras = sum(card.extras_inr.get(e.value, 0.0) for e in spec.extras)
    subtotal = construction + approval.fee_inr + extras
    contingency = subtotal * card.contingency_pct
    total = subtotal + contingency

    return Estimate(
        city=card.city,
        tier=card.tier,
        built_up_area_sqft=area_sqft,
        line_items=line_items,
        construction_cost_inr=round(construction),
        approval_fees_inr=approval.fee_inr,
        extras_inr=round(extras),
        contingency_inr=round(contingency),
        total_inr=_round_to(total, 1000),
        range_low_inr=_round_to(total * (1 - RANGE_PCT), 1000),
        range_high_inr=_round_to(total * (1 + RANGE_PCT), 1000),
        cost_per_sqft_inr=round(construction / area_sqft),
        quantities=quantities,
        rates_source=card.source,
        approval_authority=approval.authority,
    )


def apply_owner_override(estimate: Estimate, total_inr: float) -> Estimate:
    """Ravikumar edited the total in the approval gate: keep the breakdown, move the range."""
    return estimate.model_copy(
        update={
            "total_inr": _round_to(total_inr, 1000),
            "range_low_inr": _round_to(total_inr * (1 - RANGE_PCT), 1000),
            "range_high_inr": _round_to(total_inr * (1 + RANGE_PCT), 1000),
        }
    )


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str | None = None


def validate_estimate(estimate: Estimate, card: RateCard) -> ValidationResult:
    """Sanity check: cost/sqft must sit inside the tier's band. Catches bad rate-card edits."""
    cps = estimate.cost_per_sqft_inr
    if not card.band_min_per_sqft <= cps <= card.band_max_per_sqft:
        return ValidationResult(
            ok=False,
            reason=(
                f"cost/sqft ₹{cps:,.0f} outside {card.tier} band "
                f"₹{card.band_min_per_sqft:,.0f}–₹{card.band_max_per_sqft:,.0f}"
            ),
        )
    return ValidationResult(ok=True)
