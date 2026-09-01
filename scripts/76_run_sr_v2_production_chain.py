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

from bayes_constrained.constraints import assert_constraints, solve_feasible_allocation  # noqa: E402
from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.model import (  # noqa: E402
    crude_intercept_prior,
    initialize_theta,
    log_posterior_theta,
    make_design,
)
from bayes_constrained.sampler import (  # noqa: E402
    latest_valid_checkpoint,
    run_mcmc_chain_hpc,
    save_chain_checkpoint,
)


OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"
CONFIG_PATH = OUTPUT_ROOT / "config" / "sr_v2_production.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Production config is missing: {CONFIG_PATH}. Run scripts/75_prepare_sr_v2_production.py first."
        )
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def create_initial_checkpoint(frame: pd.DataFrame, config: dict, chain_id: int) -> Path:
    chain_dir = OUTPUT_ROOT / "chains" / f"chain_{chain_id:02d}"
    checkpoint_dir = chain_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    initialization_seed = int(config["run"]["initialization_seeds"][chain_id - 1])
    y = solve_feasible_allocation(
        frame,
        seed=initialization_seed,
        objective="random",
        time_limit_seconds=900,
    )
    assert_constraints(y, frame, label=f"sr_v2_chain{chain_id}_initial")
    initialization_dir = OUTPUT_ROOT / "initializations"
    initialization_dir.mkdir(parents=True, exist_ok=True)
    initial_frame = frame[["county_fips", "year", "q002_count_status"]].copy()
    initial_frame["latent_count"] = y
    initial_frame.to_parquet(
        initialization_dir / f"initial_allocation_chain_{chain_id:02d}.parquet",
        index=False,
    )

    design = make_design(frame)
    theta = initialize_theta(frame, y, design)
    current_lp = log_posterior_theta(
        y,
        theta,
        design,
        intercept_mean=crude_intercept_prior(frame),
    )
    seed = int(config["run"]["random_seeds"][chain_id - 1])
    rng = np.random.default_rng(seed)
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
    parser.add_argument("--chain-id", type=int, required=True, choices=range(1, 9))
    parser.add_argument("--max-runtime-minutes", type=int, default=4260)
    parser.add_argument("--stop-before-time-limit-minutes", type=int, default=15)
    parser.add_argument("--force-restart", action="store_true")
    args = parser.parse_args()

    config = load_config()
    chain_dir = OUTPUT_ROOT / "chains" / f"chain_{args.chain_id:02d}"
    status_path = chain_dir / "chain_status.json"
    if status_path.exists() and not args.force_restart:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") == "completed":
            print(json.dumps(status, sort_keys=True))
            return
    if args.force_restart and chain_dir.exists():
        shutil.rmtree(chain_dir)

    frame = load_model_frame()
    checkpoint_dir = chain_dir / "checkpoints"
    if latest_valid_checkpoint(checkpoint_dir) is None:
        checkpoint_dir = create_initial_checkpoint(frame, config, args.chain_id)

    seed = int(config["run"]["random_seeds"][args.chain_id - 1])
    status = run_mcmc_chain_hpc(
        frame,
        config_path=CONFIG_PATH,
        mode="production",
        chain_id=args.chain_id,
        array_task_id=args.chain_id,
        seed=seed,
        out_dir=OUTPUT_ROOT,
        checkpoint_dir=checkpoint_dir,
        checkpoint_every=int(config["run"]["checkpoint_every"]),
        resume=True,
        force=True,
        max_runtime_minutes=args.max_runtime_minutes,
        stop_before_time_limit_minutes=args.stop_before_time_limit_minutes,
    )
    if status.get("status") not in {"completed", "checkpointed"}:
        raise SystemExit(f"Scientific Reports v2 chain {args.chain_id} failed: {status}")
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
