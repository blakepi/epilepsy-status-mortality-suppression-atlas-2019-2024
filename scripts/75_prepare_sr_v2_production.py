from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"
EXTENDED_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "extended_joint_pilot"
LATENT_TUNING = ROOT / "outputs" / "scientific_reports_v2" / "latent_tuning" / "selected_latent_tuning.yaml"
HPC_CONFIG_DIR = ROOT / "hpc" / "wahab" / "configs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    extended_summary_path = EXTENDED_ROOT / "extended_joint_summary.json"
    recommended_path = EXTENDED_ROOT / "recommended_production_tuning.yaml"
    if not extended_summary_path.exists() or not recommended_path.exists():
        raise SystemExit("Extended corrected joint-pilot evidence is not available.")
    extended = json.loads(extended_summary_path.read_text(encoding="utf-8"))
    if not extended.get("pilot_pass", False):
        raise SystemExit("Extended corrected joint pilot did not pass; production is blocked.")
    if not LATENT_TUNING.exists():
        raise SystemExit(f"Missing fixed-theta latent tuning: {LATENT_TUNING}")

    chain_root = OUTPUT_ROOT / "chains"
    if chain_root.exists() and any(chain_root.glob("chain_*")) and not args.force:
        raise SystemExit(
            "Scientific Reports v2 production chain outputs already exist. "
            "Refusing to overwrite without --force."
        )

    recommended = yaml.safe_load(recommended_path.read_text(encoding="utf-8")) or {}
    latent = yaml.safe_load(LATENT_TUNING.read_text(encoding="utf-8")) or {}
    required = {"proposal_scale_multipliers", "move_weights", "max_cycle_half_length"}
    missing = required - set(recommended)
    if missing:
        raise SystemExit(f"Extended tuning is missing required fields: {sorted(missing)}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    config_dir = OUTPUT_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    HPC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    frozen_tuning = {
        "proposal_scale_multipliers": recommended["proposal_scale_multipliers"],
        "move_weights": recommended["move_weights"],
        "max_cycle_half_length": int(recommended["max_cycle_half_length"]),
        "source_extended_joint_summary_sha256": sha256(extended_summary_path),
        "source_extended_joint_tuning_sha256": sha256(recommended_path),
        "source_fixed_theta_tuning_sha256": sha256(LATENT_TUNING),
        "fixed_theta_selected_profile": latent.get("selected_profile"),
    }
    frozen_tuning_path = config_dir / "frozen_production_tuning.yaml"
    hpc_tuning_path = HPC_CONFIG_DIR / "sr_v2_frozen_production_tuning.yaml"
    tuning_text = yaml.safe_dump(frozen_tuning, sort_keys=False)
    frozen_tuning_path.write_text(tuning_text, encoding="utf-8")
    hpc_tuning_path.write_text(tuning_text, encoding="utf-8")

    seeds = list(range(58291, 58299))
    initialization_seeds = list(range(57291, 57299))
    config = {
        "run": {
            "n_chains": 8,
            "n_iter": 300000,
            "burn_in": 75000,
            "thin": 50,
            "count_move_sweeps_per_iter": 0.05,
            "max_count_proposals_per_iter": 300,
            "blocked_refresh_frequency": 25,
            "blocked_refresh_attempts": 8,
            "checkpoint_every": 500,
            "random_seeds": seeds,
            "initialization_seeds": initialization_seeds,
            "move_weights": frozen_tuning["move_weights"],
            "proposal_scale_multipliers": frozen_tuning["proposal_scale_multipliers"],
            "max_cycle_half_length": frozen_tuning["max_cycle_half_length"],
            "max_extensions": 4,
            "extension_n_iter": 150000,
            "extension_burn_in": 0,
            "extension_thin": 50,
            "target_acceptance_parameter_blocks": [0.20, 0.45],
            "validate_every_saved_latent_draw": True,
        },
        "model": {
            "outcome": "MCOD G40/G41, 2019-2024",
            "rurality_reference": "metro_large",
            "svi_reference": "Q1_lowest",
            "fixed_effect_prior_sd": 1.5,
            "intercept_prior_sd": 5.0,
            "sigma_state_prior_sd": 1.0,
            "sigma_year_prior_sd": 1.0,
            "log_kappa_prior_mean": 2.302585092994046,
            "log_kappa_prior_sd": 1.5,
            "centered_random_effect_dimension_correction": True,
        },
        "diagnostics": {
            "expected_parameters": 69,
            "rhat_max_all": 1.01,
            "ess_bulk_min_all": 400,
            "ess_tail_min_all": 400,
            "ess_bulk_min_primary": 1000,
            "ess_tail_min_primary": 1000,
            "latent_summary_rhat_max": 1.01,
            "latent_summary_ess_bulk_min": 400,
            "latent_summary_ess_tail_min": 400,
        },
        "outputs": {
            "root": "outputs/scientific_reports_v2/production_8chain",
        },
        "scientific_reports_v2": {
            "frozen_baseline_tag": "v1.1.1",
            "frozen_baseline_commit": "50b468d212616ee80be55045dedf8a696db14df5",
            "branch": "scientific-reports-v2",
            "preparation_commit": git_value("rev-parse", "HEAD"),
            "interpretation_boundary": (
                "No corrected empirical estimate is authorized until the eight-chain "
                "production gate passes and downstream summaries are frozen."
            ),
        },
    }
    config_text = yaml.safe_dump(config, sort_keys=False)
    config_path = config_dir / "sr_v2_production.yaml"
    hpc_config_path = HPC_CONFIG_DIR / "sr_v2_production.yaml"
    config_path.write_text(config_text, encoding="utf-8")
    hpc_config_path.write_text(config_text, encoding="utf-8")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_branch": git_value("branch", "--show-current"),
        "frozen_baseline_tag": "v1.1.1",
        "frozen_baseline_commit": "50b468d212616ee80be55045dedf8a696db14df5",
        "config_path": str(config_path.relative_to(ROOT)).replace("\\", "/"),
        "config_sha256": sha256(config_path),
        "hpc_config_path": str(hpc_config_path.relative_to(ROOT)).replace("\\", "/"),
        "hpc_config_sha256": sha256(hpc_config_path),
        "frozen_tuning_path": str(frozen_tuning_path.relative_to(ROOT)).replace("\\", "/"),
        "frozen_tuning_sha256": sha256(frozen_tuning_path),
        "hpc_tuning_path": str(hpc_tuning_path.relative_to(ROOT)).replace("\\", "/"),
        "hpc_tuning_sha256": sha256(hpc_tuning_path),
        "extended_joint_summary_sha256": sha256(extended_summary_path),
        "extended_joint_pilot_pass": True,
        "n_chains": 8,
        "iterations_per_chain": 300000,
        "burn_in": 75000,
        "thin": 50,
        "expected_draws_per_chain": 4500,
        "random_seeds": seeds,
        "initialization_seeds": initialization_seeds,
        "status": "prepared_not_run",
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path = OUTPUT_ROOT / "production_preparation_manifest.json"
    hpc_manifest_path = HPC_CONFIG_DIR / "sr_v2_production_preparation_manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    hpc_manifest_path.write_text(manifest_text, encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
