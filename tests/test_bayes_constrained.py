from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.stats import nbinom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "hpc_wahab"))

from bayes_constrained.constraints import assert_constraints, solve_feasible_allocation, validate_constraints  # noqa: E402
from bayes_constrained.data import GRAND_TOTAL, load_model_frame  # noqa: E402
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402
from bayes_constrained.model import Theta, nb2_logpmf  # noqa: E402
from bayes_constrained.sampler import _center_random_effects, build_move_state, load_chain_checkpoint, save_chain_checkpoint, state_2x2_swap, state_year_transfer  # noqa: E402
from common import read_submitted_jobs  # noqa: E402
from gate_convergence import gate  # noqa: E402


def toy_frame() -> pd.DataFrame:
    rows = []
    counties = [("01001", "A"), ("01003", "B")]
    years = ["2019", "2020"]
    for county_fips, county_name in counties:
        for year in years:
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "state_fips": "01",
                    "state_name": "Toy",
                    "year": year,
                    "population": 1000,
                    "q002_count_status": "suppressed_1_9",
                    "q002_lower": 1,
                    "q002_upper": 9,
                    "q001_period_status": "exact",
                    "q001_period_lower": 5,
                    "q001_period_upper": 5,
                    "q004_state_year_total": 5,
                    "q003_national_year_total": 5,
                    "primary_rurality": "metro_large",
                    "svi_quartile": "Q1_lowest",
                    "z_pct_age65": 0.0,
                    "z_pct_male": 0.0,
                }
            )
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = 10
    return frame


def test_nb2_logpmf_matches_scipy_for_known_values() -> None:
    y = np.arange(0, 8)
    mu = np.linspace(0.5, 6.0, len(y))
    kappa = 2.7
    p = kappa / (kappa + mu)
    expected = nbinom.logpmf(y, kappa, p)
    np.testing.assert_allclose(nb2_logpmf(y, mu, kappa), expected, rtol=1e-10, atol=1e-10)


def test_constraint_validator_accepts_known_feasible_toy_example() -> None:
    frame = toy_frame()
    y = np.array([2, 3, 3, 2])
    assert validate_constraints(y, frame).passed


def test_constraint_validator_rejects_noninteger_counts() -> None:
    frame = toy_frame()
    y = np.array([2.5, 2.5, 3, 2])
    assert not validate_constraints(y, frame).checks["all_counts_integer"]


def test_constraint_validator_rejects_count_below_suppressed_lower_bound() -> None:
    frame = toy_frame()
    y = np.array([0, 5, 5, 0])
    assert not validate_constraints(y, frame).checks["county_year_bounds_respected"]


def test_constraint_validator_rejects_count_above_suppressed_upper_bound() -> None:
    frame = toy_frame()
    y = np.array([10, -5, 5, 0])
    result = validate_constraints(y, frame)
    assert not result.checks["county_year_bounds_respected"]
    assert not result.checks["no_negative_counts"]


def test_constraint_validator_rejects_state_year_total_mismatch() -> None:
    frame = toy_frame()
    y = np.array([1, 4, 1, 4])
    assert not validate_constraints(y, frame).checks["state_year_totals_equal_q004"]


def test_constraint_validator_rejects_national_year_total_mismatch() -> None:
    frame = toy_frame()
    frame.loc[frame["year"].eq("2019"), "q003_national_year_total"] = 6
    y = np.array([2, 3, 3, 2])
    assert not validate_constraints(y, frame).checks["national_year_totals_equal_q003"]


def test_constraint_validator_rejects_county_period_total_mismatch() -> None:
    frame = toy_frame()
    y = np.array([1, 1, 4, 4])
    assert not validate_constraints(y, frame).checks["county_period_constraints_respected"]


def test_milp_initialization_returns_feasible_toy_solution() -> None:
    frame = toy_frame()
    y = solve_feasible_allocation(frame, seed=123, time_limit_seconds=30)
    assert validate_constraints(y, frame).passed


