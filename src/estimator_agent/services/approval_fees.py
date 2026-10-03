"""Approval authority + fee lookup (GVMC / VUDA / panchayat). Placeholder schedule.

TODO(Ravikumar): supply the real fee schedule; move it to Mongo like rate cards.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCE = "placeholder"

# Lower-case substrings. Anything not matched falls back to panchayat.
_GVMC_AREAS = (
    "visakhapatnam",
    "vizag",
    "madhurawada",
    "mvp",
    "gajuwaka",
    "seethammadhara",
    "rushikonda",
    "dwaraka nagar",
    "pendurthi",
    "kommadi",
    "yendada",
    "akkayyapalem",
)
_VUDA_AREAS = ("anandapuram", "bheemunipatnam", "bheemili", "sabbavaram", "tagarapuvalasa")

_SCHEDULE = {
    # authority: (per sqft of built-up, fixed scrutiny fee)
    "GVMC": (45.0, 15_000.0),
    "VUDA": (35.0, 10_000.0),
    "Panchayat": (15.0, 5_000.0),
}


@dataclass(frozen=True)
class ApprovalFee:
    authority: str
    fee_inr: float
    source: str = SOURCE


def authority_for(location: str) -> str:
    loc = location.lower()
    # VUDA first: peri-urban names are more specific than "visakhapatnam"
    if any(a in loc for a in _VUDA_AREAS):
        return "VUDA"
    if any(a in loc for a in _GVMC_AREAS):
        return "GVMC"
    return "Panchayat"


_KNOWN_CITIES = {
    "visakhapatnam": ("visakhapatnam", "vizag", "vishakapatnam"),
    "vijayawada": ("vijayawada", "bezawada"),
}


def city_for(location: str, default: str) -> str:
    """Rate cards are per city. Map a free-text locality to a known city."""
    loc = location.lower()
    if any(a in loc for a in _GVMC_AREAS + _VUDA_AREAS):
        return "visakhapatnam"
    for city, aliases in _KNOWN_CITIES.items():
        if any(a in loc for a in aliases):
            return city
    return default


def approval_fee(location: str, built_up_area_sqft: float) -> ApprovalFee:
    authority = authority_for(location)
    per_sqft, fixed = _SCHEDULE[authority]
    return ApprovalFee(authority=authority, fee_inr=round(per_sqft * built_up_area_sqft + fixed))
