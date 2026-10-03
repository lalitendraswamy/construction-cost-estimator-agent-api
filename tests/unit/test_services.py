from __future__ import annotations

import pytest

from estimator_agent.domain import Language, ProjectSpec, ProjectType, QualityTier
from estimator_agent.services import approval_fees, pricing, quantities
from estimator_agent.services.formatting import format_inr, format_lakhs
from estimator_agent.services.language import detect_script_language
from estimator_agent.services.units import AreaUnit, parse_floor_notation, to_sqft
from tests.fakes import InMemoryRateRepository


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [(200, AreaUnit.SQYD, 1800), (100, AreaUnit.SQFT, 100), (1, AreaUnit.CENT, 435.6)],
)
def test_to_sqft(value: float, unit: AreaUnit, expected: float) -> None:
    assert to_sqft(value, unit) == expected


@pytest.mark.parametrize(("text", "floors"), [("G", 1), ("G+1", 2), ("g + 2", 3), ("two", None)])
def test_parse_floor_notation(text: str, floors: int | None) -> None:
    assert parse_floor_notation(text) == floors


@pytest.mark.parametrize(
    ("text", "lang"),
    [("నాకు ఇల్లు కట్టాలి", Language.TE), ("मुझे घर बनाना है", Language.HI), ("Naku illu kattali", None)],
)
def test_detect_script_language(text: str, lang: Language | None) -> None:
    assert detect_script_language(text) == lang


def test_missing_fields_drive_the_interview() -> None:
    assert ProjectSpec().missing_fields() == [
        "project_type",
        "location",
        "plot_area",
        "floors",
        "tier",
    ]
    s = ProjectSpec(project_type="new_house", location="MVP", built_up_area_sqft=1500, tier="basic")
    assert s.is_complete  # built-up area makes plot + floors unnecessary


def test_built_up_area_from_plot_and_floors() -> None:
    s = ProjectSpec(plot_area_sqft=1800, floors=2)
    assert quantities.built_up_area_sqft(s) == 2160


@pytest.mark.parametrize(
    ("location", "authority"),
    [("Madhurawada, Vizag", "GVMC"), ("Anandapuram", "VUDA"), ("Some village", "Panchayat")],
)
def test_approval_authority(location: str, authority: str) -> None:
    assert approval_fees.authority_for(location) == authority


async def test_price_estimate_formula() -> None:
    card = await InMemoryRateRepository.seeded().get("visakhapatnam", QualityTier.STANDARD)
    assert card is not None
    spec = ProjectSpec(
        project_type=ProjectType.NEW_HOUSE,
        location="MVP",
        built_up_area_sqft=1000,
        tier=QualityTier.STANDARD,
        extras=["lift"],
    )
    fee = approval_fees.approval_fee("MVP", 1000)
    est = pricing.price_estimate(
        spec=spec, card=card, area_sqft=1000, quantities=None, approval=fee
    )
    # 1000*2600 + (45*1000+15000) + lift 850000 = 3,510,000 ; +7% = 3,755,700
    assert est.total_inr == 3_756_000
    assert sum(li.amount_inr for li in est.line_items) == pytest.approx(2_600_000, abs=10)
    assert pricing.validate_estimate(est, card).ok


def test_indian_number_formatting() -> None:
    assert format_inr(6129000) == "₹61,29,000"
    assert format_lakhs(6129000) == "₹61.3 L"
    assert format_lakhs(12_000_000) == "₹1.20 Cr"
