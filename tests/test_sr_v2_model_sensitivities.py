from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from scipy.stats import poisson

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.exact_validation import (  # noqa: E402
    empirical_count_kernel_frequencies,
    enumerate_feasible_states,
    exact_conditional_probabilities,
    exact_kernel_diagnostics,
    exact_transition_matrix,
)
from bayes_constrained.heatbath import amplitude_log_weights  # noqa: E402
from bayes_constrained.model import (  # noqa: E402
    PRIMARY_TERMS,
    count_logpmf,
    log_likelihood,
    log_posterior_theta,
    make_design,
    mu,
    normalize_likelihood_family,
    poisson_logpmf,
)
from bayes_constrained.sampler import _proposal_scales, _theta_to_rows  # noqa: E402
from bayes_constrained.validation_cases import (  # noqa: E402
    structural_six_cycle_frame,
    structural_six_cycle_theta,
)


POISSON = "poisson"
NB2 = "negative_binomial_2"
INTERACTION_COLUMNS = [
    "primary_rurality_metro_other__x__acute_pandemic",
    "primary_rurality_nonmetro_adjacent__x__acute_pandemic",
    "primary_rurality_nonmetro_nonadjacent__x__acute_pandemic",
    "primary_rurality_metro_other__x__later_period",
    "primary_rurality_nonmetro_adjacent__x__later_period",
    "primary_rurality_nonmetro_nonadjacent__x__later_period",
]


def pandemic_frame() -> pd.DataFrame:
    rurality = [
        "metro_other",
        "nonmetro_adjacent",
        "nonmetro_nonadjacent",
        "metro_other",
        "nonmetro_adjacent",
        "nonmetro_nonadjacent",
    ]
    return pd.DataFrame(
        {
            "state_fips": ["01"] * 6,
            "year": ["2019", "2020", "2021", "2022", "2023", "2024"],
            "population": [1000.0] * 6,
            "primary_rurality": rurality,
            "svi_quartile": ["Q1_lowest"] * 6,
            "z_pct_age65": [0.0] * 6,
            "z_pct_male": [0.0] * 6,
        }
    )


def test_poisson_logpmf_matches_scipy() -> None:
    y = np.arange(8)
    means = np.linspace(0.2, 8.0, 8)
    assert_allclose(poisson_logpmf(y, means), poisson.logpmf(y, means))


def test_likelihood_family_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Unknown likelihood family"):
        normalize_likelihood_family("quasi_poisson")


@pytest.mark.parametrize("kappa", [None, 0.0, -1.0, np.inf, np.nan])
def test_nb2_dispatch_requires_finite_positive_kappa(kappa: float | None) -> None:
    with pytest.raises(ValueError, match="NB2 requires finite positive kappa"):
        count_logpmf(
            np.asarray([1]),
            np.asarray([2.0]),
            likelihood_family=NB2,
            kappa=kappa,
        )


def test_strict_poisson_posterior_is_kappa_invariant() -> None:
    frame = structural_six_cycle_frame()
    design = make_design(frame, likelihood_family=POISSON)
    y = enumerate_feasible_states(frame)[0]
    first = structural_six_cycle_theta(frame)
    first.log_kappa = -20.0
    second = first.copy()
    second.log_kappa = 20.0
    assert log_posterior_theta(
        y, first, design, intercept_mean=0.0
    ) == log_posterior_theta(y, second, design, intercept_mean=0.0)


def test_poisson_sampler_omits_kappa_proposal_and_draw_row() -> None:
    frame = structural_six_cycle_frame()
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    assert "log_kappa" not in _proposal_scales(
        theta, likelihood_family=design.likelihood_family
    )
    rows = _theta_to_rows(
        theta, design, chain=1, draw=1, iteration=10
    )
    assert "kappa" not in {row["parameter"] for row in rows}


def test_poisson_heatbath_ratio_equals_full_target_ratio() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    indices = np.flatnonzero(states[1] != states[0])
    direction = states[1, indices] - states[0, indices]
    weights = amplitude_log_weights(
        states[0],
        indices,
        direction,
        np.asarray([0, 1]),
        mu(theta, design)[indices],
        None,
        likelihood_family=design.likelihood_family,
    )
    assert weights[1] - weights[0] == pytest.approx(
        log_likelihood(states[1], theta, design)
        - log_likelihood(states[0], theta, design),
        abs=1e-12,
    )


def test_exact_poisson_kernel_has_detailed_balance_and_stationarity() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    probabilities = exact_conditional_probabilities(states, theta, design)
    transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )
    diagnostics = exact_kernel_diagnostics(probabilities, transition)
    assert diagnostics.row_sum_error < 1e-12
    assert diagnostics.stationarity_error < 1e-12
    assert diagnostics.detailed_balance_error < 1e-12
    assert diagnostics.strongly_connected_components == 1


def test_empirical_poisson_kernel_matches_exact_probabilities() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame, likelihood_family=POISSON)
    probabilities = exact_conditional_probabilities(states, theta, design)
    empirical = empirical_count_kernel_frequencies(
        states[0],
        states,
        frame,
        theta,
        likelihood_family=POISSON,
        steps=40_000,
        burn_in=2_000,
        seed=20260818,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )
    assert_allclose(empirical, probabilities, atol=0.02, rtol=0.0)


def test_default_nb2_exact_probabilities_are_unchanged() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    probabilities = exact_conditional_probabilities(
        states, theta, make_design(frame)
    )
    assert_allclose(
        probabilities,
        np.asarray([0.53319485446001524, 0.46680514553998531]),
        atol=1e-14,
        rtol=0.0,
    )


def test_pandemic_interaction_design_has_exact_six_columns_and_coding() -> None:
    design = make_design(pandemic_frame(), model="pandemic_interaction")
    assert [column for column in design.columns if "__x__" in column] == (
        INTERACTION_COLUMNS
    )
    selected = design.x[
        :, [design.columns.index(column) for column in INTERACTION_COLUMNS]
    ]
    assert_array_equal(
        selected,
        np.asarray(
            [
                [0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 1],
            ],
            dtype=float,
        ),
    )
    assert not any("period" in column for column in design.columns if "__x__" not in column)


def test_pandemic_interaction_rejects_years_outside_2019_through_2024() -> None:
    frame = pandemic_frame()
    frame.loc[0, "year"] = "2025"
    with pytest.raises(ValueError, match="2019 through 2024"):
        make_design(frame, model="pandemic_interaction")


def test_pandemic_interactions_are_not_standalone_primary_terms() -> None:
    assert not set(INTERACTION_COLUMNS).intersection(PRIMARY_TERMS)
