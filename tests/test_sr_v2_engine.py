from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.exact_validation import (  # noqa: E402
    empirical_count_kernel_frequencies,
    enumerate_feasible_states,
    exact_conditional_probabilities,
    exact_kernel_diagnostics,
    exact_transition_matrix,
)
from bayes_constrained.heatbath import amplitude_probabilities, feasible_amplitudes  # noqa: E402
from bayes_constrained.identifiability import (  # noqa: E402
    analyze_constraint_geometry,
    build_reduced_equality_matrix,
)
from bayes_constrained.model import log_prior, make_design  # noqa: E402
from bayes_constrained.sampler import (  # noqa: E402
    interval_path_transfer,
    run_mcmc,
    state_cycle_swap,
)
from bayes_constrained.support_graph import analyze_state_support, overall_support_summary  # noqa: E402
from bayes_constrained.target_density import centered_normal_log_density  # noqa: E402
from bayes_constrained.validation_cases import (  # noqa: E402
    structural_interval_path_frame,
    structural_interval_path_theta,
    structural_six_cycle_frame,
    structural_six_cycle_theta,
)


def interval_half_edge_frame() -> pd.DataFrame:
    frame = structural_six_cycle_frame().copy()
    mask = frame["county_fips"].eq("01005")
    frame.loc[mask, "q001_period_status"] = "suppressed_1_9"
    frame.loc[mask, "q001_period_lower"] = 2
    frame.loc[mask, "q001_period_upper"] = 4
    frame.attrs["grand_total"] = 9
    return frame


def test_centered_normal_density_uses_subspace_dimension() -> None:
    values = np.asarray([-1.0, 0.0, 1.0])
    sigma = 2.0
    expected = -0.5 * np.square(values / sigma).sum() - 2.0 * np.log(sigma)
    assert centered_normal_log_density(values, sigma) == pytest.approx(expected)


def test_model_prior_calls_centered_subspace_density() -> None:
    source = inspect.getsource(log_prior)
    assert "centered_normal_log_density(state, sigma_state)" in source
    assert "centered_normal_log_density(year, sigma_year)" in source


def test_local_runner_refreshes_log_posterior_after_count_moves() -> None:
    source = inspect.getsource(run_mcmc)
    marker = "Count moves mutate y. Refresh the current target value"
    assert marker in source
    assert source.index(marker) < source.index("for block, scale in scales.items():", source.index(marker))


def test_heatbath_enumerates_complete_integer_line() -> None:
    amplitudes = feasible_amplitudes(
        np.asarray([5, 5]),
        np.asarray([0, 1]),
        np.asarray([-1, 1]),
        lower=np.asarray([1, 1]),
        upper=np.asarray([9, 9]),
        county_code=np.asarray([0, 1]),
        period_total=np.asarray([5, 5]),
        period_lower=np.asarray([1, 1]),
        period_upper=np.asarray([9, 9]),
    )
    np.testing.assert_array_equal(amplitudes, np.arange(-4, 5))
    probabilities = amplitude_probabilities(np.linspace(-2.0, 2.0, len(amplitudes)))
    assert probabilities.sum() == pytest.approx(1.0)
    assert np.all(probabilities > 0)


def test_count_moves_use_heatbath_block_updates() -> None:
    for function in [state_cycle_swap, interval_path_transfer]:
        source = inspect.getsource(function)
        assert "_apply_heatbath_direction" in source
        assert "_try_apply_delta" not in source


def test_graph_rank_matches_dense_linear_algebra_on_exact_margin_toy() -> None:
    frame = structural_six_cycle_frame()
    geometry = analyze_constraint_geometry(frame)
    matrix, metadata, _ = build_reduced_equality_matrix(frame)
    nonzero = metadata["nonzero_columns"].to_numpy(dtype=int) > 0
    dense_rank = int(np.linalg.matrix_rank(matrix[nonzero].toarray()))
    assert geometry.latent_variables == 6
    assert geometry.independent_equalities == dense_rank
    assert geometry.equality_nullity == geometry.latent_variables - dense_rank
    assert geometry.graph_components_without_interval_half_edge == 1


