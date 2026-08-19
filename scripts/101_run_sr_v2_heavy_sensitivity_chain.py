from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.model import prior_specification_from_mapping, use_prior_specification  # noqa: E402
from bayes_constrained.sampler import run_mcmc_chain_hpc  # noqa: E402
from bayes_constrained.sensitivity import (  # noqa: E402
    RUN_ID,
    artifact_inventory,
    atomic_json,
    completed_chain_is_reusable,
    load_execution_spec,
    sha256_file,
    verify_hash_inventory,
    verify_manifest_sidecar,
)


CONFIG_PATH = ROOT / "config" / "sr_v2_heavy_sensitivity_execution.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--array-index", type=int, choices=range(1, 25), required=True)
    return parser


def _profile_record(manifest: dict, profile_id: str) -> dict:
    rows = [row for row in manifest.get("profiles", []) if row.get("profile", {}).get("id") == profile_id]
    if len(rows) != 1:
        raise ValueError(f"Prepared manifest does not contain exactly one {profile_id} profile")
    return rows[0]


def _chain_record(profile_record: dict, array_index: int) -> dict:
    rows = [row for row in profile_record.get("chains", []) if int(row.get("array_index", -1)) == array_index]
    if len(rows) != 1:
        raise ValueError(f"Prepared manifest does not contain exactly one array index {array_index}")
    return rows[0]


def _verify_resume_status(chain_dir: Path, status: dict, *, run_id: str, array_index: int, fingerprint: str) -> None:
    expected = {"run_id": run_id, "array_index": array_index, "profile_fingerprint": fingerprint}
    changed = {key: (value, status.get(key)) for key, value in expected.items() if status.get(key) != value}
    if changed:
        raise ValueError(f"Refusing cross-target checkpoint/status resume: {changed}")
    inventory = status.get("artifact_sha256", {})
    if inventory:
        verify_hash_inventory(chain_dir, inventory)
    checkpoint = status.get("latest_checkpoint")
    checkpoint_hash = status.get("latest_checkpoint_sha256")
    if checkpoint or checkpoint_hash:
        if not isinstance(checkpoint, str) or not isinstance(checkpoint_hash, str):
            raise ValueError("Checkpoint path/hash evidence is incomplete")
        actual = sha256_file(chain_dir / checkpoint)
        if actual != checkpoint_hash:
            raise ValueError(f"Checkpoint SHA-256 mismatch: expected {checkpoint_hash}, found {actual}")
        latest_on_disk = max(chain_dir.glob("checkpoints/checkpoint_iter_*.npz"), default=None)
        if latest_on_disk is None or latest_on_disk.relative_to(chain_dir).as_posix() != checkpoint:
            raise ValueError("Latest on-disk checkpoint is not the fingerprint-verified resume checkpoint")


def _validate_completed_outputs(chain_dir: Path, expected_schema: list[str], expected_draws: int) -> tuple[int, int]:
    draws = pd.read_parquet(chain_dir / "draws_params.parquet")
    if list(draws.columns) != ["chain", "draw", "iteration", "parameter", "value"]:
        raise ValueError(f"Unexpected parameter-draw columns: {list(draws.columns)}")
    actual_schema = draws["parameter"].drop_duplicates().astype(str).tolist()
    if actual_schema != expected_schema:
        raise ValueError("Completed chain parameter schema does not match target fingerprint")
    counts = draws.groupby("parameter", sort=False)["draw"].nunique()
    if len(counts) != len(expected_schema) or not counts.eq(expected_draws).all():
        raise ValueError("Completed chain does not contain exactly the expected retained draws")
    validation = pd.read_csv(chain_dir / "latent_validation.csv")
    if "passed" not in validation or not validation["passed"].astype(bool).all():
        raise ValueError("Completed chain contains count-constraint failures")
    return int(len(draws)), int((~validation["passed"].astype(bool)).sum())


