from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .constraints import assert_constraints
from .data import RURAL_ORDER
from .model import Theta, make_design, mu


@dataclass(frozen=True)
class CalibrationTruth:
    beta_by_term: dict[str, float]
    state_effect_by_fips: dict[str, float]
    year_effect_by_year: dict[str, float]
    kappa: float
    seed: int

    def to_dict(self) -> dict[str, object]:
        return {
            "beta_by_term": self.beta_by_term,
            "state_effect_by_fips": self.state_effect_by_fips,
            "year_effect_by_year": self.year_effect_by_year,
            "kappa": self.kappa,
            "seed": self.seed,
        }


def select_representative_panel(
    frame: pd.DataFrame,
    *,
    counties_per_rurality: int = 16,
) -> pd.DataFrame:
    """Select a deterministic population-spanning county panel by rurality."""

    required = {
        "county_fips",
        "year",
        "population",
        "primary_rurality",
        "svi_quartile",
        "state_fips",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Model frame is missing required calibration columns: {sorted(missing)}")

    county = (
        frame.groupby("county_fips", as_index=False)
        .agg(
            population=("population", "sum"),
            primary_rurality=("primary_rurality", "first"),
            state_fips=("state_fips", "first"),
        )
        .sort_values(["primary_rurality", "population", "county_fips"])
    )
    selected: list[str] = []
    for rurality in RURAL_ORDER:
        group = county[county["primary_rurality"].eq(rurality)].reset_index(drop=True)
        if group.empty:
            raise ValueError(f"No counties available for rurality category {rurality!r}.")
        n = min(int(counties_per_rurality), len(group))
        positions = np.unique(np.rint(np.linspace(0, len(group) - 1, n)).astype(int))
        selected.extend(group.loc[positions, "county_fips"].astype(str).tolist())

    out = frame[frame["county_fips"].astype(str).isin(selected)].copy()
    out = out.sort_values(["state_fips", "county_fips", "year"]).reset_index(drop=True)
    expected_years = frame["year"].astype(str).nunique()
    if len(out) != out["county_fips"].nunique() * expected_years:
        raise ValueError("Representative calibration panel is not a complete county-year panel.")
    out.attrs["calibration_selection"] = {
        "counties_per_rurality": int(counties_per_rurality),
        "counties": int(out["county_fips"].nunique()),
        "county_year_rows": int(len(out)),
    }
    return out


def make_calibration_truth(
    frame: pd.DataFrame,
    *,
    seed: int = 20260811,
    kappa: float = 10.0,
) -> tuple[Theta, CalibrationTruth]:
    """Construct a reproducible truth with realistic rurality/SVI magnitudes."""

    design = make_design(frame)
    beta = np.zeros(len(design.columns), dtype=float)
    intended = {
        "Intercept": float(np.log(3.4 / 100000.0)),
        "primary_rurality_metro_other": float(np.log(1.12)),
        "primary_rurality_nonmetro_adjacent": float(np.log(1.27)),
        "primary_rurality_nonmetro_nonadjacent": float(np.log(1.23)),
        "svi_quartile_Q2": float(np.log(1.10)),
        "svi_quartile_Q3": float(np.log(1.25)),
        "svi_quartile_Q4_highest": float(np.log(1.43)),
        "z_pct_age65": 0.10,
        "z_pct_male": -0.06,
    }
    for index, term in enumerate(design.columns):
        beta[index] = intended.get(term, 0.0)

    rng = np.random.default_rng(seed)
    state_effect = rng.normal(0.0, 0.15, size=len(design.states))
    state_effect -= state_effect.mean()
    year_template = np.linspace(-0.15, 0.15, len(design.years))
    year_effect = year_template - year_template.mean()

    theta = Theta(
        beta=beta,
        state_effect=state_effect,
        year_effect=year_effect,
        log_sigma_state=float(np.log(0.15)),
        log_sigma_year=float(np.log(max(float(np.std(year_effect, ddof=1)), 1e-6))),
        log_kappa=float(np.log(kappa)),
    )
    truth = CalibrationTruth(
        beta_by_term={term: float(value) for term, value in zip(design.columns, beta)},
        state_effect_by_fips={
            state: float(value) for state, value in zip(design.states, state_effect)
        },
        year_effect_by_year={
            year: float(value) for year, value in zip(design.years, year_effect)
        },
        kappa=float(kappa),
        seed=int(seed),
    )
    return theta, truth


def simulate_complete_counts(
    frame: pd.DataFrame,
    theta: Theta,
    *,
    seed: int = 20260812,
) -> np.ndarray:
    """Generate complete NB2 county-year counts under a known truth."""

    design = make_design(frame)
    expected = mu(theta, design)
    kappa = float(np.exp(theta.log_kappa))
    probability = kappa / (kappa + expected)
    rng = np.random.default_rng(seed)
    counts = rng.negative_binomial(kappa, probability).astype(int)
    if np.any(counts < 0):
        raise AssertionError("Negative counts were generated.")
    return counts


def _status_bounds(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=int)
    status = np.where(
        values == 0,
        "zero",
        np.where(values <= 9, "suppressed_1_9", "exact"),
    )
    lower = np.where(values == 0, 0, np.where(values <= 9, 1, values))
    upper = np.where(values == 0, 0, np.where(values <= 9, 9, values))
    return status.astype(object), lower.astype(int), upper.astype(int)


def public_frame_from_complete_counts(
    frame: pd.DataFrame,
    complete_counts: np.ndarray,
) -> pd.DataFrame:
    """Apply WONDER-style 1–9 suppression and build compatible aggregates."""

    if len(frame) != len(complete_counts):
        raise ValueError("Count vector length does not match the calibration frame.")
    out = frame.copy().reset_index(drop=True)
    counts = np.asarray(complete_counts, dtype=int)
    status, lower, upper = _status_bounds(counts)
    out["q002_count_status"] = status
    out["q002_lower"] = lower
    out["q002_upper"] = upper
    out["q002_exact_count"] = np.where(status == "exact", counts, np.nan)
    out.loc[out["q002_count_status"].eq("zero"), "q002_exact_count"] = 0

    temporary = out[["county_fips", "state_fips", "year"]].copy()
    temporary["complete_count"] = counts
    county_total = temporary.groupby("county_fips")["complete_count"].transform("sum").to_numpy()
    period_status, period_lower, period_upper = _status_bounds(county_total)
    out["q001_period_status"] = period_status
    out["q001_period_lower"] = period_lower
    out["q001_period_upper"] = period_upper
    out["q001_period_exact_count"] = np.where(period_status == "exact", county_total, np.nan)
    out.loc[out["q001_period_status"].eq("zero"), "q001_period_exact_count"] = 0

    state_year_total = temporary.groupby(["state_fips", "year"])["complete_count"].transform("sum")
    national_year_total = temporary.groupby("year")["complete_count"].transform("sum")
    out["q004_state_year_total"] = state_year_total.to_numpy(dtype=int)
    out["q003_national_year_total"] = national_year_total.to_numpy(dtype=int)
    out.attrs["grand_total"] = int(counts.sum())
    out.attrs["calibration_complete_counts"] = counts
    assert_constraints(counts, out, label="synthetic_truth")
    return out


def suppression_summary(public_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize simulated visibility by rurality and overall."""

    rows: list[dict[str, object]] = []
    groupings: list[tuple[str, pd.DataFrame]] = [("overall", public_frame)]
    groupings.extend(
        (str(category), group)
        for category, group in public_frame.groupby("primary_rurality", sort=False)
    )
    for label, group in groupings:
        total = len(group)
        for status, count in group["q002_count_status"].value_counts().items():
            rows.append(
                {
                    "group": label,
                    "status": str(status),
                    "cells": int(count),
                    "fraction": float(count / total),
                }
            )
    return pd.DataFrame(rows)


def save_calibration_case(
    output_dir: Path,
    *,
    complete_frame: pd.DataFrame,
    public_frame: pd.DataFrame,
    complete_counts: np.ndarray,
    truth: CalibrationTruth,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    complete_frame.to_parquet(output_dir / "complete_frame.parquet", index=False)
    public_frame.to_parquet(output_dir / "public_suppressed_frame.parquet", index=False)
    pd.DataFrame(
        {
            "county_fips": public_frame["county_fips"].astype(str),
            "year": public_frame["year"].astype(str),
            "complete_count": np.asarray(complete_counts, dtype=int),
            "public_status": public_frame["q002_count_status"].astype(str),
            "public_lower": public_frame["q002_lower"].astype(int),
            "public_upper": public_frame["q002_upper"].astype(int),
        }
    ).to_csv(output_dir / "complete_truth_and_public_bounds.csv", index=False)
    import json

    (output_dir / "truth.json").write_text(
        json.dumps(truth.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    suppression_summary(public_frame).to_csv(
        output_dir / "suppression_summary.csv",
        index=False,
    )