def test_mcmc_count_moves_preserve_constraints_on_toy_problem() -> None:
    frame = toy_frame()
    y = np.array([2, 3, 3, 2])
    move = build_move_state(frame, y)
    rng = np.random.default_rng(42)
    current_mu = np.full(len(y), 2.5)
    for _ in range(30):
        state_year_transfer(y, move, current_mu, 10.0, rng)
        state_2x2_swap(y, move, current_mu, 10.0, rng)
        assert validate_constraints(y, frame).passed


def test_model_frame_reconciles_to_58380_for_full_mcod_extract() -> None:
    frame = load_model_frame()
    assert int(frame.drop_duplicates("year")["q003_national_year_total"].sum()) == GRAND_TOTAL
    assert frame["county_fips"].nunique() == 3142


def test_no_suppressed_cells_treated_as_zero() -> None:
    frame = load_model_frame()
    suppressed = frame["q002_count_status"].eq("suppressed_1_9")
    assert suppressed.any()
    assert (frame.loc[suppressed, "q002_lower"] >= 1).all()


def test_all_saved_posterior_draw_batches_pass_constraints() -> None:
    frame = load_model_frame()
    path = ROOT / "outputs" / "bayes_constrained" / "posterior_draws_primary.npz"
    if not path.exists():
        pytest.skip("posterior draw batch not generated yet")
    y = np.load(path, allow_pickle=True)["y"]
    assert y.shape[0] > 0
    for idx in range(y.shape[0]):
        assert_constraints(y[idx], frame, label=f"test_saved_draw_{idx + 1}")


def test_chain_checkpoint_roundtrip_preserves_state(tmp_path: Path) -> None:
    rng = np.random.default_rng(123)
    theta = Theta(
        beta=np.array([1.0, 2.0]),
        state_effect=np.array([0.1, -0.1]),
        year_effect=np.array([0.2, -0.2]),
        log_sigma_state=-1.0,
        log_sigma_year=-1.1,
        log_kappa=2.0,
    )
    path = tmp_path / "checkpoint_iter_000000010.npz"
    save_chain_checkpoint(
        path,
        y=np.array([1, 2, 3]),
        theta=theta,
        rng=rng,
        iteration=10,
        saved_draws=2,
        current_lp=-123.4,
        accepted={"transfer": 1},
        proposed={"transfer": 3},
        param_accept={"beta": 2},
        param_prop={"beta": 4},
    )
    loaded = load_chain_checkpoint(path)
    np.testing.assert_array_equal(loaded["y"], np.array([1, 2, 3]))
    np.testing.assert_allclose(loaded["theta"].beta, theta.beta)
    assert loaded["iteration"] == 10
    assert loaded["saved_draws"] == 2
    assert loaded["accepted"] == {"transfer": 1}


def test_checkpoint_resume_rng_reproduces_next_draw(tmp_path: Path) -> None:
    rng = np.random.default_rng(321)
    theta = Theta(np.array([0.0]), np.array([0.0]), np.array([0.0]), -1.0, -1.0, 2.0)
    _ = rng.normal(size=5)
    path = tmp_path / "checkpoint_iter_000000005.npz"
    save_chain_checkpoint(
        path,
        y=np.array([2, 3]),
        theta=theta,
        rng=rng,
        iteration=5,
        saved_draws=0,
        current_lp=-1.0,
        accepted={},
        proposed={},
        param_accept={},
        param_prop={},
    )
    expected = rng.normal(size=4)
    loaded = load_chain_checkpoint(path)
    actual = loaded["rng"].normal(size=4)
    np.testing.assert_allclose(actual, expected)


def test_random_effect_projection_enforces_identified_parameterization() -> None:
    theta = Theta(
        beta=np.array([0.0]),
        state_effect=np.array([10.0, 11.0, 13.0]),
        year_effect=np.array([-5.0, -2.0]),
        log_sigma_state=-1.0,
        log_sigma_year=-1.0,
        log_kappa=2.0,
    )
    centered = _center_random_effects(theta)
    assert centered.state_effect.mean() == pytest.approx(0.0, abs=1e-12)
    assert centered.year_effect.mean() == pytest.approx(0.0, abs=1e-12)
    np.testing.assert_allclose(
        theta.state_effect - theta.state_effect.mean(),
        centered.state_effect,
    )


