"""Unit normalisation. Plots in AP are usually quoted in square yards (gajalu)."""

from __future__ import annotations

import re
from enum import StrEnum


class AreaUnit(StrEnum):
    SQFT = "sqft"
    SQYD = "sqyd"
    SQM = "sqm"
    ACRE = "acre"
    CENT = "cent"  # common in AP: 1 cent = 435.6 sqft


_TO_SQFT: dict[AreaUnit, float] = {
    AreaUnit.SQFT: 1.0,
    AreaUnit.SQYD: 9.0,
    AreaUnit.SQM: 10.7639,
    AreaUnit.ACRE: 43_560.0,
    AreaUnit.CENT: 435.6,
}


def to_sqft(value: float, unit: AreaUnit | str) -> float:
    return round(value * _TO_SQFT[AreaUnit(unit)], 2)


_FLOOR_RE = re.compile(r"^\s*g\s*(?:\+\s*(\d+))?\s*$", re.IGNORECASE)


def parse_floor_notation(text: str) -> int | None:
    """'G' -> 1, 'G+1' -> 2, 'g + 2' -> 3. Returns None if it is not floor notation."""
    m = _FLOOR_RE.match(text)
    if not m:
        return None
    return 1 + int(m.group(1) or 0)
