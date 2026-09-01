from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.model import prior_specification_from_mapping  # noqa: E402


PRODUCTION_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"
SENSITIVITY_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "prior_sensitivity"
REGISTRY_PATH = ROOT / "config" / "scientific_reports_v2_robustness_registry.yaml"
PROFILES = {
    "broader": {
        "chain_seeds": [68291, 68292, 68293, 68294],
        "initialization_seeds": [67291, 67292, 67293, 67294],
    },
    "regularizing": {
        "chain_seeds": [69291, 69292, 69293, 69294],
        "initialization_seeds": [67391, 67392, 67393, 67394],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    gate_path = PRODUCTION_ROOT / "production_gate.json"
    gate = load_json(gate_path)
    if not gate.get("passed", False):
        raise SystemExit(
            "Corrected production gate did not pass; prior sensitivity is blocked."
        )
    production_config_path = PRODUCTION_ROOT / "config" / "sr_v2_production.yaml"
    if not production_config_path.exists():
        raise FileNotFoundError(production_config_path)
    production_config = yaml.safe_load(
        production_config_path.read_text(encoding="utf-8")
    )
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    prior_profiles = registry["prior_profiles"]

    manifests: list[dict[str, object]] = []
    for profile_name, seeds in PROFILES.items():
        profile_root = SENSITIVITY_ROOT / profile_name
        existing_chains = profile_root / "chains"
        if (
            existing_chains.exists()
            and any(existing_chains.glob("chain_*"))
            and not args.force
        ):
            raise SystemExit(
                f"Prior-sensitivity outputs already exist for {profile_name}; "
                "refusing to overwrite without --force."
            )
        profile = prior_specification_from_mapping(
            prior_profiles[profile_name],
            name=profile_name,
        )
        run = dict(production_config["run"])
        run.update(
            {
                "n_chains": 4,
                "n_iter": 180000,
                "burn_in": 45000,
                "thin": 30,
                "random_seeds": seeds["chain_seeds"],
                "initialization_seeds": seeds["initialization_seeds"],
                "max_extensions": 3,
                "extension_n_iter": 90000,
                "extension_burn_in": 0,
                "extension_thin": 30,
            }
        )
        model = dict(production_config.get("model", {}))
        model.update(
            {
                "prior_profile": profile_name,
                "intercept_prior_sd": profile.intercept_sd,
                "fixed_effect_prior_sd": profile.nonintercept_beta_sd,
                "sigma_state_prior_sd": profile.state_scale_halfnormal_sd,
                "sigma_year_prior_sd": profile.year_scale_halfnormal_sd,
                "log_kappa_prior_mean": profile.log_kappa_mean,
                "log_kappa_prior_sd": profile.log_kappa_sd,
            }
        )
        payload = {
            "run": run,
            "model": model,
            "diagnostics": {
                "rhat_max_all": 1.05,
                "ess_bulk_min_all": 100,
                "ess_tail_min_all": 100,
                "rhat_max_primary": 1.03,
                "ess_bulk_min_primary": 400,
                "ess_tail_min_primary": 400,
            },
            "outputs": {
                "root": str(profile_root.relative_to(ROOT)).replace("\\", "/"),
            },
            "scientific_reports_v2": {
                "analysis": "prior_sensitivity",
                "profile": profile_name,
                "source_production_gate_sha256": sha256(gate_path),
                "source_production_config_sha256": sha256(
                    production_config_path
                ),
                "registry_sha256": sha256(REGISTRY_PATH),
                "not_primary_inference": True,
                "interpretation_boundary": (
                    "Prior sensitivity only. Results supplement the passed corrected primary analysis and must not replace its prespecified estimand."
                ),
            },
        }
        config_dir = profile_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "prior_sensitivity.yaml"
        config_path.write_text(
            yaml.safe_dump(payload, sort_keys=False),
            encoding="utf-8",
        )
        manifest = {
            "profile": profile_name,
            "config": str(config_path.relative_to(ROOT)).replace("\\", "/"),
            "config_sha256": sha256(config_path),
            "prior": profile.to_dict(),
            "chains": 4,
            "iterations_per_chain": 180000,
            "burn_in": 45000,
            "thin": 30,
            "expected_draws_per_chain": 4500,
            "chain_seeds": seeds["chain_seeds"],
            "initialization_seeds": seeds["initialization_seeds"],
            "status": "prepared_not_run",
        }
        (profile_root / "preparation_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifests.append(manifest)

    batch_manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_production_gate": str(gate_path.relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "profiles": manifests,
        "status": "prepared_not_run",
        "interpretation_boundary": (
            "This preparation does not execute sensitivity chains or alter the corrected primary result."
        ),
    }
    SENSITIVITY_ROOT.mkdir(parents=True, exist_ok=True)
    (SENSITIVITY_ROOT / "preparation_manifest.json").write_text(
        json.dumps(batch_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(batch_manifest, sort_keys=True))


if __name__ == "__main__":
    main()
