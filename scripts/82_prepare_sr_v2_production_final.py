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
VALIDATION_ROOT = ROOT / "outputs" / "scientific_reports_v2"
EXTENDED_REAL_ROOT = VALIDATION_ROOT / "extended_joint_pilot"
CALIBRATION_EXTENSION_ROOT = (
    VALIDATION_ROOT / "calibration_pilot" / "replicate_001_extended"
)
LATENT_TUNING = VALIDATION_ROOT / "latent_tuning" / "selected_latent_tuning.yaml"
HPC_CONFIG_DIR = ROOT / "hpc" / "wahab" / "configs"
BASELINE_COMMIT = "50b468d212616ee80be55045dedf8a696db14df5"
EXPECTED_BRANCH = "scientific-reports-v2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required Scientific Reports v2 gate evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def require_gate(path: Path, key: str, label: str) -> dict:
    payload = load_json(path)
    if not bool(payload.get(key, False)):
        raise SystemExit(f"{label} did not pass; production is blocked: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    current_branch = git_value("branch", "--show-current")
    if current_branch != EXPECTED_BRANCH:
        raise SystemExit(
            f"Production preparation requires branch {EXPECTED_BRANCH!r}; "
            f"current branch is {current_branch!r}."
        )
    baseline_tag_commit = git_value("rev-list", "-n", "1", "v1.1.1")
    if baseline_tag_commit != BASELINE_COMMIT:
        raise SystemExit(
            f"v1.1.1 resolves to {baseline_tag_commit}, not frozen baseline {BASELINE_COMMIT}."
        )

    exact_path = VALIDATION_ROOT / "exact_kernel_validation" / "exact_kernel_validation.json"
    random_exact_path = (
        VALIDATION_ROOT
        / "random_exact_validation"
        / "random_exact_validation_summary.json"
    )
    geometry_path = VALIDATION_ROOT / "constraint_geometry" / "constraint_geometry.json"
    extended_real_path = EXTENDED_REAL_ROOT / "extended_joint_summary.json"
    calibration_design_path = (
        VALIDATION_ROOT
        / "calibration_design_smoke"
        / "calibration_design_summary.json"
    )
    calibration_extension_path = (
        CALIBRATION_EXTENSION_ROOT / "calibration_extension_summary.json"
    )

    exact = require_gate(exact_path, "pass", "Exact finite-state kernel gate")
    random_exact = require_gate(
        random_exact_path,
        "pass",
        "Randomized exact finite-state kernel gate",
    )
    extended_real = require_gate(
        extended_real_path,
        "pilot_pass",
        "Extended corrected real-data pilot",
    )
    calibration_design = require_gate(
        calibration_design_path,
        "design_pass",
        "Truth-known calibration design",
    )
    calibration_extension = require_gate(
        calibration_extension_path,
        "computational_gate_pass",
        "Tuned truth-known calibration extension",
    )
    geometry = load_json(geometry_path)
    if not (
        int(geometry.get("latent_variables", -1)) == 9695
        and int(geometry.get("independent_equalities", -1)) == 1256
        and int(geometry.get("equality_nullity", -1)) == 8439
    ):
        raise SystemExit("Constraint-geometry evidence does not match the audited v2 system.")
    if not LATENT_TUNING.exists():
        raise SystemExit(f"Missing fixed-theta latent tuning: {LATENT_TUNING}")

    recommended_path = EXTENDED_REAL_ROOT / "recommended_production_tuning.yaml"
    if not recommended_path.exists():
        raise SystemExit(f"Missing recommended production tuning: {recommended_path}")
    recommended = yaml.safe_load(recommended_path.read_text(encoding="utf-8")) or {}
    latent = yaml.safe_load(LATENT_TUNING.read_text(encoding="utf-8")) or {}
    required = {"proposal_scale_multipliers", "move_weights", "max_cycle_half_length"}
    missing = required - set(recommended)
    if missing:
        raise SystemExit(f"Extended real-data tuning is missing fields: {sorted(missing)}")

    chain_root = OUTPUT_ROOT / "chains"
    if chain_root.exists() and any(chain_root.glob("chain_*")) and not args.force:
        raise SystemExit(
            "Scientific Reports v2 production outputs already exist. "
            "Refusing to overwrite without --force."
        )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_config_dir = OUTPUT_ROOT / "config"
    output_config_dir.mkdir(parents=True, exist_ok=True)
    HPC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    evidence_paths = {
        "exact_kernel": exact_path,
        "randomized_exact_kernel": random_exact_path,
        "constraint_geometry": geometry_path,
        "extended_real_pilot": extended_real_path,
        "calibration_design": calibration_design_path,
        "calibration_extension": calibration_extension_path,
        "fixed_theta_tuning": LATENT_TUNING,
        "recommended_production_tuning": recommended_path,
    }
    evidence_hashes = {name: sha256(path) for name, path in evidence_paths.items()}

    frozen_tuning = {
        "proposal_scale_multipliers": recommended["proposal_scale_multipliers"],
        "move_weights": recommended["move_weights"],
        "max_cycle_half_length": int(recommended["max_cycle_half_length"]),
        "fixed_theta_selected_profile": latent.get("selected_profile"),
        "source_evidence_sha256": evidence_hashes,
    }
    tuning_text = yaml.safe_dump(frozen_tuning, sort_keys=False)
    output_tuning_path = output_config_dir / "frozen_production_tuning.yaml"
    hpc_tuning_path = HPC_CONFIG_DIR / "sr_v2_frozen_production_tuning.yaml"
    output_tuning_path.write_text(tuning_text, encoding="utf-8")
    hpc_tuning_path.write_text(tuning_text, encoding="utf-8")

    chain_seeds = list(range(58291, 58299))
    initialization_seeds = list(range(57291, 57299))
    preparation_commit = git_value("rev-parse", "HEAD")
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
            "random_seeds": chain_seeds,
            "initialization_seeds": initialization_seeds,
            "move_weights": frozen_tuning["move_weights"],
            "proposal_scale_multipliers": frozen_tuning[
                "proposal_scale_multipliers"
            ],
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
            "frozen_baseline_commit": BASELINE_COMMIT,
            "branch": EXPECTED_BRANCH,
            "preparation_commit": preparation_commit,
            "exact_kernel_gate_pass": bool(exact["pass"]),
            "randomized_exact_kernel_gate_pass": bool(random_exact["pass"]),
            "extended_real_pilot_pass": bool(extended_real["pilot_pass"]),
            "calibration_design_pass": bool(calibration_design["design_pass"]),
            "calibration_extension_computational_gate_pass": bool(
                calibration_extension["computational_gate_pass"]
            ),
            "constraint_geometry": {
                "latent_variables": 9695,
                "independent_equalities": 1256,
                "equality_nullity": 8439,
            },
            "interpretation_boundary": (
                "No corrected empirical estimate is authorized until the eight-chain "
                "production gate passes and downstream summaries are frozen."
            ),
        },
    }
    config_text = yaml.safe_dump(config, sort_keys=False)
    output_config_path = output_config_dir / "sr_v2_production.yaml"
    hpc_config_path = HPC_CONFIG_DIR / "sr_v2_production.yaml"
    output_config_path.write_text(config_text, encoding="utf-8")
    hpc_config_path.write_text(config_text, encoding="utf-8")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": preparation_commit,
        "git_branch": current_branch,
        "frozen_baseline_tag": "v1.1.1",
        "frozen_baseline_commit": BASELINE_COMMIT,
        "output_config_path": str(output_config_path.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "output_config_sha256": sha256(output_config_path),
        "hpc_config_path": str(hpc_config_path.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "hpc_config_sha256": sha256(hpc_config_path),
        "frozen_tuning_sha256": sha256(output_tuning_path),
        "evidence_sha256": evidence_hashes,
        "n_chains": 8,
        "iterations_per_chain": 300000,
        "burn_in": 75000,
        "thin": 50,
        "expected_draws_per_chain": 4500,
        "random_seeds": chain_seeds,
        "initialization_seeds": initialization_seeds,
        "status": "prepared_not_run",
        "production_launched": False,
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    output_manifest_path = OUTPUT_ROOT / "production_preparation_manifest.json"
    hpc_manifest_path = HPC_CONFIG_DIR / "sr_v2_production_preparation_manifest.json"
    output_manifest_path.write_text(manifest_text, encoding="utf-8")
    hpc_manifest_path.write_text(manifest_text, encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
