from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402
from bayes_constrained.model import PRIMARY_TERMS  # noqa: E402
from bayes_constrained.sensitivity import (  # noqa: E402
    OUTPUT_ROOT,
    RUN_ID,
    artifact_inventory,
    atomic_json,
    completed_chain_is_reusable,
    derive_period_irrs,
    load_execution_spec,
    load_final_source_manifest,
    preparation_identity,
    publish_directory_no_clobber,
    safe_relative_path,
    sha256_file,
    validate_chain_draws,
    validate_comparison_table,
    validate_diagnostics_table,
    verify_hash_inventory,
    verify_manifest_sidecar,
)


CONFIG_PATH = ROOT / "config" / "sr_v2_heavy_sensitivity_execution.yaml"
PRIMARY_SUMMARY_PATH = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain" / "posterior_primary_summary.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    return parser


def _profile_record(manifest: dict, profile_id: str) -> dict:
    rows = [row for row in manifest["profiles"] if row["profile"]["id"] == profile_id]
    if len(rows) != 1:
        raise ValueError(f"Prepared manifest profile cardinality failure: {profile_id}")
    return rows[0]


def _quantiles(values: np.ndarray) -> tuple[float, float, float]:
    lower, median, upper = np.quantile(np.asarray(values, dtype=float), [0.025, 0.5, 0.975])
    return float(median), float(lower), float(upper)


def _comparison_rows(profile, draws: pd.DataFrame, primary: pd.DataFrame, parameters: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    period_irrs = derive_period_irrs(draws) if profile.model == "pandemic_interaction" else pd.DataFrame()
    for parameter in parameters:
        primary_row = primary.loc[parameter]
        periods: list[tuple[str, np.ndarray]]
        if profile.model == "pandemic_interaction" and parameter.startswith("primary_rurality_"):
            periods = [
                (period, period_irrs.loc[(period_irrs["parameter"] == parameter) & (period_irrs["period"] == period), "irr"].to_numpy(dtype=float))
                for period in ("pre_pandemic_2019", "acute_pandemic_2020_2021", "later_period_2022_2024")
            ]
        else:
            raw = draws.loc[draws["parameter"].eq(parameter), "value"].to_numpy(dtype=float)
            reported = np.exp(raw) if parameter.startswith(("primary_rurality_", "svi_quartile_")) else raw
            periods = [("modeled_period", reported)]
        for period, values in periods:
            if len(values) != 4 * 4500:
                raise ValueError(f"Incomplete comparison draws for {profile.profile_id}/{parameter}/{period}: {len(values)}")
            median, lower, upper = _quantiles(values)
            primary_median = float(primary_row["posterior_median"])
            rows.append(
                {
                    "profile": profile.profile_id,
                    "parameter": parameter,
                    "period": period,
                    "sensitivity_median": median,
                    "sensitivity_lower_95": lower,
                    "sensitivity_upper_95": upper,
                    "sensitivity_interval_width": upper - lower,
                    "primary_median": primary_median,
                    "primary_lower_95": float(primary_row["credible_interval_lower_95"]),
                    "primary_upper_95": float(primary_row["credible_interval_upper_95"]),
                    "absolute_shift": median - primary_median,
                    "relative_shift_percent": (median / primary_median - 1.0) * 100.0 if primary_median != 0 else np.nan,
                    "primary_value_inside_sensitivity_interval": bool(lower <= primary_median <= upper),
                }
            )
    return pd.DataFrame(rows)


def _atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, path)


