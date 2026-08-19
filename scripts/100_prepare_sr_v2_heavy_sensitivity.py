from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

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
    prior_specification_from_mapping,
)
from bayes_constrained.sampler import save_chain_checkpoint  # noqa: E402
from bayes_constrained.sensitivity import (  # noqa: E402
    OUTPUT_ROOT,
    RUN_ID,
    acquire_prepare_lock,
    assert_manifest_matches,
    atomic_json,
    build_sensitivity_frame,
    checkpoint_target_identity,
    expected_parameter_schema,
    load_execution_spec,
    load_final_source_manifest,
    preparation_identity,
    profile_fingerprint,
    publish_directory_no_clobber,
    safe_relative_path,
    sha256_file,
    verify_hash_inventory,
    verify_manifest_sidecar,
)


CONFIG_PATH = ROOT / "config" / "sr_v2_heavy_sensitivity_execution.yaml"
SVI_PATH = ROOT / "data" / "raw" / "covariates" / "SVI_2022_US_county.csv"
PRIMARY_CONFIG_PATH = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain" / "config" / "sr_v2_production.yaml"
REGISTRY_PATH = ROOT / "config" / "scientific_reports_v2_robustness_registry.yaml"


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8", newline="\n")


def _profile_config(spec, profile, prior_mapping: dict, *, root: Path) -> dict:
    primary_path = root / "outputs" / "scientific_reports_v2" / "production_8chain" / "config" / "sr_v2_production.yaml"
    primary = yaml.safe_load(primary_path.read_text(encoding="utf-8"))
    run = dict(primary["run"])
    run.update(
        {
            "n_chains": 4,
            "n_iter": spec.iterations_per_chain,
            "burn_in": spec.burn_in,
            "thin": spec.thin,
            "checkpoint_every": spec.checkpoint_every,
            "random_seeds": [row.chain_seed for row in spec.chain_map if row.profile_id == profile.profile_id],
            "initialization_seeds": [row.initialization_seed for row in spec.chain_map if row.profile_id == profile.profile_id],
            "likelihood_family": profile.likelihood,
            "max_extensions": 0,
        }
    )
    model = dict(primary.get("model", {}))
    prior = prior_specification_from_mapping(prior_mapping, name=profile.prior)
    model.update(
        {
            "model_variant": profile.model,
            "frame_contract": profile.frame,
            "likelihood_family": profile.likelihood,
            "prior_profile": profile.prior,
            "intercept_prior_sd": prior.intercept_sd,
            "fixed_effect_prior_sd": prior.nonintercept_beta_sd,
            "sigma_state_prior_sd": prior.state_scale_halfnormal_sd,
            "sigma_year_prior_sd": prior.year_scale_halfnormal_sd,
            "log_kappa_prior_mean": prior.log_kappa_mean,
            "log_kappa_prior_sd": prior.log_kappa_sd,
        }
    )
    return {
        "run": run,
        "model": model,
        "diagnostics": dict(spec.thresholds),
        "outputs": {
            "root": f"{spec.output_root}/{spec.run_id}/profiles/{profile.profile_id}"
        },
        "scientific_reports_v2": {
            "analysis": "heavy_sensitivity",
            "run_id": spec.run_id,
            "profile": profile.profile_id,
            "not_primary_inference": True,
            "interpretation_boundary": spec.interpretation_boundary,
        },
    }


def _initial_checkpoint(
    frame: pd.DataFrame,
    allocation: np.ndarray,
    profile,
    prior_mapping: dict,
    assignment,
    path: Path,
    target_identity: dict[str, object],
) -> None:
    design = make_design(
        frame,
        model=profile.model,
        likelihood_family=profile.likelihood,
    )
    theta = initialize_theta(frame, allocation, design)
    prior = prior_specification_from_mapping(prior_mapping, name=profile.prior)
    current_lp = log_posterior_theta(
        allocation,
        theta,
        design,
        intercept_mean=crude_intercept_prior(frame),
        prior=prior,
    )
    if not np.isfinite(current_lp):
        raise ValueError(f"Non-finite initial target for array index {assignment.array_index}")
    moves = {
        "transfer": 0,
        "interval_transfer": 0,
        "interval_path": 0,
        "swap_2x2": 0,
        "cycle_swap": 0,
        "blocked_refresh": 0,
    }
    blocks = ["beta", "state", "year", "log_sigma_state", "log_sigma_year"]
    if profile.likelihood == "negative_binomial_2":
        blocks.append("log_kappa")
    save_chain_checkpoint(
        path,
        y=allocation,
        theta=theta,
        rng=np.random.default_rng(assignment.chain_seed),
        iteration=0,
        saved_draws=0,
        current_lp=current_lp,
        accepted=moves,
        proposed=dict(moves),
        param_accept={key: 0 for key in blocks},
        param_prop={key: 0 for key in blocks},
        likelihood_family=profile.likelihood,
        target_identity=target_identity,
    )


