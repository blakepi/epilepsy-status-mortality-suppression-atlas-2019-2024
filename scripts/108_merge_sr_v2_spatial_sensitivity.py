#!/usr/bin/env python3
"""Merge one immutable SR-v2 BYM2 epoch and write its pre-gate evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.diagnostics import spatial_diagnostics_table
from bayes_constrained.model import active_prior_specification, make_design
from bayes_constrained.spatial_bym2 import (
    build_bym2_graph,
    load_spatial_checkpoint,
    merge_spatial_draw_chunks,
)
from bayes_constrained.spatial_pipeline import (
    COMPARISON_ROWS,
    EPOCH_CONTRACT,
    RUN_ID,
    atomic_json,
    canonical_json_bytes,
    comparison_candidate_bytes,
    load_spatial_execution_spec,
    load_verified_chain_status,
    publish_directory_no_clobber,
    set_canonical_hold,
    sha256_file,
    spatial_run_root,
    validate_benchmark_evidence,
    validate_prepared_source_envelope,
    verify_hash_inventory,
    verify_sha256_sidecar,
)


CONFIG_PATH = ROOT / "config/sr_v2_spatial_sensitivity_execution.yaml"


def _write_sidecar(path: Path) -> None:
    temporary = path.with_name(f".{path.name}.sha256.{os.getpid()}.tmp")
    temporary.write_bytes((sha256_file(path) + "\n").encode("ascii"))
    os.replace(temporary, path.with_name(path.name + ".sha256"))


def _runtime_target(
    root: Path, validation: Mapping[str, Any]
) -> tuple[pd.DataFrame, Any, Any]:
    manifest = validation["manifest"]
    prepared = Path(str(validation["prepared_root"]))
    frame = pd.read_parquet(prepared / str(manifest["model_frame"]))
    adjacency = (
        "outputs/scientific_reports_v2/spatial_residual_diagnostics/"
        "county_adjacency2024.txt"
    )
    graph = build_bym2_graph(
        frame,
        root / adjacency,
        expected_sha256=manifest["source_authorities"][adjacency],
    )
    if graph.contract_sha256 != manifest["graph_contract_sha256"]:
        raise ValueError("Runtime graph does not match immutable preparation")
    return frame, make_design(frame, spatial_graph=graph), active_prior_specification()


def _load_status(chain_root: Path) -> dict[str, Any]:
    status = load_verified_chain_status(
        chain_root.parent.parent,
        int(chain_root.name.removeprefix("chain_")),
    )
    if status is None:
        raise ValueError("Completed chain lacks immutable status")
    return status


def _verify_loop_evidence(
    chain_root: Path,
    *,
    status: Mapping[str, Any],
    extension_epoch: int,
    expected_draws: int,
) -> dict[str, int | str]:
    if status.get("executor_builder") != "exact_public_chain_loop":
        raise ValueError("Production merge requires actual public-loop evidence")
    records: list[dict[str, object]] = []
    count_failures = 0
    spatial_failures = 0
    for epoch in range(extension_epoch + 1):
        root = chain_root / f"evidence/epoch_{epoch}"
        manifests = sorted(root.glob("attempt_*/attempt_evidence.json"))
        if not manifests:
            raise ValueError("Public-loop evidence manifest is missing")
        for manifest_path in manifests:
            verify_sha256_sidecar(manifest_path)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            ledger = manifest_path.parent / str(manifest.get("ledger_path", ""))
            if sha256_file(ledger) != manifest.get("ledger_sha256"):
                raise ValueError("Public-loop evidence ledger hash mismatch")
            if manifest.get("start_saved_draws") != len(records):
                raise ValueError("Public-loop evidence attempts are not contiguous")
            lines = ledger.read_bytes().splitlines()
            if len(lines) != manifest.get("record_count"):
                raise ValueError("Public-loop evidence record count mismatch")
            for line in lines:
                record = json.loads(line)
                unsigned = {
                    key: record[key]
                    for key in record
                    if key != "assertion_sha256"
                }
                if record.get("assertion_sha256") != hashlib.sha256(
                    canonical_json_bytes(unsigned)
                ).hexdigest():
                    raise ValueError("Public-loop assertion digest mismatch")
                count_failures += int(
                    record.get("count_constraints_asserted") is not True
                )
                spatial_failures += int(
                    record.get("spatial_constraints_asserted") is not True
                )
                records.append(record)
    if len(records) != expected_draws:
        raise ValueError("Public-loop assertion ledger draw count mismatch")
    for draw_id, record in enumerate(records, start=1):
        if (
            record.get("chain_id") != status.get("chain_id")
            or record.get("draw_id") != draw_id
            or record.get("cumulative_iteration") != 45_000 + 30 * draw_id
        ):
            raise ValueError("Public-loop assertion schedule mismatch")
    cumulative = hashlib.sha256(
        b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    ).hexdigest()
    status_evidence = status.get("retained_assertion_evidence")
    if (
        not isinstance(status_evidence, Mapping)
        or status_evidence.get("records") != expected_draws
        or status_evidence.get("ledger_sha256") != cumulative
    ):
        raise ValueError("Chain status does not bind cumulative loop evidence")
    return {
        "records": len(records),
        "count_constraint_failures": count_failures,
        "spatial_constraint_failures": spatial_failures,
        "ledger_sha256": cumulative,
    }


def _merge_raw_chains(
    staging: Path,
    *,
    run_root: Path,
    statuses: list[dict[str, Any]],
    frame: pd.DataFrame,
    design: Any,
    prior: Any,
) -> tuple[pd.DataFrame, dict[str, np.ndarray], list[dict[str, Any]]]:
    scalar_frames: list[pd.DataFrame] = []
    spatial_parts: dict[str, list[np.ndarray]] = {
        "chain_id": [],
        "extension_epoch": [],
        "draw_id": [],
        "structured": [],
        "unstructured": [],
    }
    loaded_checkpoints: list[dict[str, Any]] = []
    for status in statuses:
        chain_id = int(status["chain_id"])
        chain_root = run_root / f"chains/chain_{chain_id:02d}"
        checkpoint = chain_root / str(status["latest_checkpoint"])
        loaded = load_spatial_checkpoint(
            checkpoint,
            expected_identity=status["identity"],
            frame=frame,
            design=design,
            intercept_mean=float.fromhex(
                str(status["identity"]["target"]["intercept_mean_float_hex"])
            ),
            prior=prior,
            chunk_dir=chain_root / "chunks",
        )
        loaded_checkpoints.append(loaded)
        per_chain = staging / f".chain_{chain_id:02d}"
        per_chain.mkdir()
        scalar_path = per_chain / "scalar.parquet"
        spatial_path = per_chain / "spatial.npz"
        merge_spatial_draw_chunks(
            chain_root / "chunks",
            records=loaded["committed_chunks"],
            scalar_output=scalar_path,
            spatial_output=spatial_path,
            graph=design.spatial_graph,
        )
        scalar_frames.append(pd.read_parquet(scalar_path))
        with np.load(spatial_path, allow_pickle=False) as arrays:
            for key in spatial_parts:
                spatial_parts[key].append(arrays[key].copy())
        shutil.rmtree(per_chain)
    scalar = pd.concat(scalar_frames, ignore_index=True).sort_values(
        ["chain_id", "draw_id", "parameter"], kind="stable"
    ).reset_index(drop=True)
    spatial = {
        key: np.concatenate(parts, axis=0)
        for key, parts in spatial_parts.items()
    }
    order = np.lexsort((spatial["draw_id"], spatial["chain_id"]))
    spatial = {key: value[order] for key, value in spatial.items()}
    return scalar, spatial, loaded_checkpoints


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    frame.to_parquet(path, index=False)


def _write_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    with path.open("wb") as handle:
        np.savez_compressed(handle, **arrays)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def _county_summary(
    *,
    scalar: pd.DataFrame,
    spatial: Mapping[str, np.ndarray],
    diagnostics: pd.DataFrame,
    graph: Any,
) -> pd.DataFrame:
    scalar_index = scalar.set_index(["chain_id", "draw_id", "parameter"])["value"]
    keys = list(zip(spatial["chain_id"].tolist(), spatial["draw_id"].tolist()))
    sigma = np.asarray(
        [scalar_index.loc[(chain, draw, "sigma_county")] for chain, draw in keys],
        dtype=np.float64,
    )
    phi = np.asarray(
        [scalar_index.loc[(chain, draw, "phi_structured")] for chain, draw in keys],
        dtype=np.float64,
    )
    diag = diagnostics.set_index("parameter")
    rows: list[dict[str, object]] = []
    for index, county in enumerate(graph.counties):
        structured = spatial["structured"][:, index]
        unstructured = spatial["unstructured"][:, index]
        if graph.singleton_mask[index] and not np.array_equal(
            structured, np.zeros_like(structured)
        ):
            raise ValueError("Singleton structured draws must be exactly zero")
        combined = sigma * (
            np.sqrt(phi) * structured + np.sqrt(1.0 - phi) * unstructured
        )
        if not np.isfinite(combined).all():
            raise ValueError("Combined county draws contain nonfinite values")
        diagnostic = diag.loc[f"county_combined[{county}]"]
        lower, upper = np.quantile(
            combined, [0.025, 0.975], method="linear"
        )
        rows.append(
            {
                "county_fips": county,
                "component_id": int(graph.component_id[index]),
                "singleton": bool(graph.singleton_mask[index]),
                "structured_mean": float(np.mean(structured, dtype=np.float64)),
                "unstructured_mean": float(np.mean(unstructured, dtype=np.float64)),
                "combined_mean": float(np.mean(combined, dtype=np.float64)),
                "combined_lower_95": float(lower),
                "combined_upper_95": float(upper),
                "r_hat": float(diagnostic["r_hat"]),
                "ess_bulk": float(diagnostic["ess_bulk"]),
                "ess_tail": float(diagnostic["ess_tail"]),
            }
        )
    return pd.DataFrame(rows)


def _threshold_summary(diagnostics: pd.DataFrame) -> dict[str, object]:
    focus = [*COMPARISON_ROWS, "sigma_county", "phi_structured"]
    focus_rows = diagnostics.loc[diagnostics["parameter"].isin(focus)]
    if len(focus_rows) != 10:
        raise ValueError("Diagnostics omit primary plus spatial hyperparameters")
    all_pass = bool(
        diagnostics["r_hat"].le(1.05).all()
        and diagnostics["ess_bulk"].ge(100.0).all()
        and diagnostics["ess_tail"].ge(100.0).all()
    )
    focus_pass = bool(
        focus_rows["r_hat"].le(1.03).all()
        and focus_rows["ess_bulk"].ge(400.0).all()
        and focus_rows["ess_tail"].ge(400.0).all()
    )
    return {
        "all_stochastic_and_combined_county_passed": all_pass,
        "primary_plus_spatial_hyperparameters_passed": focus_pass,
        "passed": all_pass and focus_pass,
        "thresholds_inclusive": True,
        "rhat_all_max": float(diagnostics["r_hat"].max()),
        "bulk_ess_all_min": float(diagnostics["ess_bulk"].min()),
        "tail_ess_all_min": float(diagnostics["ess_tail"].min()),
        "rhat_focus_max": float(focus_rows["r_hat"].max()),
        "bulk_ess_focus_min": float(focus_rows["ess_bulk"].min()),
        "tail_ess_focus_min": float(focus_rows["ess_tail"].min()),
    }


def _verify_existing(path: Path, expected_epoch: int) -> dict[str, Any]:
    manifest_path = path / "pre_gate_manifest.json"
    verify_sha256_sidecar(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("extension_epoch") != expected_epoch:
        raise ValueError("Existing merge epoch identity mismatch")
    verify_hash_inventory(
        path,
        manifest["artifact_sha256"],
        exact_files=True,
        allowed_files=(
            "pre_gate_manifest.json",
            "pre_gate_manifest.json.sha256",
        ),
    )
    return manifest


def merge_epoch(
    *,
    extension_epoch: int,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    output_base_override: Path | None = None,
    prepared_validator: Callable[..., Mapping[str, Any]] = validate_prepared_source_envelope,
    runtime_loader: Callable[[Path, Mapping[str, Any]], tuple[pd.DataFrame, Any, Any]] = _runtime_target,
    merged_input_loader: Callable[..., tuple[pd.DataFrame, dict[str, np.ndarray], list[dict[str, Any]]]] | None = None,
    diagnostics_builder: Callable[..., pd.DataFrame] = spatial_diagnostics_table,
    benchmark_validator: Callable[..., Mapping[str, Any]] = validate_benchmark_evidence,
    evidence_validator: Callable[..., Mapping[str, Any]] = _verify_loop_evidence,
    bounded_test_mode: bool = False,
) -> dict[str, Any]:
    root = Path(root).resolve()
    set_canonical_hold(
        root,
        reason="merge_not_verified",
        stage="merge",
        extension_epoch=extension_epoch,
        output_base_override=output_base_override,
    )
    if isinstance(extension_epoch, bool) or extension_epoch not in range(4):
        raise ValueError("Merge extension epoch must be exactly 0..3")
    spec = load_spatial_execution_spec(config_path)
    validation = prepared_validator(
        root,
        config_path=config_path,
        output_base_override=output_base_override,
    )
    manifest = validation["manifest"]
    run_root = spatial_run_root(root, output_base_override)
    merge_root = run_root / f"epochs/epoch_{extension_epoch}/merge"
    if os.path.lexists(merge_root):
        return _verify_existing(merge_root, extension_epoch)
    statuses = [
        _load_status(run_root / f"chains/chain_{chain_id:02d}")
        for chain_id in range(1, 5)
    ]
    expected = EPOCH_CONTRACT[extension_epoch]
    fingerprints: set[str] = set()
    for assignment, status in zip(spec.chain_map, statuses, strict=True):
        if (
            status.get("status") != "completed"
            or status.get("chain_id") != assignment.chain_id
            or status.get("array_index") != assignment.array_index
            or status.get("extension_epoch") != extension_epoch
            or status.get("iterations") != expected["iterations"]
            or status.get("retained_draws") != expected["draws"]
            or status.get("chunks") != expected["chunks"]
            or status.get("preparation_identity") != manifest["preparation_identity"]
            or status.get("seeds")
            != {
                "chain_seed": assignment.chain_seed,
                "allocation_initialization_seed": assignment.allocation_initialization_seed,
                "spatial_initialization_seed": assignment.spatial_initialization_seed,
            }
        ):
            raise ValueError("Merge requires four exact completed chain statuses")
        fingerprints.add(str(status.get("chain_fingerprint")))
    if len(fingerprints) != 4:
        raise ValueError("Merge refuses copied or duplicate chain fingerprints")
    evidence_rows = [
        evidence_validator(
            run_root / f"chains/chain_{chain_id:02d}",
            status=statuses[chain_id - 1],
            extension_epoch=extension_epoch,
            expected_draws=expected["draws"],
        )
        for chain_id in range(1, 5)
    ]
    count_constraint_failures = sum(
        int(row["count_constraint_failures"]) for row in evidence_rows
    )
    spatial_constraint_failures = sum(
        int(row["spatial_constraint_failures"]) for row in evidence_rows
    )
    benchmark = benchmark_validator(
        run_root,
        preparation_identity=manifest["preparation_identity"],
        target_fingerprints=[row["target_fingerprint"] for row in manifest["chain_mapping"]],
        launch_envelope_sha256=manifest["launch_envelope_sha256"],
        final_source_manifest_sha256=manifest["final_source_manifest_sha256"],
    )
    frame, design, prior = runtime_loader(root, validation)
    merge_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".merge-epoch-{extension_epoch}-", dir=merge_root.parent
        )
    )
    try:
        if merged_input_loader is None:
            scalar, spatial, checkpoints = _merge_raw_chains(
                staging,
                run_root=run_root,
                statuses=statuses,
                frame=frame,
                design=design,
                prior=prior,
            )
        else:
            scalar, spatial, checkpoints = merged_input_loader(
                staging=staging,
                run_root=run_root,
                statuses=statuses,
                frame=frame,
                design=design,
                prior=prior,
            )
        production_dependencies = (
            merged_input_loader is None
            and prepared_validator is validate_prepared_source_envelope
            and runtime_loader is _runtime_target
            and diagnostics_builder is spatial_diagnostics_table
            and benchmark_validator is validate_benchmark_evidence
            and evidence_validator is _verify_loop_evidence
            and not bounded_test_mode
        )
        builder = (
            "verified_raw_chunk_merge"
            if production_dependencies
            else "injected_bounded_test_builder"
        )
        if not bounded_test_mode and not production_dependencies:
            raise ValueError("Injected merge dependencies are test-only")
        parameter_schema = manifest["parameter_schema"]
        diagnostics = diagnostics_builder(
            scalar,
            spatial,
            design.spatial_graph,
            parameter_schema=parameter_schema,
            count_constraint_failures=count_constraint_failures,
            spatial_constraint_failures=spatial_constraint_failures,
        )
        if list(diagnostics.columns) != [
            "parameter",
            "r_hat",
            "ess_bulk",
            "ess_tail",
            "arviz_version",
            "constraint_failures",
        ]:
            raise ValueError("Spatial diagnostics schema changed")
        if not diagnostics["arviz_version"].eq("1.2.0").all():
            raise ValueError("Spatial diagnostics require ArviZ 1.2.0")
        production_shape = (
            len(design.spatial_graph.counties) == 3_142
            and len(parameter_schema) == 71
            and len(diagnostics) == 9_483
        )
        if not bounded_test_mode and not production_shape:
            raise ValueError("Production merge requires 3,142 counties, 71 parameters, and 9,483 diagnostics")
        _write_parquet(staging / "posterior_parameter_draws.parquet", scalar)
        _write_npz(staging / "draws_spatial.npz", spatial)
        _write_csv(staging / "spatial_diagnostics.csv", diagnostics)
        county = _county_summary(
            scalar=scalar,
            spatial=spatial,
            diagnostics=diagnostics,
            graph=design.spatial_graph,
        )
        _write_csv(staging / "county_effect_summary.csv", county)
        acceptance_rows: list[dict[str, object]] = []
        for status, loaded in zip(statuses, checkpoints, strict=True):
            for parameter in sorted(loaded["proposed"]):
                proposed = int(loaded["proposed"][parameter])
                accepted = int(loaded["accepted"][parameter])
                acceptance_rows.append(
                    {
                        "chain_id": status["chain_id"],
                        "transition": parameter,
                        "accepted": accepted,
                        "proposed": proposed,
                        "acceptance_rate": accepted / proposed if proposed else np.nan,
                    }
                )
        _write_csv(staging / "acceptance_summary.csv", pd.DataFrame(acceptance_rows))
        threshold = _threshold_summary(diagnostics)
        constraint = {
            "schema_id": "sr_v2_spatial_constraint_summary/v1",
            "count_constraint_failures": count_constraint_failures,
            "spatial_constraint_failures": spatial_constraint_failures,
            "retained_draw_assertions_per_chain": expected["draws"],
            "historical_latent_y_stored": False,
            "independent_historical_y_reconstruction_possible": False,
        }
        atomic_json(staging / "constraint_summary.json", constraint)
        atomic_json(
            staging / "spatial_diagnostics_summary.json",
            {
                "schema_id": "sr_v2_spatial_diagnostics_summary/v1",
                "extension_epoch": extension_epoch,
                "rows": len(diagnostics),
                "arviz_version": "1.2.0",
                **threshold,
            },
        )
        primary = pd.read_csv(
            root
            / "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv",
            float_precision="round_trip",
        )
        candidate = comparison_candidate_bytes(primary, scalar)
        (staging / "primary_vs_spatial.candidate.csv").write_bytes(candidate)
        artifact_hashes = {
            path.relative_to(staging).as_posix(): sha256_file(path)
            for path in sorted(staging.rglob("*"))
            if path.is_file()
        }
        pre_gate = {
            "schema_id": "sr_v2_spatial_pre_gate_manifest/v1",
            "run_id": RUN_ID,
            "model_id": spec.model_id,
            "extension_epoch": extension_epoch,
            "iterations_per_chain": expected["iterations"],
            "draws_per_chain": expected["draws"],
            "chunks_per_chain": expected["chunks"],
            "chains": 4,
            "preparation_identity": manifest["preparation_identity"],
            "launch_envelope_sha256": manifest["launch_envelope_sha256"],
            "final_source_manifest_sha256": manifest["final_source_manifest_sha256"],
            "benchmark_report_sha256": benchmark["report_sha256"],
            "chain_fingerprints": sorted(fingerprints),
            "parameter_schema_rows": len(parameter_schema),
            "county_rows": len(county),
            "diagnostic_rows": len(diagnostics),
            "arviz_version": "1.2.0",
            "threshold_summary": threshold,
            "count_constraint_failures": count_constraint_failures,
            "spatial_constraint_failures": spatial_constraint_failures,
            "retained_assertion_ledger_sha256": {
                str(status["chain_id"]): row["ledger_sha256"]
                for status, row in zip(statuses, evidence_rows, strict=True)
            },
            "comparison_rows": list(COMPARISON_ROWS),
            "candidate_sha256": sha256_file(
                staging / "primary_vs_spatial.candidate.csv"
            ),
            "artifact_sha256": artifact_hashes,
            "builder": builder,
            "bounded_test_mode": bool(bounded_test_mode),
            "production_shape": production_shape,
            "submission_authorized": False,
        }
        manifest_path = staging / "pre_gate_manifest.json"
        atomic_json(manifest_path, pre_gate)
        _write_sidecar(manifest_path)
        publish_directory_no_clobber(
            staging, merge_root, commit_marker="pre_gate_manifest.json.sha256"
        )
        return pre_gate
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        set_canonical_hold(
            root,
            reason="merge_failed",
            stage="merge",
            extension_epoch=extension_epoch,
            output_base_override=output_base_override,
        )
        raise


def main() -> None:
    set_canonical_hold(ROOT, reason="merge_cli_started", stage="merge")
    parser = argparse.ArgumentParser()
    parser.add_argument("--extension-epoch", required=True, type=int)
    args = parser.parse_args()
    merge_epoch(extension_epoch=args.extension_epoch)


if __name__ == "__main__":
    main()