def test_hpc_config_yamls_parse() -> None:
    for path in (ROOT / "hpc" / "wahab" / "configs").glob("*.yaml"):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "run" in loaded
        assert "model" in loaded


def _write_gate_inputs(base: Path, *, r_hat: float = 1.01, ess: float = 500.0, extension_round: int = 0) -> Path:
    base.mkdir(parents=True)
    parameters = [
        "primary_rurality_metro_other",
        "primary_rurality_nonmetro_adjacent",
        "primary_rurality_nonmetro_nonadjacent",
        "svi_quartile_Q2",
        "svi_quartile_Q3",
        "svi_quartile_Q4_highest",
        "kappa",
        "sigma_state",
        "sigma_year",
        "Intercept",
        "z_pct_age65",
        "z_pct_male",
        "state_effect[01]",
        "year_effect[2019]",
    ]
    pd.DataFrame(
        {
            "parameter": parameters,
            "r_hat": [r_hat] * len(parameters),
            "ess_bulk": [ess] * len(parameters),
            "ess_tail": [ess] * len(parameters),
            "chains": [8] * len(parameters),
            "draws_per_chain": [4500] * len(parameters),
        }
    ).to_csv(base / "hpc_mcmc_diagnostics.csv", index=False)
    pd.DataFrame({"label": ["draw1"], "check": ["grand_total_equals_58380"], "passed": [True], "detail": ["58380"]}).to_csv(base / "hpc_constraint_validation_summary.csv", index=False)
    pd.DataFrame(
        {
            "chain": [f"chain_{idx:02d}" for idx in range(1, 9)],
            "status": ["completed"] * 8,
            "grand_total": [58380] * 8,
            "suppressed_cells_treated_as_zero": [False] * 8,
        }
    ).to_csv(base / "chain_status_summary.csv", index=False)
    (base / "extension_round.txt").write_text(f"{extension_round}\n", encoding="utf-8")
    config = base / "config.yaml"
    config.write_text(
        "run:\n  n_chains: 8\n  max_extensions: 4\n  extension_n_iter: 150000\n"
        f"diagnostics:\n  expected_parameters: {len(parameters)}\n  rhat_max: 1.01\n  ess_bulk_min: 400\n  ess_tail_min: 400\n",
        encoding="utf-8",
    )
    return config


def test_modern_diagnostics_cover_every_parameter() -> None:
    rng = np.random.default_rng(20260715)
    rows = []
    for chain in range(1, 5):
        for draw in range(1, 1001):
            rows.append({"chain": chain, "draw": draw, "parameter": "alpha", "value": rng.normal()})
            rows.append({"chain": chain, "draw": draw, "parameter": "beta", "value": rng.normal(0.2, 0.5)})
    result = diagnostics_table(pd.DataFrame(rows), output_dir=None)
    assert set(result["parameter"]) == {"alpha", "beta"}
    assert {"r_hat", "ess_bulk", "ess_tail", "mcse_mean", "mcse_sd"}.issubset(result.columns)
    assert (result["r_hat"] <= 1.01).all()
    assert (result["ess_bulk"] > 400).all()


def test_modern_diagnostics_reject_duplicate_chain_draw_rows() -> None:
    rows = []
    for chain in [1, 2]:
        for draw in range(1, 11):
            rows.append({"chain": chain, "draw": draw, "parameter": "alpha", "value": float(draw)})
    rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match="Duplicate chain/draw"):
        diagnostics_table(pd.DataFrame(rows), output_dir=None)


def test_convergence_gate_passes_on_synthetic_diagnostics(tmp_path: Path) -> None:
    config = _write_gate_inputs(tmp_path / "hpc")
    result = gate(config, hpc_out=tmp_path / "hpc")
    assert result["passed"]
    assert result["action"] == "finalize"


def test_convergence_gate_extends_then_stops_on_synthetic_failures(tmp_path: Path) -> None:
    config = _write_gate_inputs(tmp_path / "hpc_extend", r_hat=1.5, ess=10.0, extension_round=0)
    result = gate(config, hpc_out=tmp_path / "hpc_extend")
    assert not result["passed"]
    assert result["action"] == "extend"
    config = _write_gate_inputs(tmp_path / "hpc_stop", r_hat=1.5, ess=10.0, extension_round=4)
    result = gate(config, hpc_out=tmp_path / "hpc_stop")
    assert result["action"] == "stop_nonfinal"