def _verify_existing(run_root: Path, expected_identity: dict) -> dict:
    manifest_path = run_root / "prepared_run_manifest.json"
    verify_manifest_sidecar(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert_manifest_matches(expected_identity, manifest)
    inventory = manifest.get("prepared_artifact_sha256")
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("Existing preparation manifest has no artifact hash inventory")
    verify_hash_inventory(run_root, inventory)
    return manifest


def prepare(
    *,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    launch_envelope_path: Path | None = None,
    frame_loader=load_model_frame,
    allocation_solver=solve_feasible_allocation,
) -> dict:
    root = Path(root).resolve()
    spec = load_execution_spec(config_path)
    verify_hash_inventory(root, spec.source_authorities)
    if launch_envelope_path is None:
        raise FileNotFoundError("Reviewed external launch envelope is required before preparation")
    final_source = load_final_source_manifest(root, spec, launch_envelope_path)
    primary_gate_path = root / "outputs/scientific_reports_v2/production_8chain/production_gate.json"
    if json.loads(primary_gate_path.read_text(encoding="utf-8")).get("passed") is not True:
        raise ValueError("Frozen corrected primary gate is not passed")
    config_hash = sha256_file(config_path)
    identity = {
        "schema_id": "sr_v2_heavy_sensitivity_prepared_run/v1",
        "run_id": spec.run_id,
        "preparation_identity": preparation_identity(
            spec, config_sha256=config_hash, final_source_manifest=final_source
        ),
        "operational_config_sha256": config_hash,
        "final_source_manifest_sha256": final_source["manifest_sha256"],
        "launch_envelope_sha256": final_source["envelope_sha256"],
        "launch_commit": final_source["launch_commit"],
        "bundle_sha256": final_source["bundle_sha256"],
    }
    output_base = safe_relative_path(root, OUTPUT_ROOT)
    run_root = output_base / RUN_ID
    output_base.mkdir(parents=True, exist_ok=True)
    with acquire_prepare_lock(output_base / f".{RUN_ID}.prepare.lock"):
        if run_root.exists():
            return _verify_existing(run_root, identity)
        registry = yaml.safe_load(
            (root / "config/scientific_reports_v2_robustness_registry.yaml").read_text(encoding="utf-8")
        )
        prior_profiles = registry["prior_profiles"]
        source_frame = frame_loader()
        svi_path = root / "data/raw/covariates/SVI_2022_US_county.csv"
        temporary = Path(tempfile.mkdtemp(prefix=f".{RUN_ID}.prepare-", dir=output_base))
        try:
            artifact_hashes: dict[str, str] = {}
            envelope_copy = temporary / "launch_envelope.json"
            shutil.copyfile(Path(launch_envelope_path), envelope_copy)
            shutil.copyfile(Path(launch_envelope_path).with_name(Path(launch_envelope_path).name + ".sha256"), envelope_copy.with_name(envelope_copy.name + ".sha256"))
            artifact_hashes["launch_envelope.json"] = sha256_file(envelope_copy)
            artifact_hashes["launch_envelope.json.sha256"] = sha256_file(envelope_copy.with_name(envelope_copy.name + ".sha256"))
            profile_records: list[dict] = []
            for profile in spec.profiles:
                profile_root = temporary / "profiles" / profile.profile_id
                frame = build_sensitivity_frame(source_frame, profile, svi_path=svi_path)
                frame_path = profile_root / "inputs/model_frame.parquet"
                frame_path.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(frame_path, index=False)
                frame_hash = sha256_file(frame_path)
                frame_relative = frame_path.relative_to(temporary).as_posix()
                artifact_hashes[frame_relative] = frame_hash
                resolved = _profile_config(spec, profile, prior_profiles[profile.prior], root=root)
                resolved_path = profile_root / "config/resolved_profile.yaml"
                _write_yaml(resolved_path, resolved)
                resolved_hash = sha256_file(resolved_path)
                resolved_relative = resolved_path.relative_to(temporary).as_posix()
                artifact_hashes[resolved_relative] = resolved_hash
                schema = expected_parameter_schema(frame, profile)
                years = sorted(frame["year"].astype(str).unique())
                chains: list[dict] = []
                for assignment in (row for row in spec.chain_map if row.profile_id == profile.profile_id):
                    initial = allocation_solver(
                        frame, seed=assignment.initialization_seed, objective="random", time_limit_seconds=900
                    )
                    assert_constraints(initial, frame, label=f"{profile.profile_id}_chain{assignment.chain_id}_fresh_start")
                    initialization_path = profile_root / "initializations" / f"initial_allocation_chain_{assignment.chain_id:02d}.parquet"
                    initialization_path.parent.mkdir(parents=True, exist_ok=True)
                    initial_frame = frame[["county_fips", "year", "q002_count_status"]].copy()
                    initial_frame["latent_count"] = initial
                    initial_frame.to_parquet(initialization_path, index=False)
                    init_relative = initialization_path.relative_to(temporary).as_posix()
                    init_hash = sha256_file(initialization_path)
                    artifact_hashes[init_relative] = init_hash
                    fingerprint = profile_fingerprint(
                        profile,
                        assignment,
                        run_id=RUN_ID,
                        included_years=years,
                        execution={
                            "iterations_per_chain": spec.iterations_per_chain,
                            "burn_in": spec.burn_in,
                            "thin": spec.thin,
                            "retained_draws_per_chain": spec.retained_draws_per_chain,
                        },
                        config_sha256=config_hash,
                        input_hashes={**spec.source_authorities, "profile_frame": frame_hash, "initialization": init_hash},
                        source_hashes=final_source["sources"],
                        parameter_schema=schema,
                        launch_provenance={
                            "final_source_manifest_sha256": final_source["manifest_sha256"],
                            "launch_envelope_sha256": final_source["envelope_sha256"],
                            "launch_commit": final_source["launch_commit"],
                            "bundle_sha256": final_source["bundle_sha256"],
                        },
                    )
                    target_identity = checkpoint_target_identity(
                        spec=spec,
                        profile=profile,
                        assignment=assignment,
                        profile_fingerprint_value=fingerprint,
                        operational_config_sha256=config_hash,
                        profile_config_sha256=resolved_hash,
                        frame_sha256=frame_hash,
                        final_source_manifest_sha256=final_source["manifest_sha256"],
                        parameter_schema=schema,
                    )
                    checkpoint_path = profile_root / "chains" / f"chain_{assignment.chain_id:02d}" / "checkpoints/checkpoint_iter_000000000.npz"
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    _initial_checkpoint(
                        frame, initial, profile, prior_profiles[profile.prior], assignment, checkpoint_path, target_identity
                    )
                    checkpoint_relative = checkpoint_path.relative_to(temporary).as_posix()
                    checkpoint_sidecar = checkpoint_path.with_name(checkpoint_path.name + ".sha256")
                    sidecar_relative = checkpoint_sidecar.relative_to(temporary).as_posix()
                    artifact_hashes[checkpoint_relative] = sha256_file(checkpoint_path)
                    artifact_hashes[sidecar_relative] = sha256_file(checkpoint_sidecar)
                    chains.append(
                        {
                            **assignment.to_dict(),
                            "profile_fingerprint": fingerprint,
                            "checkpoint_target_identity": target_identity,
                            "initialization": init_relative,
                            "initialization_sha256": init_hash,
                            "initial_checkpoint": checkpoint_relative,
                            "initial_checkpoint_sha256": sha256_file(checkpoint_path),
                        }
                    )
                profile_records.append(
                    {
                        "profile": profile.to_dict(),
                        "included_years": years,
                        "required_columns": sorted(frame.columns.astype(str).tolist()),
                        "parameter_schema": schema,
                        "frame": frame_relative,
                        "frame_sha256": frame_hash,
                        "config": resolved_relative,
                        "config_sha256": resolved_hash,
                        "chains": chains,
                    }
                )
            manifest = {
                **identity,
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "status": "prepared_not_run",
                "source_authorities": spec.source_authorities,
                "joint_regression_evidence_sha256": final_source["joint_regression_evidence_sha256"],
                "profiles": profile_records,
                "prepared_artifact_sha256": dict(sorted(artifact_hashes.items())),
                "interpretation_boundary": spec.interpretation_boundary,
            }
            manifest_path = temporary / "prepared_run_manifest.json"
            atomic_json(manifest_path, manifest)
            manifest_path.with_name(manifest_path.name + ".sha256").write_text(
                sha256_file(manifest_path) + "\n", encoding="ascii", newline="\n"
            )
            atomic_json(
                temporary / "heavy_sensitivity_gate.json",
                {
                    "schema_id": "sr_v2_heavy_sensitivity_gate/v1",
                    "run_id": RUN_ID,
                    "status": "HOLD",
                    "passed": False,
                    "reason": "prepared_not_run",
                    "submission_authorized": False,
                    "interpretation_boundary": spec.interpretation_boundary,
                },
            )
            publish_directory_no_clobber(
                temporary,
                run_root,
                commit_marker="prepared_run_manifest.json.sha256",
            )
        except BaseException:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise
    print(json.dumps({"status": "prepared_not_run", "run_id": RUN_ID}, sort_keys=True))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-envelope", required=True)
    args = parser.parse_args()
    prepare(launch_envelope_path=Path(args.launch_envelope))


if __name__ == "__main__":
    main()
