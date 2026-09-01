from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.sampler import run_mcmc_chain_hpc  # noqa: E402


DEFAULT_MOVE_WEIGHTS = {
    "state_year_transfer": 0.05,
    "county_period_exploration": 0.30,
    "interval_path_transfer": 0.25,
    "swap_2x2": 0.30,
    "cycle_swap": 0.10,
}


def selected_move_settings() -> tuple[dict[str, float], int, str]:
    path = ROOT / "outputs" / "scientific_reports_v2" / "latent_tuning" / "selected_latent_tuning.yaml"
    if not path.exists():
        return DEFAULT_MOVE_WEIGHTS.copy(), 6, "default_balanced_circuit_heatbath"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    weights = payload.get("move_weights") or DEFAULT_MOVE_WEIGHTS
    return (
        {key: float(value) for key, value in weights.items()},
        int(payload.get("max_cycle_half_length", 6)),
        str(payload.get("selected_profile", "selected_profile")),
    )


def build_config(chain_id: int, output_root: Path) -> Path:
    weights, max_cycle_half_length, profile = selected_move_settings()
    config = {
        "run": {
            "n_chains": 4,
            "n_iter": 1500,
            "burn_in": 500,
            "thin": 10,
            "count_move_sweeps_per_iter": 0.02,
            "max_count_proposals_per_iter": 200,
            "blocked_refresh_frequency": 25,
            "blocked_refresh_attempts": 8,
            "checkpoint_every": 500,
            "random_seeds": [28291, 28292, 28293, 28294],
            "max_extensions": 0,
            "move_weights": weights,
            "max_cycle_half_length": max_cycle_half_length,
            "proposal_scale_multipliers": {
                "beta": 0.60,
                "state": 1.30,
                "year": 1.50,
                "log_sigma_state": 4.00,
                "log_sigma_year": 6.00,
                "log_kappa": 2.40,
            },
            "latent_tuning_profile": profile,
            "pilot_only": True,
        },
        "model": {
            "outcome": "MCOD G40/G41, 2019-2024",
            "rurality_reference": "metro_large",
            "svi_reference": "Q1_lowest",
            "target_density": "Scientific Reports v2 corrected centered-prior target",
        },
        "outputs": {"hpc_root": str(output_root)},
    }
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / f"joint_pilot_chain_{chain_id:02d}_config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-id", type=int, required=True, choices=range(1, 5))
    args = parser.parse_args()

    output_root = ROOT / "outputs" / "scientific_reports_v2" / "joint_pilot"
    config_path = build_config(args.chain_id, output_root)
    frame = load_model_frame()
    status = run_mcmc_chain_hpc(
        frame,
        config_path=config_path,
        mode="production",
        chain_id=args.chain_id,
        seed=28290 + args.chain_id,
        out_dir=output_root,
        checkpoint_dir=output_root / "chains" / f"chain_{args.chain_id:02d}" / "checkpoints",
        checkpoint_every=500,
        resume=False,
        force=True,
        model_name="primary",
    )
    if status.get("status") != "completed":
        raise SystemExit(f"Joint pilot chain {args.chain_id} did not complete: {status}")
    print(json.dumps(status, sort_keys=True))


if __name__ == "__main__":
    main()
