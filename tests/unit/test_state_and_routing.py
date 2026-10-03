from __future__ import annotations

import pytest

from estimator_agent.agent.routing import make_route_after_estimator, route_for_intent
from estimator_agent.agent.state import merge_spec
from estimator_agent.agent.tools.contact import is_affirmative, normalise_phone
from estimator_agent.domain import Extra, Intent, ProjectSpec, QualityTier
from estimator_agent.domain.estimate import Estimate


def test_merge_spec_only_overwrites_fields_that_were_set() -> None:
    current = ProjectSpec(location="MVP", floors=2, tier=QualityTier.STANDARD, extras=[Extra.SUMP])
    merged = merge_spec(current, {"tier": QualityTier.PREMIUM, "extras": [Extra.LIFT]})
    assert merged.tier == QualityTier.PREMIUM
    assert merged.location == "MVP"
    assert merged.floors == 2
    assert set(merged.extras) == {Extra.SUMP, Extra.LIFT}


def test_merge_spec_ignores_none_patch() -> None:
    current = ProjectSpec(location="MVP")
    assert merge_spec(current, None) is current


@pytest.mark.parametrize(
    ("intent", "node"),
    [
        (Intent.ESTIMATE, "intake"),
        (Intent.MODIFY, "intake"),  # what-if also re-extracts before pricing
        (Intent.QUESTION, "knowledge"),
        (Intent.CONTACT, "contact"),
        (Intent.CHIT_CHAT, "responder"),
        (Intent.OFF_TOPIC, "responder"),
    ],
)
def test_supervisor_routing_table(intent: Intent, node: str) -> None:
    assert route_for_intent(intent) == node


def _estimate(total: float) -> Estimate:
    return Estimate(
        city="visakhapatnam",
        tier=QualityTier.BASIC,
        built_up_area_sqft=1,
        line_items=[],
        construction_cost_inr=total,
        approval_fees_inr=0,
        extras_inr=0,
        contingency_inr=0,
        total_inr=total,
        range_low_inr=total,
        range_high_inr=total,
        cost_per_sqft_inr=1,
    )


def test_owner_approval_threshold() -> None:
    route = make_route_after_estimator(1_00_00_000)
    assert route({"estimate": _estimate(1_00_00_001)}) == "request_approval"
    assert route({"estimate": _estimate(99_00_000)}) == "responder"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("98765 43210", "919876543210"), ("+91-9876543210", "919876543210"), ("12345", None)],
)
def test_normalise_phone(raw: str, expected: str | None) -> None:
    assert normalise_phone(raw) == expected


@pytest.mark.parametrize(
    ("answer", "ok"),
    [
        ("yes", True),
        ("Avunu, cheyandi", True),
        ("అవును", True),
        ("no", False),
        ({"confirmed": True}, True),
        (False, False),
    ],
)
def test_is_affirmative(answer: object, ok: bool) -> None:
    assert is_affirmative(answer) is ok
