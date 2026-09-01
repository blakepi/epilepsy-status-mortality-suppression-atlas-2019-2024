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
    OUTPUT_ROOT,
    RUN_ID,
    artifact_inventory,
    atomic_json,
    completed_chain_is_reusable,
    load_declared_checkpoint,
    load_execution_spec,
    load_final_source_manifest,
    preparation_identity,
    safe_relative_path,
    sha256_file,
    validate_chain_draws,
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


def _checkpoint_artifacts(chain_dir: Path) -> list[str]:
    return sorted(path.relative_to(chain_dir).as_posix() for path in (chain_dir / "checkpoints").iterdir() if path.is_file())


def _latest_checkpoint(chain_dir: Path) -> Path | None:
    checkpoints = list((chain_dir / "checkpoints").glob("checkpoint_iter_*.npz"))
    if not checkpoints:
        return None
    try:
        return max(checkpoints, key=lambda path: int(path.stem.removeprefix("checkpoint_iter_")))
    except ValueError as exc:
        raise ValueError("Malformed checkpoint iteration filename") from exc


def _verify_resume_status(
    chain_dir: Path,
    status: dict,
    *,
    run_id: str,
    array_index: int,
    fingerprint: str,
    target_identity: dict[str, object],
    likelihood_family: str,
) -> Path:
    expected = {
        "run_id": run_id,
        "array_index": array_index,
        "profile_fingerprint": fingerprint,
        "checkpoint_target_identity": target_identity,
    }
    changed = {key: (value, status.get(key)) for key, value in expected.items() if status.get(key) != value}
    if changed:
        raise ValueError(f"Refusing cross-target checkpoint/status resume: {changed}")
    inventory = status.get("artifact_sha256", {})
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("Resume status has no exact artifact inventory")
    verify_hash_inventory(chain_dir, inventory)
    actual = {path.relative_to(chain_dir).as_posix() for path in chain_dir.rglob("*") if path.is_file() and path.name != "chain_status.json"}
    if actual != set(inventory):
        raise ValueError("Resume chain contains orphan, missing, or undeclared artifacts")
    checkpoint = status.get("latest_checkpoint")
    checkpoint_hash = status.get("latest_checkpoint_sha256")
    if checkpoint or checkpoint_hash:
        if not isinstance(checkpoint, str) or not isinstance(checkpoint_hash, str):
            raise ValueError("Checkpoint path/hash evidence is incomplete")
        checkpoint_path = safe_relative_path(chain_dir, checkpoint, must_exist=True)
        actual_hash = sha256_file(checkpoint_path)
        if actual_hash != checkpoint_hash:
            raise ValueError(f"Checkpoint SHA-256 mismatch: expected {checkpoint_hash}, found {actual_hash}")
        load_declared_checkpoint(
            chain_dir / "checkpoints",
            checkpoint_path.name,
            expected_target_identity=target_identity,
            expected_likelihood_family=likelihood_family,
        )
        return checkpoint_path
    raise ValueError("Resume status does not declare an exact checkpoint")


def _validate_completed_outputs(chain_dir: Path, expected_schema: list[str], expected_draws: int, *, chain_id: int, burn_in: int, thin: int) -> tuple[int, int]:
    draws = pd.read_parquet(chain_dir / "draws_params.parquet")
    validate_chain_draws(draws, chain_id=chain_id, parameter_schema=expected_schema, retained_draws=expected_draws, burn_in=burn_in, thin=thin)
    validation = pd.read_csv(chain_dir / "latent_validation.csv")
    if "passed" not in validation or not validation["passed"].astype(bool).all():
        raise ValueError("Completed chain contains count-constraint failures")
    return int(len(draws)), int((~validation["passed"].astype(bool)).sum())