def _load_reusable_merge(merged_root: Path, profile_id: str) -> dict | None:
    evidence_path = merged_root / "profile_merge.json"
    if not merged_root.exists():
        return None
    if not evidence_path.is_file():
        raise ValueError(f"Existing merged profile has no evidence manifest: {profile_id}")
    verify_manifest_sidecar(evidence_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    verify_hash_inventory(merged_root, evidence["artifact_sha256"])
    expected_files = set(evidence["artifact_sha256"]) | {"profile_merge.json", "profile_merge.json.sha256"}
    actual_files = {path.relative_to(merged_root).as_posix() for path in merged_root.rglob("*") if path.is_file()}
    if actual_files != expected_files:
        raise ValueError(f"Existing merged profile contains orphan/missing files: {profile_id}")
    return evidence


def merge(run_id: str, *, root: Path = ROOT, config_path: Path = CONFIG_PATH) -> dict:
    root = Path(root).resolve()
    spec = load_execution_spec(config_path)
    if run_id != RUN_ID or run_id != spec.run_id:
        raise ValueError(f"Only immutable run id {RUN_ID} is accepted")
    verify_hash_inventory(root, spec.source_authorities)
    run_root = safe_relative_path(root, OUTPUT_ROOT) / RUN_ID
    final_source = load_final_source_manifest(root, spec, run_root / "launch_envelope.json")
    config_hash = sha256_file(config_path)
    expected_preparation = preparation_identity(spec, config_sha256=config_hash, final_source_manifest=final_source)
    prepared_manifest_path = run_root / "prepared_run_manifest.json"
    verify_manifest_sidecar(prepared_manifest_path)
    manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_id") != "sr_v2_heavy_sensitivity_prepared_run/v1"
        or manifest.get("run_id") != RUN_ID
        or manifest.get("operational_config_sha256") != config_hash
        or manifest.get("preparation_identity") != expected_preparation
        or manifest.get("final_source_manifest_sha256") != final_source["manifest_sha256"]
        or manifest.get("launch_envelope_sha256") != final_source["envelope_sha256"]
        or manifest.get("launch_commit") != final_source["launch_commit"]
        or manifest.get("bundle_sha256") != final_source["bundle_sha256"]
    ):
        raise ValueError("Prepared run is bound to a different operational config")
    verify_hash_inventory(run_root, manifest["prepared_artifact_sha256"])
    combined_path = run_root / "merge_manifest.json"
    if combined_path.exists():
        verify_manifest_sidecar(combined_path)
        existing = json.loads(combined_path.read_text(encoding="utf-8"))
        expected_existing = {
            "schema_id": "sr_v2_heavy_sensitivity_merge/v1",
            "run_id": spec.run_id,
            "operational_config_sha256": config_hash,
            "preparation_identity": expected_preparation,
            "final_source_manifest_sha256": final_source["manifest_sha256"],
            "launch_envelope_sha256": final_source["envelope_sha256"],
            "launch_commit": final_source["launch_commit"],
            "bundle_sha256": final_source["bundle_sha256"],
        }
        drift = {key: (value, existing.get(key)) for key, value in expected_existing.items() if existing.get(key) != value}
        if drift:
            raise ValueError(f"Existing merge identity mismatch: {drift}")
        verify_hash_inventory(run_root, existing["artifact_sha256"])
        print(json.dumps(existing, sort_keys=True))
        return existing

    primary = pd.read_csv(root / "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv").set_index("parameter")
    parameters = list(spec.comparison["primary_parameters"])
    if sorted(primary.index.intersection(parameters)) != sorted(parameters):
        raise ValueError("Frozen primary summary does not contain all comparison parameters")
    profile_evidence: list[dict] = []
    combined_artifacts: dict[str, str] = {}
    for profile in spec.profiles:
        record = _profile_record(manifest, profile.profile_id)
        profile_root = run_root / "profiles" / profile.profile_id
        expected_chain_dirs = [f"chain_{chain_id:02d}" for chain_id in range(1, 5)]
        actual_chain_dirs = sorted(path.name for path in (profile_root / "chains").glob("chain_*") if path.is_dir())
        if actual_chain_dirs != expected_chain_dirs:
            raise ValueError(f"Profile {profile.profile_id} requires exactly four chain directories; found {actual_chain_dirs}")
        merged_root = profile_root / "merged"
        reusable = _load_reusable_merge(merged_root, profile.profile_id)
        if reusable is not None:
            expected_reusable = {
                "schema_id": "sr_v2_heavy_sensitivity_profile_merge/v1",
                "run_id": spec.run_id,
                "profile": profile.profile_id,
                "operational_config_sha256": config_hash,
                "preparation_identity": expected_preparation,
                "final_source_manifest_sha256": final_source["manifest_sha256"],
                "launch_envelope_sha256": final_source["envelope_sha256"],
                "launch_commit": final_source["launch_commit"],
                "bundle_sha256": final_source["bundle_sha256"],
            }
            drift = {key: (value, reusable.get(key)) for key, value in expected_reusable.items() if reusable.get(key) != value}
            if drift:
                raise ValueError(f"Existing profile merge identity mismatch: {drift}")
            profile_evidence.append(reusable)
            for relative, digest in reusable["artifact_sha256"].items():
                combined_artifacts[(merged_root.relative_to(run_root) / relative).as_posix()] = digest
            combined_artifacts[(merged_root.relative_to(run_root) / "profile_merge.json").as_posix()] = sha256_file(merged_root / "profile_merge.json")
            continue
        draws_frames: list[pd.DataFrame] = []
        validation_frames: list[pd.DataFrame] = []
        chain_records: list[dict] = []
        for assignment_record in record["chains"]:
            chain_id = int(assignment_record["chain"])
            chain_dir = profile_root / "chains" / f"chain_{chain_id:02d}"
            status = json.loads((chain_dir / "chain_status.json").read_text(encoding="utf-8"))
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
                ] + sorted(path.relative_to(chain_dir).as_posix() for path in (chain_dir / "checkpoints").iterdir() if path.is_file()),
                expected_parameter_schema=record["parameter_schema"],
                expected_years=record["included_years"],
                expected_terminal_iteration=spec.iterations_per_chain,
                target_identity=assignment_record["checkpoint_target_identity"],
            )
            if list(status.get("parameter_schema", [])) != list(record["parameter_schema"]):
                raise ValueError(f"Chain {chain_id} parameter schema differs from prepared target")
            draws = pd.read_parquet(chain_dir / "draws_params.parquet")
            validate_chain_draws(
                draws,
                chain_id=chain_id,
                parameter_schema=record["parameter_schema"],
                retained_draws=spec.retained_draws_per_chain,
                burn_in=spec.burn_in,
                thin=spec.thin,
            )
            validation = pd.read_csv(chain_dir / "latent_validation.csv")
            failures = int((~validation["passed"].astype(bool)).sum())
            draws_frames.append(draws)
            validation_frames.append(validation)
            chain_records.append(
                {
                    "chain_id": chain_id,
                    "status": status["status"],
                    "saved_draws": int(status["saved_draws"]),
                    "hashes_verified": True,
                    "constraint_failures": failures,
                    "parameter_schema": list(status["parameter_schema"]),
                    "included_years": list(status["included_years"]),
                    "profile_fingerprint": status["profile_fingerprint"],
                    "chain_status_sha256": sha256_file(chain_dir / "chain_status.json"),
                    "checkpoint_target_identity": assignment_record["checkpoint_target_identity"],
                }
            )
        draws = pd.concat(draws_frames, ignore_index=True)
        diagnostics = diagnostics_table(draws, output_dir=None)
        comparisons = _comparison_rows(profile, draws, primary, parameters)
        validate_diagnostics_table(diagnostics, parameter_schema=record["parameter_schema"])
        validate_comparison_table(comparisons, profile_id=profile.profile_id)
        validation = pd.concat(validation_frames, ignore_index=True)
        temporary = Path(tempfile.mkdtemp(prefix=".merge-", dir=profile_root))
        try:
            _atomic_parquet(temporary / "parameter_draws.parquet", draws)
            diagnostics.to_csv(temporary / "parameter_diagnostics.csv", index=False)
            comparisons.to_csv(temporary / "primary_comparison.csv", index=False)
            validation.to_csv(temporary / "latent_validation.csv.gz", index=False, compression="gzip")
            if profile.model == "pandemic_interaction":
                _atomic_parquet(temporary / "period_irrs.parquet", derive_period_irrs(draws))
            files = [path.relative_to(temporary).as_posix() for path in temporary.iterdir() if path.is_file()]
            inventory = artifact_inventory(temporary, files)
            evidence = {
                "schema_id": "sr_v2_heavy_sensitivity_profile_merge/v1",
                "run_id": spec.run_id,
                "profile": profile.profile_id,
                "status": "merged_not_gated",
                "operational_config_sha256": sha256_file(config_path),
                "preparation_identity": manifest["preparation_identity"],
                "final_source_manifest_sha256": final_source["manifest_sha256"],
                "launch_envelope_sha256": final_source["envelope_sha256"],
                "launch_commit": final_source["launch_commit"],
                "bundle_sha256": final_source["bundle_sha256"],
                "primary_summary_sha256": spec.source_authorities["outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv"],
                "parameter_schema": list(record["parameter_schema"]),
                "included_years": list(record["included_years"]),
                "chain_records": chain_records,
                "comparison_parameters": parameters,
                "artifact_sha256": inventory,
                "interpretation_boundary": spec.interpretation_boundary,
            }
            atomic_json(temporary / "profile_merge.json", evidence)
            evidence_path = temporary / "profile_merge.json"
            evidence_path.with_name(f"{evidence_path.name}.sha256").write_text(
                sha256_file(evidence_path) + "\n", encoding="ascii", newline="\n"
            )
            publish_directory_no_clobber(temporary, merged_root)
        except BaseException:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise
        profile_evidence.append(evidence)
        for relative, digest in inventory.items():
            combined_artifacts[(merged_root.relative_to(run_root) / relative).as_posix()] = digest
        combined_artifacts[(merged_root.relative_to(run_root) / "profile_merge.json").as_posix()] = sha256_file(merged_root / "profile_merge.json")
    combined = {
        "schema_id": "sr_v2_heavy_sensitivity_merge/v1",
        "run_id": spec.run_id,
        "status": "merged_not_gated",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preparation_identity": manifest["preparation_identity"],
        "operational_config_sha256": sha256_file(config_path),
        "final_source_manifest_sha256": final_source["manifest_sha256"],
        "launch_envelope_sha256": final_source["envelope_sha256"],
        "launch_commit": final_source["launch_commit"],
        "bundle_sha256": final_source["bundle_sha256"],
        "profiles": profile_evidence,
        "artifact_sha256": dict(sorted(combined_artifacts.items())),
        "interpretation_boundary": spec.interpretation_boundary,
    }
    atomic_json(combined_path, combined)
    combined_path.with_name(f"{combined_path.name}.sha256").write_text(
        sha256_file(combined_path) + "\n", encoding="ascii", newline="\n"
    )
    print(json.dumps(combined, sort_keys=True))
    return combined


def main() -> None:
    args = build_parser().parse_args()
    merge(args.run_id)


if __name__ == "__main__":
    main()
