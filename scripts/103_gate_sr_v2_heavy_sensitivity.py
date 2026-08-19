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
    RUN_ID,
    atomic_json,
    completed_chain_is_reusable,
    evaluate_profile_gate,
    load_execution_spec,
    sha256_file,
    verify_hash_inventory,
    verify_manifest_sidecar,
)


CONFIG_PATH = ROOT / "config" / "sr_v2_heavy_sensitivity_execution.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    return parser


def _hold_payload(spec, reason: str, *, checks: list[dict] | None = None) -> dict:
    return {
        "schema_id": "sr_v2_heavy_sensitivity_gate/v1",
        "run_id": spec.run_id,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HOLD",
        "passed": False,
        "reason": reason,
        "checks": checks or [],
        "primary_result_replaced": False,
        "manuscript_authorized": False,
        "submission_authorized": False,
        "interpretation_boundary": spec.interpretation_boundary,
    }


def gate(run_id: str) -> dict:
    spec = load_execution_spec(CONFIG_PATH)
    if run_id != RUN_ID or run_id != spec.run_id:
        raise ValueError(f"Only immutable run id {RUN_ID} is accepted")
    run_root = ROOT / spec.output_root / spec.run_id
    gate_path = run_root / "heavy_sensitivity_gate.json"
    atomic_json(gate_path, _hold_payload(spec, "validation_in_progress"))
    profile_results: list[dict] = []
    top_checks: list[dict] = []
    try:
        authority_hashes = verify_hash_inventory(ROOT, spec.source_authorities)
        source_hashes = verify_hash_inventory(ROOT, spec.reviewed_sources, canonical_text=True)
        top_checks.append({"check": "frozen_authority_hashes", "passed": True, "detail": f"files={len(authority_hashes)}"})
        top_checks.append({"check": "reviewed_source_hashes", "passed": True, "detail": f"files={len(source_hashes)}"})
        primary_gate = json.loads((ROOT / "outputs" / "scientific_reports_v2" / "production_8chain" / "production_gate.json").read_text(encoding="utf-8"))
        top_checks.append({"check": "frozen_primary_gate_passed", "passed": primary_gate.get("passed") is True, "detail": f"passed={primary_gate.get('passed')}"})
        prepared_manifest_path = run_root / "prepared_run_manifest.json"
        verify_manifest_sidecar(prepared_manifest_path)
        manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
        verify_hash_inventory(run_root, manifest["prepared_artifact_sha256"])
        top_checks.append({"check": "prepared_artifact_hashes", "passed": True, "detail": f"files={len(manifest['prepared_artifact_sha256'])}"})
        merge_manifest_path = run_root / "merge_manifest.json"
        verify_manifest_sidecar(merge_manifest_path)
        merge_manifest = json.loads(merge_manifest_path.read_text(encoding="utf-8"))
        verify_hash_inventory(run_root, merge_manifest["artifact_sha256"])
        merged_ids = [row["profile"] for row in merge_manifest.get("profiles", [])]
        expected_ids = [profile.profile_id for profile in spec.profiles]
        top_checks.append({"check": "exact_six_merged_profiles", "passed": merged_ids == expected_ids, "detail": f"profiles={merged_ids}"})
        top_checks.append({"check": "current_primary_comparison_authority", "passed": all(row.get("primary_summary_sha256") == spec.source_authorities["outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv"] for row in merge_manifest.get("profiles", [])), "detail": "profile merges bind frozen primary summary"})

        for profile in spec.profiles:
            prepared_rows = [row for row in manifest["profiles"] if row["profile"]["id"] == profile.profile_id]
            merged_rows = [row for row in merge_manifest["profiles"] if row["profile"] == profile.profile_id]
            if len(prepared_rows) != 1 or len(merged_rows) != 1:
                raise ValueError(f"Profile evidence cardinality failure: {profile.profile_id}")
            prepared = prepared_rows[0]
            merged = merged_rows[0]
            merged_root = run_root / "profiles" / profile.profile_id / "merged"
            verify_hash_inventory(merged_root, merged["artifact_sha256"])
            frame = pd.read_parquet(run_root / prepared["frame"])
            required_columns_ok = sorted(frame.columns.astype(str).tolist()) == list(prepared["required_columns"])
            diagnostics = pd.read_csv(merged_root / "parameter_diagnostics.csv")
            comparisons = pd.read_csv(merged_root / "primary_comparison.csv")
            gate_chain_records: list[dict] = []
            for assignment_record, merge_chain_record in zip(prepared["chains"], merged["chain_records"], strict=True):
                chain_id = int(assignment_record["chain"])
                chain_dir = run_root / "profiles" / profile.profile_id / "chains" / f"chain_{chain_id:02d}"
                status_path = chain_dir / "chain_status.json"
                if sha256_file(status_path) != merge_chain_record.get("chain_status_sha256"):
                    raise ValueError(f"Chain-status SHA-256 changed after merge: {profile.profile_id}/chain_{chain_id:02d}")
                status = json.loads(status_path.read_text(encoding="utf-8"))
                completed_chain_is_reusable(
                    chain_dir,
                    status,
                    run_id=spec.run_id,
                    array_index=int(assignment_record["array_index"]),
                    fingerprint=str(assignment_record["profile_fingerprint"]),
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
                    expected_parameter_schema=prepared["parameter_schema"],
                    expected_years=prepared["included_years"],
                )
                gate_chain_records.append(
                    {
                        "chain_id": chain_id,
                        "status": status["status"],
                        "saved_draws": int(status["saved_draws"]),
                        "hashes_verified": True,
                        "constraint_failures": int(status["constraint_failures"]),
                        "parameter_schema": list(status["parameter_schema"]),
                        "included_years": list(status["included_years"]),
                    }
                )
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
            if profile.model == "pandemic_interaction":
                expected_period_rows = 3 * len(spec.comparison["interaction_periods"])
                period_rows = comparisons[comparisons["parameter"].isin([
                    "primary_rurality_metro_other",
                    "primary_rurality_nonmetro_adjacent",
                    "primary_rurality_nonmetro_nonadjacent",
                ])]
                periods_ok = len(period_rows) == expected_period_rows and sorted(period_rows["period"].unique()) == sorted(spec.comparison["interaction_periods"])
                result["checks"].append({"check": "complete_draw_derived_interaction_periods", "passed": periods_ok, "detail": f"rows={len(period_rows)}"})
            result["passed"] = all(bool(row["passed"]) for row in result["checks"])
            result["status"] = "PASS" if result["passed"] else "HOLD"
            profile_results.append(result)
        top_pass = all(bool(row["passed"]) for row in top_checks)
        passed = top_pass and len(profile_results) == 6 and all(result["passed"] for result in profile_results)
        payload = {
            "schema_id": "sr_v2_heavy_sensitivity_gate/v1",
            "run_id": spec.run_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if passed else "HOLD",
            "passed": passed,
            "reason": "computational_sensitivity_complete" if passed else "one_or_more_checks_failed",
            "checks": top_checks,
            "profiles": profile_results,
            "source_authorities": spec.source_authorities,
            "reviewed_sources": spec.reviewed_sources,
            "merge_manifest_sha256": sha256_file(run_root / "merge_manifest.json"),
            "primary_result_replaced": False,
            "manuscript_authorized": False,
            "submission_authorized": False,
            "interpretation_boundary": spec.interpretation_boundary,
        }
    except Exception as exc:
        payload = _hold_payload(spec, f"validation_error: {type(exc).__name__}: {exc}", checks=top_checks)
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
