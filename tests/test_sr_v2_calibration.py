from __future__ import annotations

import numpy as np

from bayes_constrained.calibration import (
    make_calibration_truth,
    public_frame_from_complete_counts,
    simulate_complete_counts,
    suppression_summary,
)
from bayes_constrained.calibration_design import select_state_clustered_panel
from bayes_constrained.constraints import solve_feasible_allocation, validate_constraints
from bayes_constrained.data import load_model_frame


def test_state_clustered_calibration_panel_is_complete_and_nontrivial() -> None:
    full = load_model_frame()
    panel = select_state_clustered_panel(full, max_states=4, counties_per_state=8)
    assert panel["state_fips"].nunique() == 4
    assert panel["county_fips"].nunique() == 32
    assert len(panel) == 32 * full["year"].astype(str).nunique()
    assert panel["primary_rurality"].nunique() == 4
    assert (panel.drop_duplicates("county_fips").groupby("state_fips").size() == 8).all()


def test_synthetic_truth_survives_suppression_and_all_constraints() -> None:
    full = load_model_frame()
    panel = select_state_clustered_panel(full, max_states=4, counties_per_state=8)
    theta, truth = make_calibration_truth(panel, seed=1001)
    counts = simulate_complete_counts(panel, theta, seed=1002)
    public = public_frame_from_complete_counts(panel, counts)

    result = validate_constraints(counts, public)
    assert result.passed
    assert public.attrs["grand_total"] == int(counts.sum())
    assert truth.beta_by_term["primary_rurality_nonmetro_nonadjacent"] == np.log(1.23)
    assert set(public["q002_count_status"].unique()) <= {"zero", "suppressed_1_9", "exact"}
    suppressed = public["q002_count_status"].eq("suppressed_1_9")
    assert suppressed.any()
    assert (public.loc[suppressed, "q002_lower"] == 1).all()
    assert (public.loc[suppressed, "q002_upper"] == 9).all()

    allocation = solve_feasible_allocation(public, seed=1003, time_limit_seconds=30)
    assert validate_constraints(allocation, public).passed


def test_suppression_summary_fractions_sum_to_one_within_group() -> None:
    full = load_model_frame()
    panel = select_state_clustered_panel(full, max_states=4, counties_per_state=8)
    theta, _ = make_calibration_truth(panel, seed=2001)
    counts = simulate_complete_counts(panel, theta, seed=2002)
    public = public_frame_from_complete_counts(panel, counts)
    summary = suppression_summary(public)
    grouped = summary.groupby("group")["fraction"].sum().to_numpy(dtype=float)
    np.testing.assert_allclose(grouped, np.ones_like(grouped), atol=1e-12)