def test_submitted_job_tsv_parser(tmp_path: Path) -> None:
    path = tmp_path / "submitted_jobs.tsv"
    path.write_text("submitted_at\tstage\tjob_id\tdependency\tscript\nnow\tsmoke\t123\t\ta.sbatch\n", encoding="utf-8")
    rows = read_submitted_jobs(path)
    assert rows == [{"submitted_at": "now", "stage": "smoke", "job_id": "123", "dependency": "", "script": "a.sbatch"}]


def test_slurm_scripts_have_required_logging_and_environment_activation() -> None:
    for path in (ROOT / "hpc" / "wahab" / "slurm").glob("*.sbatch"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/bin/bash -l")
        assert "#SBATCH --job-name" in text
        assert "#SBATCH --output=logs/slurm/%x_%A_%a.out" in text
        assert "#SBATCH --error=logs/slurm/%x_%A_%a.err" in text
        assert 'source "$VENV_PATH/bin/activate"' in text
        assert "PYTHONPATH=\"$PROJECT_HOME\"" in text
        assert "MPLBACKEND=Agg" in text
        assert "sync_results_home.sh" in text
        assert "make " not in text.lower()


def test_production_slurm_uses_main_partition_and_no_gpu_resources() -> None:
    text = (ROOT / "hpc" / "wahab" / "slurm" / "30_production_chain_array.sbatch").read_text(encoding="utf-8").lower()
    assert "#SBATCH --partition=main".lower() in text
    assert "--nodes=1" in text
    assert "--gres" not in text
    assert "gpu" not in text
    assert "--exclusive" not in text


def test_timed_slurm_jobs_use_timed_main_and_under_two_hours() -> None:
    timed = ["00_smoke_timed.sbatch", "20_tune_array_timed.sbatch", "50_finalize_manuscript.sbatch", "99_failure_report.sbatch"]
    for name in timed:
        text = (ROOT / "hpc" / "wahab" / "slurm" / name).read_text(encoding="utf-8")
        assert "#SBATCH --partition=timed-main" in text
        time_line = next(line for line in text.splitlines() if line.startswith("#SBATCH --time="))
        hours, minutes, seconds = [int(part) for part in time_line.split("=")[1].split(":")]
        assert hours * 3600 + minutes * 60 + seconds <= 2 * 3600


def test_no_rc_compute_working_directory_in_slurm_scripts() -> None:
    for path in (ROOT / "hpc" / "wahab" / "slurm").glob("*.sbatch"):
        assert "/RC" not in path.read_text(encoding="utf-8")


def test_no_hard_coded_local_windows_path_in_hpc_runtime_scripts() -> None:
    runtime_paths = list((ROOT / "hpc" / "wahab" / "slurm").glob("*.sbatch"))
    runtime_paths += [path for path in (ROOT / "hpc" / "wahab").glob("*.sh")]
    runtime_paths += [path for path in (ROOT / "scripts" / "hpc_wahab").glob("*.py") if path.name != "print_manual_next_steps.py"]
    for path in runtime_paths:
        text = path.read_text(encoding="utf-8")
        assert "C:\\" not in text
        assert "C:/" not in text


def test_scratch_home_path_resolution_and_dry_run_flags() -> None:
    stage = (ROOT / "hpc" / "wahab" / "stage_to_scratch.sh").read_text(encoding="utf-8")
    sync = (ROOT / "hpc" / "wahab" / "sync_results_home.sh").read_text(encoding="utf-8")
    assert 'PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"' in stage
    assert 'PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"' in stage
    assert "--dry-run" in stage
    assert "--dry-run" in sync
    assert "--delete" in sync


def test_no_gpu_partition_or_gres_in_default_slurm_scripts() -> None:
    for path in (ROOT / "hpc" / "wahab" / "slurm").glob("*.sbatch"):
        text = path.read_text(encoding="utf-8").lower()
        assert "high-gpu-mem" not in text
        assert "#SBATCH --gres" not in text
        assert "#SBATCH --partition=gpu" not in text