def test_interval_half_edge_removes_the_component_margin_dependency() -> None:
    exact = analyze_constraint_geometry(structural_six_cycle_frame())
    interval = analyze_constraint_geometry(interval_half_edge_frame())
    assert interval.independent_equalities == exact.independent_equalities
    assert interval.nonzero_reduced_equalities == exact.nonzero_reduced_equalities - 1
    assert interval.intrinsic_margin_dependencies == exact.intrinsic_margin_dependencies - 1
    assert interval.graph_components_without_interval_half_edge == 0


def test_support_graph_detects_chordless_six_cycle_without_four_cycle() -> None:
    by_state = analyze_state_support(structural_six_cycle_frame())
    assert len(by_state) == 1
    row = by_state.iloc[0]
    assert int(row["exact_support_cycle_rank"]) == 1
    assert int(row["exact_support_cycle_edges"]) == 6
    assert int(row["exact_support_four_cycle_edges"]) == 0
    assert int(row["exact_support_long_cycle_only_edges"]) == 6
    assert int(row["exact_support_unspanned_cycle_dimension_gf2"]) == 1
    assert int(row["cyclic_components_without_four_cycle"]) == 1
    overall = overall_support_summary(by_state)
    assert overall["states_with_long_cycle_only_edges"] == 1


def test_v111_two_by_two_kernel_is_disconnected_on_a_six_cycle_support() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    assert len(states) == 2
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame)
    transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 0.0,
            "swap_2x2": 1.0,
            "cycle_swap": 0.0,
        },
    )
    probabilities = exact_conditional_probabilities(states, theta, design)
    diagnostics = exact_kernel_diagnostics(probabilities, transition)
    assert diagnostics.strongly_connected_components == 2


def test_general_cycle_heatbath_connects_and_preserves_exact_posterior() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame)
    probabilities = exact_conditional_probabilities(states, theta, design)
    assert abs(probabilities[0] - probabilities[1]) > 0.01
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


def test_interval_path_is_required_for_cross_year_interval_endpoints() -> None:
    frame = structural_interval_path_frame()
    states = enumerate_feasible_states(frame)
    assert len(states) == 2
    theta = structural_interval_path_theta(frame)
    design = make_design(frame)
    probabilities = exact_conditional_probabilities(states, theta, design)
    blocked = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.25,
            "county_period_exploration": 0.25,
            "interval_path_transfer": 0.0,
            "swap_2x2": 0.25,
            "cycle_swap": 0.25,
        },
        max_cycle_half_length=2,
    )
    repaired = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 1.0,
            "swap_2x2": 0.0,
            "cycle_swap": 0.0,
        },
        max_cycle_half_length=2,
    )
    blocked_diagnostics = exact_kernel_diagnostics(probabilities, blocked)
    repaired_diagnostics = exact_kernel_diagnostics(probabilities, repaired)
    assert blocked_diagnostics.strongly_connected_components == 2
    assert repaired_diagnostics.strongly_connected_components == 1
    assert repaired_diagnostics.row_sum_error < 1e-12
    assert repaired_diagnostics.stationarity_error < 1e-12
    assert repaired_diagnostics.detailed_balance_error < 1e-12


def test_empirical_cycle_heatbath_matches_exact_toy_posterior() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    probabilities = exact_conditional_probabilities(states, theta, make_design(frame))
    empirical = empirical_count_kernel_frequencies(
        states[0],
        states,
        frame,
        theta,
        steps=40_000,
        burn_in=2_000,
        seed=20260810,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )
    np.testing.assert_allclose(empirical, probabilities, atol=0.02, rtol=0.0)


def test_empirical_interval_path_heatbath_matches_exact_toy_posterior() -> None:
    frame = structural_interval_path_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_interval_path_theta(frame)
    probabilities = exact_conditional_probabilities(states, theta, make_design(frame))
    empirical = empirical_count_kernel_frequencies(
        states[0],
        states,
        frame,
        theta,
        steps=30_000,
        burn_in=1_000,
        seed=20260811,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "interval_path_transfer": 1.0,
            "swap_2x2": 0.0,
            "cycle_swap": 0.0,
        },
        max_cycle_half_length=2,
    )
    np.testing.assert_allclose(empirical, probabilities, atol=0.02, rtol=0.0)