def run_chain(run_id: str, array_index: int) -> dict:
    spec = load_execution_spec(CONFIG_PATH)
    if run_id != RUN_ID or run_id != spec.run_id:
        raise ValueError(f"Only immutable run id {RUN_ID} is accepted")
    assignment = spec.assignment(array_index)
    profile = spec.profile(assignment.profile_id)
    run_root = ROOT / spec.output_root / spec.run_id
    manifest_path = run_root / "prepared_run_manifest.json"
    verify_manifest_sidecar(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != spec.run_id or manifest.get("operational_config_sha256") != sha256_file(CONFIG_PATH):
        raise ValueError("Prepared manifest is not bound to the current immutable run/config")
    verify_hash_inventory(ROOT, spec.source_authorities)
    verify_hash_inventory(ROOT, spec.reviewed_sources, canonical_text=True)
    verify_hash_inventory(run_root, manifest["prepared_artifact_sha256"])

    profile_record = _profile_record(manifest, profile.profile_id)
    chain_record = _chain_record(profile_record, array_index)
    fingerprint = str(chain_record["profile_fingerprint"])
    profile_root = run_root / "profiles" / profile.profile_id
    chain_dir = profile_root / "chains" / f"chain_{assignment.chain_id:02d}"
    status_path = chain_dir / "chain_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if completed_chain_is_reusable(
            chain_dir,
            status,
            run_id=run_id,
            array_index=array_index,
            fingerprint=fingerprint,
            expected_draws=spec.retained_draws_per_chain,
            required_artifacts=[
                "draws_params.parquet",
                "draws_latent.npz",
                "latent_validation.csv",
                "acceptance_rates.csv",
                "runtime_log.csv",
                "chain_config_resolved.yaml",
                str(status.get("latest_checkpoint", "")),
            ],
            expected_parameter_schema=profile_record["parameter_schema"],
            expected_years=profile_record["included_years"],
        ):
            print(json.dumps(status, sort_keys=True))
            return status
        _verify_resume_status(
            chain_dir,
            status,
            run_id=run_id,
            array_index=array_index,
            fingerprint=fingerprint,
        )
    else:
        checkpoints = sorted(chain_dir.glob("checkpoints/checkpoint_iter_*.npz"))
        expected_initial = run_root / chain_record["initial_checkpoint"]
        if checkpoints != [expected_initial]:
            raise ValueError("A status-free chain may contain only its manifest-bound initial checkpoint")

    frame_path = run_root / profile_record["frame"]
    config_path = run_root / profile_record["config"]
    if sha256_file(frame_path) != profile_record["frame_sha256"] or sha256_file(config_path) != profile_record["config_sha256"]:
        raise ValueError("Profile input/config hash verification failed")
    frame = pd.read_parquet(frame_path)
    frame.attrs["included_years"] = list(profile_record["included_years"])
    if profile.frame == "pandemic_exclusion":
        frame.attrs["constraint_contract"] = "selected_years_no_period_total"
        frame.attrs["q001_constraint_policy"] = "full_period_q001_not_applied"
        frame.attrs["grand_total"] = int(frame.drop_duplicates("year")["q003_national_year_total"].sum())
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    prior = prior_specification_from_mapping(config["model"], name=profile.prior)
    try:
        with use_prior_specification(prior):
            raw_status = run_mcmc_chain_hpc(
                frame,
                config_path=config_path,
                mode="production",
                chain_id=assignment.chain_id,
                array_task_id=array_index,
                seed=assignment.chain_seed,
                out_dir=profile_root,
                checkpoint_dir=chain_dir / "checkpoints",
                checkpoint_every=spec.checkpoint_every,
                resume=True,
                max_runtime_minutes=spec.max_runtime_minutes,
                stop_before_time_limit_minutes=spec.stop_before_time_limit_minutes,
                model_name=profile.model,
            )
    except Exception:
        if status_path.exists():
            failed = json.loads(status_path.read_text(encoding="utf-8"))
            existing_artifacts = [
                name
                for name in (
                    "draws_params.parquet",
                    "draws_latent.npz",
                    "latent_validation.csv",
                    "acceptance_rates.csv",
                    "runtime_log.csv",
                    "chain_config_resolved.yaml",
                )
                if (chain_dir / name).is_file()
            ]
            inventory = artifact_inventory(chain_dir, existing_artifacts)
            latest = max(chain_dir.glob("checkpoints/checkpoint_iter_*.npz"), default=None)
            if latest is not None:
                latest_relative = latest.relative_to(chain_dir).as_posix()
                inventory[latest_relative] = sha256_file(latest)
                failed["latest_checkpoint"] = latest_relative
                failed["latest_checkpoint_sha256"] = inventory[latest_relative]
            failed.update(
                {
                    "schema_id": "sr_v2_heavy_sensitivity_chain_status/v1",
                    "run_id": run_id,
                    "array_index": array_index,
                    "profile": profile.profile_id,
                    "chain_id": assignment.chain_id,
                    "chain_seed": assignment.chain_seed,
                    "initialization_seed": assignment.initialization_seed,
                    "profile_fingerprint": fingerprint,
                    "parameter_schema": list(profile_record["parameter_schema"]),
                    "included_years": list(profile_record["included_years"]),
                    "artifact_sha256": inventory,
                }
            )
            atomic_json(status_path, failed)
        raise
    status_name = str(raw_status.get("status"))
    if status_name not in {"completed", "checkpointed"}:
        raise ValueError(f"Sampler returned nonreusable chain status: {status_name}")
    artifacts = [
        "draws_params.parquet",
        "draws_latent.npz",
        "latent_validation.csv",
        "acceptance_rates.csv",
        "runtime_log.csv",
        "chain_config_resolved.yaml",
    ]
    inventory = artifact_inventory(chain_dir, artifacts)
    latest_checkpoint = max((chain_dir / "checkpoints").glob("checkpoint_iter_*.npz"))
    latest_relative = latest_checkpoint.relative_to(chain_dir).as_posix()
    inventory[latest_relative] = sha256_file(latest_checkpoint)
    if status_name == "completed":
        _, constraint_failures = _validate_completed_outputs(
            chain_dir,
            list(profile_record["parameter_schema"]),
            spec.retained_draws_per_chain,
        )
    else:
        validation = pd.read_csv(chain_dir / "latent_validation.csv")
        constraint_failures = int((~validation["passed"].astype(bool)).sum()) if "passed" in validation else -1
    status = {
        **raw_status,
        "schema_id": "sr_v2_heavy_sensitivity_chain_status/v1",
        "run_id": run_id,
        "array_index": array_index,
        "profile": profile.profile_id,
        "chain_id": assignment.chain_id,
        "chain_seed": assignment.chain_seed,
        "initialization_seed": assignment.initialization_seed,
        "profile_fingerprint": fingerprint,
        "parameter_schema": list(profile_record["parameter_schema"]),
        "included_years": list(profile_record["included_years"]),
        "constraint_failures": constraint_failures,
        "artifact_sha256": inventory,
        "latest_checkpoint": latest_relative,
        "latest_checkpoint_sha256": inventory[latest_relative],
        "interpretation_boundary": spec.interpretation_boundary,
    }
    atomic_json(status_path, status)
    print(json.dumps(status, sort_keys=True))
    if status_name == "checkpointed":
        raise SystemExit(75)
    return status


def main() -> None:
    args = build_parser().parse_args()
    run_chain(args.run_id, args.array_index)


if __name__ == "__main__":
    main()
