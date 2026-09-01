from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.model import PRIMARY_TERMS  # noqa: E402
from bayes_constrained.sensitivity import (  # noqa: E402
    EXPECTED_EXCLUSION_YEARS,
    EXPECTED_FULL_YEARS,
    OUTPUT_ROOT,
    RUN_ID,
    atomic_json,
    completed_chain_is_reusable,
    evaluate_profile_gate,
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
    return parser


def _hold_payload(reason: str, *, run_id: str = RUN_ID, interpretation_boundary: str = "", checks: list[dict] | None = None) -> dict:
    return {
        "schema_id": "sr_v2_heavy_sensitivity_gate/v1",
        "run_id": RUN_ID,
        "invocation": {"requested_run_id": str(run_id)},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HOLD",
        "passed": False,
        "reason": reason,
        "checks": checks or [],
        "primary_result_replaced": False,
        "manuscript_authorized": False,
        "submission_authorized": False,
        "interpretation_boundary": interpretation_boundary,
    }


def _prepared_profile(rows: list[dict], profile_id: str) -> dict:
    matches = [row for row in rows if row.get("profile", {}).get("id") == profile_id]
    if len(matches) != 1:
        raise ValueError(f"Prepared profile evidence cardinality failure: {profile_id}")
    return matches[0]


def _merged_profile(rows: list[dict], profile_id: str) -> dict:
    matches = [row for row in rows if row.get("profile") == profile_id]
    if len(matches) != 1:
        raise ValueError(f"Merged profile evidence cardinality failure: {profile_id}")
    return matches[0]


def _checkpoint_files(chain_dir: Path) -> list[str]:
    checkpoint_dir = chain_dir / "checkpoints"
    if not checkpoint_dir.is_dir():
        raise ValueError(f"Checkpoint directory is missing: {chain_dir}")
    return sorted(path.relative_to(chain_dir).as_posix() for path in checkpoint_dir.iterdir() if path.is_file())


def gate(run_id: str, *, root: Path = ROOT, config_path: Path = CONFIG_PATH) -> dict:
    """Evaluate the immutable heavy gate, writing canonical HOLD before parsing inputs."""
    root = Path(root).resolve()
    canonical_root = safe_relative_path(root, OUTPUT_ROOT) / RUN_ID
    canonical_root.mkdir(parents=True, exist_ok=True)
    gate_path = canonical_root / "heavy_sensitivity_gate.json"
    payload = _hold_payload("validation_in_progress", run_id=run_id)
    atomic_json(gate_path, payload)

    profile_results: list[dict] = []
    top_checks: list[dict] = []
    try:
        spec = load_execution_spec(config_path)
        payload["interpretation_boundary"] = spec.interpretation_boundary
        if run_id != RUN_ID or run_id != spec.run_id:
            raise ValueError(f"Only immutable run id {RUN_ID} is accepted")
        if canonical_root != safe_relative_path(root, spec.output_root) / spec.run_id:
            raise ValueError("Configured output root is not the canonical gate root")
        config_hash = sha256_file(config_path)
        authority_hashes = verify_hash_inventory(root, spec.source_authorities)
        final_source = load_final_source_manifest(root, spec, canonical_root / "launch_envelope.json")
        expected_preparation_identity = preparation_identity(spec, config_sha256=config_hash, final_source_manifest=final_source)
        top_checks.extend([
            {"check": "frozen_authority_hashes", "passed": True, "detail": f"files={len(authority_hashes)}"},
            {"check": "reviewed_final_source_manifest", "passed": True, "detail": f"files={len(final_source['sources'])}"},
        ])
        primary_gate_path = safe_relative_path(root, "outputs/scientific_reports_v2/production_8chain/production_gate.json", must_exist=True)
        primary_gate = json.loads(primary_gate_path.read_text(encoding="utf-8"))
        top_checks.append({"check": "frozen_primary_gate_passed", "passed": primary_gate.get("passed") is True, "detail": f"passed={primary_gate.get('passed')}"})

        prepared_manifest_path = canonical_root / "prepared_run_manifest.json"
        prepared_hash = verify_manifest_sidecar(prepared_manifest_path)
        manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
        expected_prepared = {
            "schema_id": "sr_v2_heavy_sensitivity_prepared_run/v1",
            "run_id": spec.run_id,
            "operational_config_sha256": config_hash,
            "preparation_identity": expected_preparation_identity,
            "final_source_manifest_sha256": final_source["manifest_sha256"],
            "launch_envelope_sha256": final_source["envelope_sha256"],
            "launch_commit": final_source["launch_commit"],
            "bundle_sha256": final_source["bundle_sha256"],
        }
        prepared_drift = {key: (value, manifest.get(key)) for key, value in expected_prepared.items() if manifest.get(key) != value}
        if prepared_drift:
            raise ValueError(f"Prepared-run identity mismatch: {prepared_drift}")
        verify_hash_inventory(canonical_root, manifest["prepared_artifact_sha256"])
        top_checks.append({"check": "prepared_artifact_hashes", "passed": True, "detail": f"files={len(manifest['prepared_artifact_sha256'])}"})

        merge_manifest_path = canonical_root / "merge_manifest.json"
        merge_hash = verify_manifest_sidecar(merge_manifest_path)
        merge_manifest = json.loads(merge_manifest_path.read_text(encoding="utf-8"))
        expected_merge = {
            "schema_id": "sr_v2_heavy_sensitivity_merge/v1",
            "run_id": spec.run_id,
            "operational_config_sha256": config_hash,
            "preparation_identity": expected_preparation_identity,
            "final_source_manifest_sha256": final_source["manifest_sha256"],
            "launch_envelope_sha256": final_source["envelope_sha256"],
            "launch_commit": final_source["launch_commit"],
            "bundle_sha256": final_source["bundle_sha256"],
        }
        merge_drift = {key: (value, merge_manifest.get(key)) for key, value in expected_merge.items() if merge_manifest.get(key) != value}
        if merge_drift:
            raise ValueError(f"Merge identity mismatch: {merge_drift}")
        verify_hash_inventory(canonical_root, merge_manifest["artifact_sha256"])
        merged_ids = [row.get("profile") for row in merge_manifest.get("profiles", [])]
        expected_ids = [profile.profile_id for profile in spec.profiles]
        top_checks.append({"check": "exact_six_merged_profiles", "passed": merged_ids == expected_ids, "detail": f"profiles={merged_ids}"})
        primary_hash = spec.source_authorities["outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv"]
        current_primary = all(row.get("primary_summary_sha256") == primary_hash for row in merge_manifest.get("profiles", []))
        top_checks.append({"check": "current_primary_comparison_authority", "passed": current_primary, "detail": "profile merges bind frozen primary summary"})

        for profile in spec.profiles:
            prepared = _prepared_profile(manifest["profiles"], profile.profile_id)
            merged = _merged_profile(merge_manifest["profiles"], profile.profile_id)
            merged_root = canonical_root / "profiles" / profile.profile_id / "merged"
            expected_profile_merge = {
                "schema_id": "sr_v2_heavy_sensitivity_profile_merge/v1",
                "run_id": spec.run_id,
                "profile": profile.profile_id,
                "operational_config_sha256": config_hash,
                "preparation_identity": expected_preparation_identity,
                "final_source_manifest_sha256": final_source["manifest_sha256"],
                "launch_envelope_sha256": final_source["envelope_sha256"],
                "launch_commit": final_source["launch_commit"],
                "bundle_sha256": final_source["bundle_sha256"],
                "primary_summary_sha256": primary_hash,
            }
            profile_drift = {key: (value, merged.get(key)) for key, value in expected_profile_merge.items() if merged.get(key) != value}
            if profile_drift:
                raise ValueError(f"Profile merge identity mismatch for {profile.profile_id}: {profile_drift}")
            verify_manifest_sidecar(merged_root / "profile_merge.json")
            verify_hash_inventory(merged_root, merged["artifact_sha256"])
            frame = pd.read_parquet(safe_relative_path(canonical_root, prepared["frame"], must_exist=True))
            required_columns_ok = sorted(frame.columns.astype(str).tolist()) == list(prepared["required_columns"])
            diagnostics = pd.read_csv(merged_root / "parameter_diagnostics.csv")
            comparisons = pd.read_csv(merged_root / "primary_comparison.csv")
            merge_chain_records = merged.get("chain_records", [])
            if [int(row.get("chain_id", -1)) for row in merge_chain_records] != [1, 2, 3, 4]:
                raise ValueError(f"Profile merge chain labels are not exactly 1..4: {profile.profile_id}")
            gate_chain_records: list[dict] = []
            for assignment_record, merge_chain_record in zip(prepared["chains"], merge_chain_records, strict=True):
                chain_id = int(assignment_record["chain"])
                chain_dir = canonical_root / "profiles" / profile.profile_id / "chains" / f"chain_{chain_id:02d}"
                status_path = chain_dir / "chain_status.json"
                if sha256_file(status_path) != merge_chain_record.get("chain_status_sha256"):
                    raise ValueError(f"Chain-status SHA-256 changed after merge: {profile.profile_id}/chain_{chain_id:02d}")
                status = json.loads(status_path.read_text(encoding="utf-8"))
                if (
                    status.get("profile_fingerprint") != assignment_record["profile_fingerprint"]
                    or merge_chain_record.get("profile_fingerprint") != assignment_record["profile_fingerprint"]
                    or status.get("checkpoint_target_identity") != assignment_record["checkpoint_target_identity"]
                    or merge_chain_record.get("checkpoint_target_identity") != assignment_record["checkpoint_target_identity"]
                ):
                    raise ValueError(f"Profile fingerprint/checkpoint identity drift: {profile.profile_id}/chain_{chain_id:02d}")
                completed_chain_is_reusable(
                    chain_dir, status,
                    run_id=spec.run_id,
                    array_index=int(assignment_record["array_index"]),
                    fingerprint=str(assignment_record["profile_fingerprint"]),
                    expected_draws=spec.retained_draws_per_chain,
                    required_artifacts=[
                        "draws_params.parquet", "draws_latent.npz", "latent_validation.csv",
                        "acceptance_rates.csv", "runtime_log.csv", "chain_config_resolved.yaml",
                    ] + _checkpoint_files(chain_dir),
                    expected_parameter_schema=prepared["parameter_schema"],
                    expected_years=prepared["included_years"],
                    expected_terminal_iteration=spec.iterations_per_chain,
                    target_identity=assignment_record["checkpoint_target_identity"],
                )
                validate_chain_draws(
                    pd.read_parquet(chain_dir / "draws_params.parquet"),
                    chain_id=chain_id,
                    parameter_schema=prepared["parameter_schema"],
                    retained_draws=spec.retained_draws_per_chain,
                    burn_in=spec.burn_in,
                    thin=spec.thin,
                )
                gate_chain_records.append({
                    "chain_id": chain_id,
                    "status": status["status"],
                    "saved_draws": int(status["saved_draws"]),
                    "hashes_verified": True,
                    "constraint_failures": int(status["constraint_failures"]),
                    "parameter_schema": list(status["parameter_schema"]),
                    "included_years": list(status["included_years"]),
                })
            result = evaluate_profile_gate(
                profile=profile,
                chain_records=gate_chain_records,
                diagnostics=diagnostics,
                comparisons=comparisons,
                expected_schema=prepared["parameter_schema"],
                expected_years=(EXPECTED_EXCLUSION_YEARS if profile.frame == "pandemic_exclusion" else EXPECTED_FULL_YEARS),
                expected_comparison_parameters=spec.comparison["primary_parameters"],
                thresholds=spec.thresholds,
                primary_parameters=PRIMARY_TERMS,
            )
            result["checks"].append({"check": "required_frame_columns", "passed": required_columns_ok, "detail": f"columns={len(frame.columns)}"})
            result["passed"] = all(bool(row["passed"]) for row in result["checks"])
            result["status"] = "PASS" if result["passed"] else "HOLD"
            result["profile_fingerprints"] = [row["profile_fingerprint"] for row in prepared["chains"]]
            profile_results.append(result)

        passed = all(bool(row["passed"]) for row in top_checks) and len(profile_results) == 6 and all(result["passed"] for result in profile_results)
        payload = {
            "schema_id": "sr_v2_heavy_sensitivity_gate/v1",
            "run_id": spec.run_id,
            "invocation": {"requested_run_id": run_id, "config_path": str(Path(config_path).resolve())},
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if passed else "HOLD",
            "passed": passed,
            "reason": "computational_sensitivity_complete" if passed else "one_or_more_checks_failed",
            "checks": top_checks,
            "profiles": profile_results,
            "operational_config_sha256": config_hash,
            "preparation_identity": expected_preparation_identity,
            "prepared_manifest_sha256": prepared_hash,
            "merge_manifest_sha256": merge_hash,
            "final_source_manifest_sha256": final_source["manifest_sha256"],
            "launch_envelope_sha256": final_source["envelope_sha256"],
            "launch_commit": final_source["launch_commit"],
            "bundle_sha256": final_source["bundle_sha256"],
            "source_authorities": spec.source_authorities,
            "primary_result_replaced": False,
            "manuscript_authorized": False,
            "submission_authorized": False,
            "interpretation_boundary": spec.interpretation_boundary,
        }
    except Exception as exc:
        payload = _hold_payload(
            f"validation_error: {type(exc).__name__}: {exc}",
            run_id=run_id,
            interpretation_boundary=str(payload.get("interpretation_boundary", "")),
            checks=top_checks,
        )
        payload["profiles"] = profile_results
    atomic_json(gate_path, payload)
    print(json.dumps(payload, sort_keys=True))
    return payload


def main() -> None:
    args = build_parser().parse_args()
    result = gate(args.run_id)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
