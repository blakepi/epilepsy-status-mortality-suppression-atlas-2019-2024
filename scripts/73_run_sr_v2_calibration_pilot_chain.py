from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.constraints import assert_constraints  # noqa: E402
from bayes_constrained.model import (  # noqa: E402
    crude_intercept_prior,
    initialize_theta,
    log_posterior_theta,
    make_design,
)
from bayes_constrained.sampler import run_mcmc_chain_hpc, save_chain_checkpoint  # noqa: E402


DESIGN_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_design_smoke"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_pilot" / "replicate_001"
N_ITER = 8000
BURN_IN = 2000
THIN = 10


def load_public_frame() -> pd.DataFrame:
    frame = pd.read_parquet(DESIGN_ROOT / "public_suppressed_frame.parquet")
    summary = json.loads((DESIGN_ROOT / "calibration_design_summary.json").read_text(encoding="utf-8"))
    frame.attrs["grand_total"] = int(summary["grand_total"])
    return frame


def initial_allocation(frame: pd.DataFrame, chain_id: int) -> np.ndarray:
    path = DESIGN_ROOT / f"feasible_initialization_{chain_id}.parquet"
    initial = pd.read_parquet(path)
    keys = frame[["county_fips", "year"]].copy()
    keys["county_fips"] = keys["county_fips"].astype(str)
    keys["year"] = keys["year"].astype(str)
    initial["county_fips"] = initial["county_fips"].astype(str)
    initial["year"] = initial["year"].astype(str)
    merged = keys.merge(
        initial[["county_fips", "year", "latent_count"]],
        on=["county_fips", "year"],
        how="left",
        validate="one_to_one",
    )
    if merged["latent_count"].isna().any():
        raise ValueError(f"Calibration initialization {chain_id} does not match the public frame.")
    y = merged["latent_count"].to_numpy(dtype=int)
    assert_constraints(y, frame, label=f"calibration_chain{chain_id}_initial")
    return y


def build_config(chain_id: int) -> Path:
    payload = {
        "run": {
            "n_chains": 4,
            "n_iter": N_ITER,
            "burn_in": BURN_IN,
            "thin": THIN,
            "count_move_sweeps_per_iter": 0.40,
            "max_count_proposals_per_iter": 250,
            "blocked_refresh_frequency": 25,
            "blocked_refresh_attempts": 8,
            "checkpoint_every": 500,
            "random_seeds": [42001, 42002, 42003, 42004],
            "move_weights": {
                "state_year_transfer": 0.10,
                "county_period_exploration": 0.25,
                "interval_path_transfer": 0.25,
                "swap_2x2": 0.30,
                "cycle_swap": 0.10,
            },
            "proposal_scale_multipliers": {
                "beta": 0.60,
                "state": 1.30,
                "year": 1.50,
                "log_sigma_state": 5.00,
                "log_sigma_year": 9.00,
                "log_kappa": 2.40,
            },
            "max_cycle_half_length": 6,
            "target_acceptance_parameter_blocks": [0.20, 0.45],
        },
        "model": {
            "outcome": "truth-known synthetic MCOD-like county counts",
            "rurality_reference": "metro_large",
            "svi_reference": "Q1_lowest",
        },
        "outputs": {
            "hpc_root": str(OUTPUT_ROOT.relative_to(ROOT)).replace("\\", "/"),
        },
        "scientific_reports_v2": {
            "purpose": "End-to-end corrected constrained-model calibration pilot.",
            "replicate": 1,
            "truth_source": str((DESIGN_ROOT / "truth.json").relative_to(ROOT)).replace("\\", "/"),
            "not_for_empirical_inference": True,
        },
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_ROOT / f"calibration_pilot_chain_{chain_id:02d}_config.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def write_initial_checkpoint(frame: pd.DataFrame, chain_id: int, y: np.ndarray) -> Path:
    chain_dir = OUTPUT_ROOT / "chains" / f"chain_{chain_id:02d}"
    if chain_dir.exists():
        shutil.rmtree(chain_dir)
    checkpoint_dir = chain_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    design = make_design(frame)
    theta = initialize_theta(frame, y, design)
    current_lp = log_posterior_theta(
        y,
        theta,
        design,
        intercept_mean=crude_intercept_prior(frame),
    )
    rng = np.random.default_rng(42000 + chain_id)
    accepted = {
        "transfer": 0,
        "interval_transfer": 0,
        "interval_path": 0,
        "swap_2x2": 0,
        "cycle_swap": 0,
        "blocked_refresh": 0,
    }
    proposed = {key: 0 for key in accepted}
    parameter_blocks = [
        "beta",
        "state",
        "year",
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
    ]
    checkpoint = checkpoint_dir / "checkpoint_iter_000000000.npz"
    save_chain_checkpoint(
        checkpoint,
        y=y,
        theta=theta,
        rng=rng,
        iteration=0,
        saved_draws=0,
        current_lp=current_lp,
        accepted=accepted,
        proposed=proposed,
        param_accept={key: 0 for key in parameter_blocks},
        param_prop={key: 0 for key in parameter_blocks},
    )
    return checkpoint_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-id", type=int, required=True, choices=range(1, 5))
    args = parser.parse_args()

    frame = load_public_frame()
    y = initial_allocation(frame, args.chain_id)
    checkpoint_dir = write_initial_checkpoint(frame, args.chain_id, y)
    config_path = build_config(args.chain_id)
    status = run_mcmc_chain_hpc(
        frame,
        config_path=config_path,
        mode="production",
        chain_id=args.chain_id,
        seed=42000 + args.chain_id,
        out_dir=OUTPUT_ROOT,
        checkpoint_dir=checkpoint_dir,
        resume=True,
        force=True,
        max_runtime_minutes=75,
        stop_before_time_limit_minutes=8,
    )
    expected_draws = (N_ITER - BURN_IN) // THIN
    if status.get("status") != "completed":
        raise SystemExit(f"Calibration chain {args.chain_id} did not complete: {status}")
    if int(status.get("iteration", -1)) != N_ITER:
        raise SystemExit(f"Calibration chain {args.chain_id} did not reach {N_ITER} iterations.")
    if int(status.get("saved_draws", -1)) != expected_draws:
        raise SystemExit(
            f"Calibration chain {args.chain_id} retained {status.get('saved_draws')} draws; "
            f"expected {expected_draws}."
        )
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
