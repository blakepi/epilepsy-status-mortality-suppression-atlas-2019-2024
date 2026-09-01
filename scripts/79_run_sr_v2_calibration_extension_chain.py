from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.sampler import run_mcmc_chain_hpc  # noqa: E402


SOURCE_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_pilot" / "replicate_001"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_pilot" / "replicate_001_extended"
DESIGN_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_design_smoke"
EXTENSION_ITERATIONS = 20000


def load_public_frame() -> pd.DataFrame:
    frame = pd.read_parquet(DESIGN_ROOT / "public_suppressed_frame.parquet")
    summary = json.loads((DESIGN_ROOT / "calibration_design_summary.json").read_text(encoding="utf-8"))
    frame.attrs["grand_total"] = int(summary["grand_total"])
    return frame


def prepare_chain(chain_id: int) -> Path:
    source = SOURCE_ROOT / "chains" / f"chain_{chain_id:02d}"
    target = OUTPUT_ROOT / "chains" / f"chain_{chain_id:02d}"
    if not source.exists():
        raise FileNotFoundError(f"Missing source calibration chain: {source}")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    acceptance = target / "acceptance_rates.csv"
    if acceptance.exists():
        shutil.copy2(acceptance, target / "source_acceptance_rates.csv")
    return target


def build_config(chain_id: int) -> Path:
    payload = {
        "run": {
            "n_chains": 4,
            "n_iter": 8000,
            "burn_in": 2000,
            "thin": 10,
            "extension_n_iter": EXTENSION_ITERATIONS,
            "extension_burn_in": 0,
            "extension_thin": 10,
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
            "hpc_root": str(OUTPUT_ROOT.relative_to(ROOT)).replace("\\", "/"),
        },
        "scientific_reports_v2": {
            "purpose": "Tuned extension of the end-to-end truth-known calibration pilot.",
            "replicate": 1,
            "source_iterations": 8000,
            "extension_iterations": EXTENSION_ITERATIONS,
            "not_for_empirical_inference": True,
        },
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_ROOT / f"calibration_extension_chain_{chain_id:02d}_config.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-id", type=int, required=True, choices=range(1, 5))
    args = parser.parse_args()

    chain_dir = prepare_chain(args.chain_id)
    config_path = build_config(args.chain_id)
    frame = load_public_frame()
    status = run_mcmc_chain_hpc(
        frame,
        config_path=config_path,
        mode="extend",
        chain_id=args.chain_id,
        seed=142000 + args.chain_id,
        out_dir=OUTPUT_ROOT,
        checkpoint_dir=chain_dir / "checkpoints",
        resume=True,
        force=True,
        max_runtime_minutes=80,
        stop_before_time_limit_minutes=8,
    )
    expected_iteration = 8000 + EXTENSION_ITERATIONS
    expected_draws = 600 + EXTENSION_ITERATIONS // 10
    if status.get("status") != "completed":
        raise SystemExit(f"Calibration extension chain {args.chain_id} did not complete: {status}")
    if int(status.get("iteration", -1)) != expected_iteration:
        raise SystemExit(
            f"Calibration extension chain {args.chain_id} stopped at {status.get('iteration')}; "
            f"expected {expected_iteration}."
        )
    if int(status.get("saved_draws", -1)) != expected_draws:
        raise SystemExit(
            f"Calibration extension chain {args.chain_id} retained {status.get('saved_draws')} draws; "
            f"expected {expected_draws}."
        )
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
