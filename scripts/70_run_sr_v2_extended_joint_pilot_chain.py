from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.sampler import run_mcmc_chain_hpc  # noqa: E402


SOURCE_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "joint_pilot"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "extended_joint_pilot"
EXTENSION_ITERATIONS = 8500


def build_config(chain_id: int) -> Path:
    tuning_path = SOURCE_ROOT / "recommended_joint_tuning.yaml"
    if not tuning_path.exists():
        raise FileNotFoundError(f"Missing joint-pilot tuning evidence: {tuning_path}")
    tuning = yaml.safe_load(tuning_path.read_text(encoding="utf-8")) or {}
    payload = {
        "run": {
            "n_chains": 4,
            "n_iter": 1500,
            "burn_in": 500,
            "thin": 10,
            "extension_n_iter": EXTENSION_ITERATIONS,
            "extension_burn_in": 0,
            "extension_thin": 10,
            "count_move_sweeps_per_iter": 0.02,
            "max_count_proposals_per_iter": 200,
            "blocked_refresh_frequency": 25,
            "blocked_refresh_attempts": 8,
            "checkpoint_every": 500,
            "random_seeds": [28291, 28292, 28293, 28294],
            "move_weights": tuning["move_weights"],
            "proposal_scale_multipliers": tuning["proposal_scale_multipliers"],
            "max_cycle_half_length": int(tuning.get("max_cycle_half_length", 6)),
            "target_acceptance_parameter_blocks": [0.20, 0.45],
        },
        "model": {
            "outcome": "MCOD G40/G41, 2019-2024",
            "rurality_reference": "metro_large",
            "svi_reference": "Q1_lowest",
        },
        "outputs": {
            "hpc_root": str(OUTPUT_ROOT.relative_to(ROOT)).replace("\\", "/"),
        },
        "scientific_reports_v2": {
            "purpose": "Extended corrected tuning pilot resumed from the four-chain short joint pilot.",
            "source_chain_root": str(SOURCE_ROOT.relative_to(ROOT)).replace("\\", "/"),
            "source_draws_per_chain": 100,
            "analysis_excludes_first_combined_draws_per_chain": 300,
            "not_for_inference": True,
        },
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    config_path = OUTPUT_ROOT / f"extended_joint_pilot_chain_{chain_id:02d}_config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def prepare_chain(chain_id: int) -> Path:
    source = SOURCE_ROOT / "chains" / f"chain_{chain_id:02d}"
    target = OUTPUT_ROOT / "chains" / f"chain_{chain_id:02d}"
    if not source.exists():
        raise FileNotFoundError(f"Missing source joint-pilot chain: {source}")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-id", type=int, required=True, choices=range(1, 5))
    args = parser.parse_args()

    chain_dir = prepare_chain(args.chain_id)
    config_path = build_config(args.chain_id)
    frame = load_model_frame()
    status = run_mcmc_chain_hpc(
        frame,
        config_path=config_path,
        mode="extend",
        chain_id=args.chain_id,
        out_dir=OUTPUT_ROOT,
        checkpoint_dir=chain_dir / "checkpoints",
        resume=True,
        force=True,
        max_runtime_minutes=80,
        stop_before_time_limit_minutes=8,
    )
    expected_iteration = 1500 + EXTENSION_ITERATIONS
    if status.get("status") != "completed":
        raise SystemExit(f"Extended joint-pilot chain {args.chain_id} did not complete: {status}")
    if int(status.get("iteration", -1)) != expected_iteration:
        raise SystemExit(
            f"Extended chain {args.chain_id} stopped at {status.get('iteration')}; "
            f"expected {expected_iteration}."
        )
    if int(status.get("saved_draws", -1)) != 950:
        raise SystemExit(
            f"Extended chain {args.chain_id} retained {status.get('saved_draws')} draws; expected 950."
        )
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
