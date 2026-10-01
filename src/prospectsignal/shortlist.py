"""Shortlist scoring: an optional, transparent fit score with weights the user sets and can see.

The score is a weighted share of four yes/no-style checks, scaled to 0-100. It is a sorting aid for a human, not a
prediction of anything, and every component is shown next to the total.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import nace
from .icp import ICP
from .schema import EMPLOYEE_BANDS, band_range


@dataclass(frozen=True)
class FitWeights:
    size: float = 1.0
    region: float = 1.0
    nace: float = 1.0
    age: float = 1.0

    def total(self) -> float:
        return self.size + self.region + self.nace + self.age


@dataclass(frozen=True)
class FitTargets:
    bands: tuple[str, ...] = ()
    fylker: tuple[str, ...] = ()
    nace_prefixes: tuple[str, ...] = ()
    age_min_years: int = 3
    age_max_years: int = 30

    @classmethod
    def from_icp(cls, icp: ICP) -> "FitTargets":
        low = icp.employees_min if icp.employees_min is not None else 0
        high = icp.employees_max
        bands = []
        for band in EMPLOYEE_BANDS:
            band_low, band_high = band_range(band)
            if (high is None or band_low <= high) and (band_high is None or band_high >= low):
                bands.append(band)
        return cls(bands=tuple(bands), fylker=tuple(icp.fylker), nace_prefixes=tuple(icp.nace_prefixes))


def _age_years(founded: object, today: date) -> float | None:
    if founded is None or (isinstance(founded, float) and pd.isna(founded)) or pd.isna(founded):
        return None
    founded_date = pd.Timestamp(founded).date()
    return (today - founded_date).days / 365.25


def score_frame(
    frame: pd.DataFrame, targets: FitTargets, weights: FitWeights, today: date | None = None
) -> pd.DataFrame:
    """Add fit_size, fit_region, fit_nace, fit_age (each 0, 0.5 or 1) and fit_score (0-100)."""
    today = today or date.today()
    result = frame.copy()
    if result.empty:
        for column in ("fit_size", "fit_region", "fit_nace", "fit_age", "fit_score"):
            result[column] = pd.Series(dtype=float)
        return result
    result["fit_size"] = result["employee_band"].map(lambda band: 1.0 if band in targets.bands else 0.0)
    result["fit_region"] = result["fylke_nr"].map(lambda fylke: 1.0 if fylke in targets.fylker else 0.0)

    def nace_fit(row: pd.Series) -> float:
        if nace.matches(row.get("nace1"), targets.nace_prefixes):
            return 1.0
        if any(
            nace.matches(row.get(column), targets.nace_prefixes) for column in ("nace2", "nace3") if row.get(column)
        ):
            return 0.5  # only a secondary code matches
        return 0.0

    result["fit_nace"] = result.apply(nace_fit, axis=1) if targets.nace_prefixes else 1.0

    def age_fit(founded: object) -> float:
        years = _age_years(founded, today)
        if years is None:
            return 0.0
        return 1.0 if targets.age_min_years <= years <= targets.age_max_years else 0.0

    result["fit_age"] = result["founded"].map(age_fit)
    if not targets.fylker:
        result["fit_region"] = 1.0
    if not targets.bands:
        result["fit_size"] = 1.0
    total = weights.total()
    if total <= 0:
        result["fit_score"] = 0.0
    else:
        result["fit_score"] = (
            100
            * (
                weights.size * result["fit_size"]
                + weights.region * result["fit_region"]
                + weights.nace * result["fit_nace"]
                + weights.age * result["fit_age"]
            )
            / total
        ).round(0)
    return result
