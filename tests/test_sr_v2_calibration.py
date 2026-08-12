from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.calibration import (  # noqa: E402
    make_calibration_truth,
    public_frame_from_complete_counts,
    simulate_complete_counts,
    suppression_summary,
)
from bayes_constrained.calibration_design import select_state_clustered_panel  # noqa: E402
from bayes_constrained.calibration_study import (  # noqa: E402
    scenario_for_replicate,
    scenarios_for_batch,
)
from bayes_constrained.constraints import solve_feasible_allocation, validate_constraints  # noqa: E402
from bayes_constrained.data import load_model_frame  # noqa: E402


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


def test_second_calibration_batch_is_balanced_and_independently_seeded() -> None:
    batch1 = scenarios_for_batch(1)
    batch2 = scenarios_for_batch(2)
    assert len(batch1) == 4
    assert len(batch2) == 16

    family_counts: dict[str, int] = {}
    for scenario in batch2:
        family_counts[scenario.scenario_id] = (
            family_counts.get(scenario.scenario_id, 0) + 1
        )
    assert set(family_counts.values()) == {4}
    assert set(family_counts) == {item.scenario_id for item in batch1}

    all_scenarios = (*batch1, *batch2)
    assert len({item.truth_seed for item in all_scenarios}) == len(all_scenarios)
    assert len({item.count_seed for item in all_scenarios}) == len(all_scenarios)
    assert len({item.initialization_seed_base for item in all_scenarios}) == len(
        all_scenarios
    )
    assert scenario_for_replicate(16, batch_id=2) == batch2[-1]


def test_second_calibration_batch_workflow_matches_frozen_request() -> None:
    request = json.loads(
        (
            ROOT
            / "outputs"
            / "scientific_reports_v2"
            / "calibration_study_batch2_requested.json"
        ).read_text(encoding="utf-8")
    )
    workflow = (
        ROOT / ".github" / "workflows" / "sr-v2-calibration-study-batch2.yml"
    ).read_text(encoding="utf-8")
    assert request["replicates"] == 16
    assert request["combined_program_replicates_after_completion"] == 20
    assert set(request["scenario_families"].values()) == {4}
    assert workflow.count("--batch-id 2") == 4
    assert "calibration_study_batch2_requested.json" in workflow
    assert "scripts/97_aggregate_sr_v2_calibration_program.py" in workflow
    assert "calibration_reporting_gate.json" in workflow


def test_combined_calibration_reporting_gate_requires_complete_balanced_program(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script = ROOT / "scripts" / "97_aggregate_sr_v2_calibration_program.py"
    spec = importlib.util.spec_from_file_location("calibration_program_aggregate", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(module, "PROGRAM_ROOT", tmp_path / "calibration_program")

    families = [item.scenario_id for item in scenarios_for_batch(1)]
    parameters = [f"parameter_{index}" for index in range(6)]
    for batch_id, replicate_count in ((1, 4), (2, 16)):
        root = tmp_path / f"calibration_study_batch{batch_id}"
        root.mkdir(parents=True)
        statuses = []
        primary = []
        latent = []
        comparators = []
        for replicate_id in range(1, replicate_count + 1):
            family = families[(replicate_id - 1) % 4]
            statuses.append(
                {
                    "replicate_id": replicate_id,
                    "scenario_id": family,
                    "computational_gate_pass": True,
                    "maximum_primary_rhat": 1.01,
                    "minimum_primary_bulk_ess": 150.0,
                    "minimum_primary_tail_ess": 175.0,
                }
            )
            for parameter in parameters:
                primary.append(
                    {
                        "replicate": replicate_id,
                        "scenario": family,
                        "parameter": parameter,
                        "truth_covered_by_95_interval": True,
                        "bias_irr": 0.01,
                        "squared_error_irr": 0.0001,
                        "relative_bias_percent": 1.0,
                        "interval_width": 0.2,
                        "r_hat": 1.01,
                        "ess_bulk": 150.0,
                        "ess_tail": 175.0,
                    }
                )
            latent.append(
                {
                    "replicate": replicate_id,
                    "scenario": family,
                    "cell_group": "suppressed_cells",
                    "cells": 200,
                    "coverage_95": 0.95,
                    "root_mean_squared_error": 1.0,
                }
            )
            comparators.append(
                {
                    "replicate": replicate_id,
                    "scenario": "visible_only",
                    "term": parameters[0],
                    "truth_covered_by_95_interval": False,
                    "bias_irr": -0.05,
                    "squared_error_irr": 0.0025,
                }
            )
        pd.DataFrame(statuses).to_csv(root / "replicate_status.csv", index=False)
        pd.DataFrame(primary).to_csv(
            root / "primary_recovery_all_replicates.csv",
            index=False,
        )
        pd.DataFrame(latent).to_csv(
            root / "latent_recovery_all_replicates.csv",
            index=False,
        )
        pd.DataFrame(comparators).to_csv(
            root / "comparator_results_all_replicates.csv",
            index=False,
        )

    module.main()
    gate = json.loads(
        (module.PROGRAM_ROOT / "calibration_reporting_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["passed"] is True
    assert gate["observed_replicates"] == 20
    assert set(gate["observed_replicates_by_truth_scenario"].values()) == {5}
    assert gate["precise_nominal_coverage_claim_authorized"] is False
