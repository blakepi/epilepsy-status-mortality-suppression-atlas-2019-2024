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

from bayes_constrained.calibration_study import (  # noqa: E402
    scenario_for_replicate,
    valid_replicates_for_batch,
)
from bayes_constrained.constraints import assert_constraints  # noqa: E402
from bayes_constrained.model import (  # noqa: E402
    crude_intercept_prior,
    initialize_theta,
    log_posterior_theta,
    make_design,
)
from bayes_constrained.sampler import run_mcmc_chain_hpc, save_chain_checkpoint  # noqa: E402


N_ITER = 24000
BURN_IN = 6000
THIN = 10


def batch_root(batch_id: int) -> Path:
    return (
        ROOT
        / "outputs"
        / "scientific_reports_v2"
        / f"calibration_study_batch{batch_id}"
    )


def replicate_root(batch_id: int, replicate_id: int) -> Path:
    return batch_root(batch_id) / f"replicate_{replicate_id:02d}"


def load_public_frame(batch_id: int, replicate_id: int) -> pd.DataFrame:
    design_root = replicate_root(batch_id, replicate_id) / "design"
    frame = pd.read_parquet(design_root / "public_suppressed_frame.parquet")
    summary = json.loads(
        (design_root / "design_summary.json").read_text(encoding="utf-8")
    )
    frame.attrs["grand_total"] = int(summary["grand_total"])
    return frame


def load_initial_allocation(
    frame: pd.DataFrame,
    batch_id: int,
    replicate_id: int,
    chain_id: int,
) -> np.ndarray:
    design_root = replicate_root(batch_id, replicate_id) / "design"
    initial = pd.read_parquet(
        design_root / f"initial_allocation_chain_{chain_id:02d}.parquet"
    )
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
        raise ValueError(
            f"Replicate {replicate_id} chain {chain_id} initialization does not match the frame."
        )
    allocation = merged["latent_count"].to_numpy(dtype=int)
    assert_constraints(
        allocation,
        frame,
        label=(
            f"calibration_batch{batch_id}_rep{replicate_id}_"
            f"chain{chain_id}_initial"
        ),
    )
    return allocation


def chain_seed(batch_id: int, replicate_id: int, chain_id: int) -> int:
    if batch_id == 1:
        return 610000 + replicate_id * 100 + chain_id
    return 620000 + replicate_id * 100 + chain_id


def build_config(batch_id: int, replicate_id: int, chain_id: int) -> Path:
    scenario = scenario_for_replicate(replicate_id, batch_id=batch_id)
    output_root = replicate_root(batch_id, replicate_id)
    seeds = [chain_seed(batch_id, replicate_id, value) for value in range(1, 5)]
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
            "random_seeds": seeds,
            "move_weights": {
                "state_year_transfer": 0.10,
                "county_period_exploration": 0.25,
                "interval_path_transfer": 0.25,
                "swap_2x2": 0.30,
                "cycle_swap": 0.10,
            },
            "proposal_scale_multipliers": {
                "beta": 4.00,
                "state": 3.50,
                "year": 4.50,
                "log_sigma_state": 18.00,
                "log_sigma_year": 18.00,
                "log_kappa": 14.00,
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
            "hpc_root": str(output_root.relative_to(ROOT)).replace("\\", "/"),
        },
        "scientific_reports_v2": {
            "purpose": f"Multi-replicate truth-known calibration batch {batch_id}.",
            "batch": batch_id,
            "replicate": replicate_id,
            "scenario": scenario.scenario_id,
            "baseline_rate_per_100k": scenario.baseline_rate_per_100k,
            "truth_kappa": scenario.kappa,
            "not_for_empirical_inference": True,
        },
    }
    config_dir = output_root / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / f"chain_{chain_id:02d}.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def write_initial_checkpoint(
    frame: pd.DataFrame,
    batch_id: int,
    replicate_id: int,
    chain_id: int,
    allocation: np.ndarray,
) -> Path:
    output_root = replicate_root(batch_id, replicate_id)
    chain_dir = output_root / "chains" / f"chain_{chain_id:02d}"
    if chain_dir.exists():
        shutil.rmtree(chain_dir)
    checkpoint_dir = chain_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    design = make_design(frame)
    theta = initialize_theta(frame, allocation, design)
    current_lp = log_posterior_theta(
        allocation,
        theta,
        design,
        intercept_mean=crude_intercept_prior(frame),
    )
    rng = np.random.default_rng(chain_seed(batch_id, replicate_id, chain_id))
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
    save_chain_checkpoint(
        checkpoint_dir / "checkpoint_iter_000000000.npz",
        y=allocation,
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
    parser.add_argument("--batch-id", type=int, default=1, choices=(1, 2))
    parser.add_argument("--replicate-id", type=int, required=True)
    parser.add_argument("--chain-id", type=int, required=True, choices=range(1, 5))
    args = parser.parse_args()
    valid_replicates = valid_replicates_for_batch(args.batch_id)
    if args.replicate_id not in valid_replicates:
        parser.error(
            f"batch {args.batch_id} replicate must be one of {valid_replicates}"
        )

    frame = load_public_frame(args.batch_id, args.replicate_id)
    allocation = load_initial_allocation(
        frame,
        args.batch_id,
        args.replicate_id,
        args.chain_id,
    )
    checkpoint_dir = write_initial_checkpoint(
        frame,
        args.batch_id,
        args.replicate_id,
        args.chain_id,
        allocation,
    )
    config_path = build_config(args.batch_id, args.replicate_id, args.chain_id)
    output_root = replicate_root(args.batch_id, args.replicate_id)
    status = run_mcmc_chain_hpc(
        frame,
        config_path=config_path,
        mode="production",
        chain_id=args.chain_id,
        seed=chain_seed(args.batch_id, args.replicate_id, args.chain_id),
        out_dir=output_root,
        checkpoint_dir=checkpoint_dir,
        resume=True,
        force=True,
        max_runtime_minutes=80,
        stop_before_time_limit_minutes=8,
    )
    expected_draws = (N_ITER - BURN_IN) // THIN
    if status.get("status") != "completed":
        raise SystemExit(
            f"Calibration batch {args.batch_id} replicate {args.replicate_id} chain "
            f"{args.chain_id} did not complete: {status}"
        )
    if int(status.get("iteration", -1)) != N_ITER:
        raise SystemExit(
            f"Calibration batch {args.batch_id} replicate {args.replicate_id} chain "
            f"{args.chain_id} stopped at {status.get('iteration')}; expected {N_ITER}."
        )
    if int(status.get("saved_draws", -1)) != expected_draws:
        raise SystemExit(
            f"Calibration batch {args.batch_id} replicate {args.replicate_id} chain "
            f"{args.chain_id} retained {status.get('saved_draws')} draws; "
            f"expected {expected_draws}."
        )
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