def run_chain(
    run_id: str,
    array_index: int,
    *,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    sampler_runner=run_mcmc_chain_hpc,
) -> dict:
    root = Path(root).resolve()
    spec = load_execution_spec(config_path)
    if run_id != RUN_ID or run_id != spec.run_id:
        raise ValueError(f"Only immutable run id {RUN_ID} is accepted")
    assignment = spec.assignment(array_index)
    profile = spec.profile(assignment.profile_id)
    run_root = safe_relative_path(root, OUTPUT_ROOT) / RUN_ID
    final_source = load_final_source_manifest(root, spec, run_root / "launch_envelope.json")
    config_hash = sha256_file(config_path)
    expected_preparation = preparation_identity(spec, config_sha256=config_hash, final_source_manifest=final_source)
    manifest_path = run_root / "prepared_run_manifest.json"
    verify_manifest_sidecar(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_id") != "sr_v2_heavy_sensitivity_prepared_run/v1"
        or manifest.get("run_id") != spec.run_id
        or manifest.get("operational_config_sha256") != config_hash
        or manifest.get("preparation_identity") != expected_preparation
        or manifest.get("final_source_manifest_sha256") != final_source["manifest_sha256"]
        or manifest.get("launch_envelope_sha256") != final_source["envelope_sha256"]
        or manifest.get("launch_commit") != final_source["launch_commit"]
        or manifest.get("bundle_sha256") != final_source["bundle_sha256"]
    ):
        raise ValueError("Prepared manifest is not bound to the current immutable run/config")
    verify_hash_inventory(root, spec.source_authorities)
    verify_hash_inventory(run_root, manifest["prepared_artifact_sha256"])

    profile_record = _profile_record(manifest, profile.profile_id)
    chain_record = _chain_record(profile_record, array_index)
    fingerprint = str(chain_record["profile_fingerprint"])
    target_identity = dict(chain_record["checkpoint_target_identity"])
    profile_root = run_root / "profiles" / profile.profile_id
    chain_dir = profile_root / "chains" / f"chain_{assignment.chain_id:02d}"
    status_path = chain_dir / "chain_status.json"
    resume_checkpoint: Path
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
            ] + _checkpoint_artifacts(chain_dir),
            expected_parameter_schema=profile_record["parameter_schema"],
            expected_years=profile_record["included_years"],
            expected_terminal_iteration=spec.iterations_per_chain,
            target_identity=target_identity,
        ):
            print(json.dumps(status, sort_keys=True))
            return status
        resume_checkpoint = _verify_resume_status(
            chain_dir,
            status,
            run_id=run_id,
            array_index=array_index,
            fingerprint=fingerprint,
            target_identity=target_identity,
            likelihood_family=profile.likelihood,
        )
    else:
        checkpoints = sorted(chain_dir.glob("checkpoints/checkpoint_iter_*.npz"))
        expected_initial = safe_relative_path(run_root, chain_record["initial_checkpoint"], must_exist=True)
        if checkpoints != [expected_initial]:
            raise ValueError("A status-free chain may contain only its manifest-bound initial checkpoint")
        expected_files = {expected_initial, expected_initial.with_name(expected_initial.name + ".sha256")}
        if set(path for path in (chain_dir / "checkpoints").iterdir() if path.is_file()) != expected_files:
            raise ValueError("Status-free chain contains orphan initial checkpoint artifacts")
        load_declared_checkpoint(
            chain_dir / "checkpoints",
            expected_initial.name,
            expected_target_identity=target_identity,
            expected_likelihood_family=profile.likelihood,
        )
        resume_checkpoint = expected_initial

    frame_path = safe_relative_path(run_root, profile_record["frame"], must_exist=True)
    profile_config_path = safe_relative_path(run_root, profile_record["config"], must_exist=True)
    if sha256_file(frame_path) != profile_record["frame_sha256"] or sha256_file(profile_config_path) != profile_record["config_sha256"]:
        raise ValueError("Profile input/config hash verification failed")
    frame = pd.read_parquet(frame_path)
    frame.attrs["included_years"] = list(profile_record["included_years"])
    if profile.frame == "pandemic_exclusion":
        frame.attrs["constraint_contract"] = "selected_years_no_period_total"
        frame.attrs["q001_constraint_policy"] = "full_period_q001_not_applied"
        frame.attrs["grand_total"] = int(frame.drop_duplicates("year")["q003_national_year_total"].sum())
    config = yaml.safe_load(profile_config_path.read_text(encoding="utf-8"))
    prior = prior_specification_from_mapping(config["model"], name=profile.prior)
    try:
        with use_prior_specification(prior):
            raw_status = sampler_runner(
                frame,
                config_path=profile_config_path,
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
                target_identity=target_identity,
                resume_checkpoint_path=resume_checkpoint,
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
            existing_artifacts.extend(_checkpoint_artifacts(chain_dir))
            inventory = artifact_inventory(chain_dir, existing_artifacts)
            latest = _latest_checkpoint(chain_dir)
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
                    "checkpoint_target_identity": target_identity,
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
    artifacts.extend(_checkpoint_artifacts(chain_dir))
    inventory = artifact_inventory(chain_dir, artifacts)
    latest_checkpoint = _latest_checkpoint(chain_dir)
    if latest_checkpoint is None:
        raise ValueError("Sampler returned without a checkpoint")
    latest_relative = latest_checkpoint.relative_to(chain_dir).as_posix()
    if status_name == "completed":
        _, constraint_failures = _validate_completed_outputs(
            chain_dir,
            list(profile_record["parameter_schema"]),
            spec.retained_draws_per_chain,
            chain_id=assignment.chain_id,
            burn_in=spec.burn_in,
            thin=spec.thin,
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
        "checkpoint_target_identity": target_identity,
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
