from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .constraints import solve_feasible_allocation
from .model import PRIMARY_TERMS, make_design


CALIBRATION_TERMS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
]


def augmented_fixed_effect_design(frame: pd.DataFrame) -> pd.DataFrame:
    """Use the primary fixed effects plus state and year indicators for comparators."""

    design = make_design(frame)
    x = pd.DataFrame(design.x, columns=design.columns, index=frame.index)
    state = pd.get_dummies(
        pd.Categorical(frame["state_fips"].astype(str)),
        prefix="state_fixed",
        drop_first=True,
        dtype=float,
    )
    year = pd.get_dummies(
        pd.Categorical(frame["year"].astype(str)),
        prefix="year_fixed",
        drop_first=True,
        dtype=float,
    )
    return pd.concat([x, state.set_axis(frame.index), year.set_axis(frame.index)], axis=1)


def fit_known_dispersion_glm(
    frame: pd.DataFrame,
    counts: np.ndarray,
    *,
    scenario: str,
    row_mask: np.ndarray | None = None,
    kappa: float = 10.0,
) -> pd.DataFrame:
    """Fit a transparent NB2 comparator using the simulation's known dispersion."""

    counts = np.asarray(counts, dtype=float)
    if len(counts) != len(frame):
        raise ValueError("Comparator count vector does not match frame length.")
    mask = np.ones(len(frame), dtype=bool) if row_mask is None else np.asarray(row_mask, dtype=bool)
    if mask.sum() <= 20:
        raise ValueError(f"Scenario {scenario!r} retains too few rows: {int(mask.sum())}.")
    x = augmented_fixed_effect_design(frame).loc[mask]
    y = counts[mask]
    offset = np.log(pd.to_numeric(frame.loc[mask, "population"], errors="coerce").clip(lower=1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            result = sm.GLM(
                y,
                x,
                family=sm.families.NegativeBinomial(alpha=1.0 / float(kappa)),
                offset=offset,
            ).fit(cov_type="HC0", maxiter=300)
            model_type = "NB2_GLM_known_dispersion_HC0"
        except Exception:
            result = sm.GLM(
                y,
                x,
                family=sm.families.Poisson(),
                offset=offset,
            ).fit(cov_type="HC0", maxiter=300)
            model_type = "Poisson_GLM_HC0_fallback"

    rows: list[dict[str, object]] = []
    for term in CALIBRATION_TERMS:
        if term not in result.params.index:
            continue
        coefficient = float(result.params[term])
        standard_error = float(result.bse[term])
        rows.append(
            {
                "scenario": scenario,
                "model_type": model_type,
                "term": term,
                "coefficient": coefficient,
                "irr": float(np.exp(coefficient)),
                "ci_low": float(np.exp(coefficient - 1.96 * standard_error)),
                "ci_high": float(np.exp(coefficient + 1.96 * standard_error)),
                "standard_error": standard_error,
                "n_rows": int(mask.sum()),
                "events": float(y.sum()),
            }
        )
    return pd.DataFrame(rows)


def comparator_scenarios(
    public_frame: pd.DataFrame,
    complete_counts: np.ndarray,
    *,
    kappa: float,
    allocation_seed: int = 20260813,
) -> pd.DataFrame:
    """Run transparent oracle, deletion, substitution, and feasible-allocation comparators."""

    complete_counts = np.asarray(complete_counts, dtype=int)
    suppressed = public_frame["q002_count_status"].eq("suppressed_1_9").to_numpy()
    visible = ~suppressed
    frames = [
        fit_known_dispersion_glm(
            public_frame,
            complete_counts,
            scenario="oracle_complete_counts",
            kappa=kappa,
        ),
        fit_known_dispersion_glm(
            public_frame,
            complete_counts,
            scenario="visible_exact_and_zero_only",
            row_mask=visible,
            kappa=kappa,
        ),
    ]
    public_lower = public_frame["q002_lower"].to_numpy(dtype=int)
    for value in [1, 5, 9]:
        assigned = public_lower.copy()
        assigned[suppressed] = value
        frames.append(
            fit_known_dispersion_glm(
                public_frame,
                assigned,
                scenario=f"suppressed_equals_{value}",
                kappa=kappa,
            )
        )
    feasible = solve_feasible_allocation(
        public_frame,
        seed=allocation_seed,
        objective="population",
        time_limit_seconds=60,
    )
    frames.append(
        fit_known_dispersion_glm(
            public_frame,
            feasible,
            scenario="population_favoring_feasible_allocation",
            kappa=kappa,
        )
    )
    return pd.concat(frames, ignore_index=True)
