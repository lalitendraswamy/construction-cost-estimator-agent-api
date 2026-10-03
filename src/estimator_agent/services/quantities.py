"""Material quantity take-off from built-up area (thumb rules, placeholder).

TODO(Ravikumar): replace per-sqft coefficients with the firm's own numbers.
"""

from __future__ import annotations

from estimator_agent.domain import MaterialQuantities, ProjectSpec, ProjectType

# Per sqft of built-up area, typical RCC framed residential structure.
_PER_SQFT = {
    "cement_bags": 0.40,
    "steel_kg": 4.0,
    "sand_cft": 1.8,
    "aggregate_cft": 1.35,
    "bricks": 8.0,
}

# Rough scaling by project type (renovation/interior use far less structure).
_TYPE_FACTOR = {
    ProjectType.NEW_HOUSE: 1.0,
    ProjectType.COMMERCIAL: 1.1,
    ProjectType.RENOVATION: 0.35,
    ProjectType.INTERIOR: 0.1,
    ProjectType.COMPOUND_WALL: 0.25,
}


DEFAULT_COVERAGE_RATIO = 0.6  # built-up per floor / plot area (setbacks eat the rest)


def built_up_area_sqft(spec: ProjectSpec, coverage_ratio: float = DEFAULT_COVERAGE_RATIO) -> float:
    """A in the PRD formula: explicit built-up area, else plot × coverage × floors."""
    if spec.built_up_area_sqft:
        return spec.built_up_area_sqft
    if spec.plot_area_sqft is None or spec.floors is None:
        raise ValueError("Need built_up_area_sqft or (plot_area_sqft and floors)")
    return round(spec.plot_area_sqft * coverage_ratio * spec.floors, 2)


def compute_quantities(area_sqft: float, project_type: ProjectType) -> MaterialQuantities:
    factor = _TYPE_FACTOR[project_type]
    return MaterialQuantities(**{k: round(v * area_sqft * factor, 1) for k, v in _PER_SQFT.items()})
