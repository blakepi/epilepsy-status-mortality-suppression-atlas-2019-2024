#!/usr/bin/env python3
"""Implementation-independent verifier, release writer, and gate-last publisher."""

from __future__ import annotations

import argparse
import base64
import csv
import ctypes
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.special import expit, gammaln


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "sr-v2-spatial-sensitivity-20260818-v1"
MODEL_ID = "sr-v2-primary-nb2-bym2-v1"
OUTPUT_ROOT = Path("outputs/scientific_reports_v2/spatial_sensitivity")
PROTECTED_TREES = (
    "outputs/scientific_reports_v2/production_8chain",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics",
)
CONFIG_PATH = ROOT / "config/sr_v2_spatial_sensitivity_execution.yaml"
EPOCH_CONTRACT = {
    0: {"iterations": 180_000, "draws": 4_500, "chunks": 18},
    1: {"iterations": 270_000, "draws": 7_500, "chunks": 30},
    2: {"iterations": 360_000, "draws": 10_500, "chunks": 42},
    3: {"iterations": 450_000, "draws": 13_500, "chunks": 54},
}
CHAIN_SEEDS = (74291, 74292, 74293, 74294)
ALLOCATION_SEEDS = (74251, 74252, 74253, 74254)
SPATIAL_SEEDS = (74261, 74262, 74263, 74264)
REQUIRED_SOURCE_PATHS = (
    "config/sr_v2_spatial_sensitivity_execution.yaml",
    "src/bayes_constrained/__init__.py",
    "src/bayes_constrained/paths.py",
    "src/bayes_constrained/data.py",
    "src/bayes_constrained/constraints.py",
    "src/bayes_constrained/target_density.py",
    "src/bayes_constrained/model.py",
    "src/bayes_constrained/heatbath.py",
    "src/bayes_constrained/interval_paths.py",
    "src/bayes_constrained/sampler.py",
    "src/bayes_constrained/diagnostics.py",
    "src/bayes_constrained/spatial_bym2.py",
    "src/bayes_constrained/spatial_pipeline.py",
    "scripts/106_prepare_sr_v2_spatial_sensitivity.py",
    "scripts/107_run_sr_v2_spatial_sensitivity_chain.py",
    "scripts/108_merge_sr_v2_spatial_sensitivity.py",
    "scripts/109_gate_sr_v2_spatial_sensitivity.py",
    "hpc/wahab/stage_sr_v2_spatial_sensitivity_to_scratch.sh",
    "hpc/wahab/sync_sr_v2_spatial_sensitivity_results_home.sh",
    "hpc/wahab/slurm/65_sr_v2_spatial_sensitivity_benchmark.sbatch",
    "hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch",
    "hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch",
    "hpc/wahab/submit_sr_v2_spatial_sensitivity.sh",
    "hpc/wahab/resume_sr_v2_spatial_sensitivity.sh",
)
TARGET_EXACT_FIELDS = {
    "schema_id", "run_id", "model_id", "config_sha256",
    "input_manifest_sha256", "source_manifest_sha256",
    "model_frame_semantic_sha256", "graph_contract_sha256", "likelihood",
    "prior", "intercept_mean_rule", "intercept_mean_float_hex",
    "design_schema", "parameter_schema", "extension_epoch",
    "extension_authorization_sha256",
}
CHECKPOINT_EXACT_FIELDS = {
    "schema_version", "run_id", "model_id", "target_fingerprint",
    "chain_fingerprint", "extension_epoch", "job_attempt", "chain_id", "seeds",
    "current_state", "rng_state", "current_target", "iteration", "saved_draws",
    "accepted", "proposed", "committed_chunks", "pending_buffers",
    "adaptation_state", "next_draw_id", "output_positions",
}
COUNTER_FIELDS = {
    "transfer", "interval_transfer", "interval_path", "swap_2x2", "cycle_swap",
    "blocked_refresh", "beta", "state", "year", "log_sigma_state",
    "log_sigma_year", "log_kappa", "spatial_hyperparameters", "mala",
}
CHAIN_STATUS_EXACT_FIELDS = {
    "schema_id", "run_id", "model_id", "preparation_identity",
    "launch_envelope_sha256", "final_source_manifest_sha256", "chain_id",
    "array_index", "extension_epoch", "job_attempt", "status", "iterations",
    "retained_draws", "chunks", "seeds", "identity", "target_fingerprint",
    "chain_fingerprint", "latest_checkpoint", "latest_checkpoint_sha256",
    "artifact_sha256", "executor_builder", "retained_assertion_evidence",
    "failure_category", "retryable", "updated_utc", "submission_authorized",
}
COMPARISON_ROWS = (
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
    "z_pct_age65",
    "z_pct_male",
)
COMPARISON_FIELDS = (
    "parameter",
    "scale",
    "primary_mean",
    "primary_lower_95",
    "primary_upper_95",
    "spatial_mean",
    "spatial_lower_95",
    "spatial_upper_95",
    "absolute_change",
    "relative_change",
    "interval_overlap",
)
PREPARED_MANIFEST_EXACT_FIELDS = {
    "schema_id", "run_id", "model_id", "operational_config_sha256",
    "launch_envelope_sha256", "final_source_manifest_sha256", "launch_commit",
    "bundle_sha256", "joint_regression_evidence_sha256", "preparation_identity",
    "generated_utc", "status", "production_eligible", "builder_provenance",
    "input_manifest", "input_manifest_sha256", "source_authorities",
    "graph_contract", "graph_contract_sha256", "model_frame", "model_frame_sha256",
    "model_frame_semantic_sha256", "parameter_schema", "protected_tree_manifest",
    "protected_tree_manifest_sha256", "chain_mapping", "prepared_artifact_sha256",
    "interpretation_boundary", "submission_authorized",
}
INPUT_MANIFEST_EXACT_FIELDS = {
    "schema_id", "run_id", "operational_config_sha256", "source_authorities",
    "launch_envelope_sha256", "final_source_manifest_sha256", "launch_commit",
    "bundle_sha256", "joint_regression_evidence_sha256",
    "source_model_frame_sha256", "prepared_model_frame_sha256",
    "model_frame_semantic_sha256", "graph_contract_sha256", "graph_artifact_sha256",
}
PRE_GATE_EXACT_FIELDS = {
    "schema_id", "run_id", "model_id", "extension_epoch", "iterations_per_chain",
    "draws_per_chain", "chunks_per_chain", "chains", "preparation_identity",
    "launch_envelope_sha256", "final_source_manifest_sha256",
    "benchmark_report_sha256", "chain_fingerprints", "parameter_schema_rows",
    "county_rows", "diagnostic_rows", "arviz_version", "threshold_summary",
    "count_constraint_failures", "spatial_constraint_failures",
    "retained_assertion_ledger_sha256", "comparison_rows", "candidate_sha256",
    "artifact_sha256", "builder", "bounded_test_mode", "production_shape",
    "submission_authorized",
}
VERIFICATION_EXACT_FIELDS = {
    "schema_id", "run_id", "model_id", "extension_epoch", "preparation_identity",
    "launch_envelope_sha256", "final_source_manifest_sha256",
    "benchmark_report_sha256", "pre_gate_manifest_sha256", "passed",
    "source_checks", "graph_checks", "chain_checks", "diagnostic_checks",
    "comparison_checks", "benchmark_checks", "protected_tree_checks",
    "artifact_snapshot", "artifact_snapshot_sha256",
    "submission_authorized",
}
RELEASE_EXACT_FIELDS = {
    "schema_id", "run_id", "model_id", "extension_epoch", "preparation_identity",
    "launch_envelope_sha256", "final_source_manifest_sha256",
    "benchmark_report_sha256", "pre_gate_manifest_sha256",
    "independent_verification_sha256", "verification_convergence_passed",
    "verification_artifact_snapshot", "verification_artifact_snapshot_sha256",
    "artifacts", "artifact_inventory_sha256", "planned_outputs", "excludes",
    "submission_authorized",
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_hash(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def _sidecar(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    if (
        not path.is_file()
        or path.is_symlink()
        or not sidecar.is_file()
        or sidecar.is_symlink()
    ):
        raise ValueError(f"Missing or unsafe manifest/sidecar: {path}")
    raw_sidecar = sidecar.read_bytes()
    if len(raw_sidecar) != 65 or raw_sidecar[-1:] != b"\n":
        raise ValueError(f"Noncanonical SHA-256 sidecar: {sidecar}")
    try:
        expected_text = raw_sidecar[:64].decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError(f"Noncanonical SHA-256 sidecar: {sidecar}") from error
    expected = _require_hash(expected_text, "sidecar")
    actual = _sha(path)
    if actual != expected:
        raise ValueError(f"Manifest SHA-256 mismatch: {path}")
    return actual


def _safe(base: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("Artifact paths must be nonempty strings")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Artifact path escapes its immutable root")
    path = (base / rel).resolve(strict=False)
    if not path.is_relative_to(base.resolve()):
        raise ValueError("Artifact path escapes its immutable root")
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Artifact is missing or unsafe: {relative}")
    return path


def _inventory(
    base: Path,
    inventory: object,
    *,
    exact_files: bool = False,
    allowed_files: Sequence[str] = (),
) -> dict[str, str]:
    if not isinstance(inventory, Mapping) or not inventory:
        raise ValueError("Artifact inventory must be a nonempty mapping")
    checked: dict[str, str] = {}
    for relative, digest in inventory.items():
        expected = _require_hash(digest, f"artifact {relative}")
        path = _safe(base, relative)
        actual = _sha(path)
        if actual != expected:
            raise ValueError(f"Artifact SHA-256 mismatch: {relative}")
        checked[str(relative)] = actual
    if exact_files:
        allowed = set(checked)
        for relative in allowed_files:
            allowed.add(_safe(base, relative).relative_to(base.resolve()).as_posix())
        actual_files: set[str] = set()
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError("Exact artifact inventory contains a symlink")
            if path.is_file():
                actual_files.add(path.relative_to(base).as_posix())
        if actual_files != allowed:
            raise ValueError(
                "Exact artifact inventory mismatch: "
                f"extra={sorted(actual_files - allowed)} "
                f"missing={sorted(allowed - actual_files)}"
            )
    return checked


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _pretty_json_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    _atomic_bytes(path, _pretty_json_bytes(payload))


def _write_sidecar(path: Path) -> None:
    _atomic_bytes(
        path.with_name(path.name + ".sha256"), (_sha(path) + "\n").encode("ascii")
    )


def _run_root(root: Path, output_base_override: Path | None) -> Path:
    base = (
        Path(output_base_override).resolve()
        if output_base_override is not None
        else root.resolve() / OUTPUT_ROOT
    )
    return base / RUN_ID


def _set_hold(
    root: Path,
    *,
    reason: str,
    stage: str,
    extension_epoch: int | None = None,
    output_base_override: Path | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_id": "sr_v2_spatial_sensitivity_gate/v1",
        "run_id": RUN_ID,
        "status": "HOLD",
        "passed": False,
        "stage": stage,
        "reason": reason,
        "submission_authorized": False,
        "interpretation_boundary": (
            "Ecological model-based sensitivity only; no effect is a person-level "
            "or causal estimate."
        ),
    }
    if extension_epoch is not None:
        payload["extension_epoch"] = extension_epoch
    _atomic_json(
        _run_root(root, output_base_override) / "spatial_sensitivity_gate.json",
        payload,
    )
    return payload


def _publish_immutable_json(directory: Path, name: str, payload: Mapping[str, object]) -> Path:
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{directory.name}-", dir=directory.parent))
    lock = directory.parent / f".{directory.name}.publication.lock"
    lock_handle = None
    try:
        path = staging / name
        _atomic_json(path, payload)
        _write_sidecar(path)
        lock_handle = lock.open("x", encoding="ascii", newline="\n")
        lock_handle.write(f"pid={os.getpid()}\n")
        lock_handle.flush()
        os.fsync(lock_handle.fileno())
        if os.path.lexists(directory):
            raise FileExistsError(f"Immutable publication already exists: {directory}")
        if sys.platform.startswith("linux"):
            renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
            renameat2.argtypes = [
                ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                ctypes.c_uint,
            ]
            renameat2.restype = ctypes.c_int
            if renameat2(-100, os.fsencode(staging), -100, os.fsencode(directory), 1) != 0:
                code = ctypes.get_errno()
                raise FileExistsError(code, os.strerror(code), str(directory))
        else:
            os.rename(staging, directory)
        return directory / name
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    finally:
        if lock_handle is not None:
            lock_handle.close()
            lock.unlink(missing_ok=True)


def _publish_or_reuse_immutable_json(
    directory: Path, name: str, payload: Mapping[str, object]
) -> Path:
    """Publish once, or reuse only byte-identical fully committed evidence."""

    expected_payload = _pretty_json_bytes(payload)

    def validate_existing() -> Path:
        if not directory.is_dir() or directory.is_symlink():
            raise FileExistsError(f"Conflicting immutable publication: {directory}")
        path = directory / name
        sidecar = path.with_name(path.name + ".sha256")
        actual_files = {
            item.relative_to(directory).as_posix()
            for item in directory.rglob("*")
            if item.is_file()
        }
        if any(item.is_symlink() for item in directory.rglob("*")) or actual_files != {
            name,
            name + ".sha256",
        }:
            raise FileExistsError(f"Conflicting immutable publication: {directory}")
        _sidecar(path)
        if path.read_bytes() != expected_payload:
            raise FileExistsError(f"Conflicting immutable publication: {directory}")
        return path

    if os.path.lexists(directory):
        return validate_existing()
    try:
        return _publish_immutable_json(directory, name, payload)
    except FileExistsError:
        return validate_existing()


def _commit_gate_decision(
    run_root: Path,
    extension_epoch: int,
    decision: Mapping[str, object],
    *,
    pointer_writer: Any = _atomic_json,
) -> Path:
    immutable = _publish_or_reuse_immutable_json(
        run_root / f"epochs/epoch_{extension_epoch}/gate",
        "gate_decision.json",
        decision,
    )
    pointer_writer(run_root / "spatial_sensitivity_gate.json", decision)
    return immutable


def _load_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if (
        not isinstance(config, dict)
        or config.get("schema_id") != "sr_v2_spatial_sensitivity_execution/v1"
        or config.get("run_id") != RUN_ID
        or config.get("model_id") != MODEL_ID
        or config.get("status") != "triggered_frozen_execution_contract"
    ):
        raise ValueError("Frozen spatial config identity changed")
    if config.get("execution", {}).get("valid_total_iterations_and_draws") != [
        [180000, 4500],
        [270000, 7500],
        [360000, 10500],
        [450000, 13500],
    ]:
        raise ValueError("Frozen epoch contract changed")
    if config.get("comparison", {}).get("rows") != list(COMPARISON_ROWS):
        raise ValueError("Frozen comparison row order changed")
    final_source = config.get("final_source_manifest")
    if (
        not isinstance(final_source, Mapping)
        or set(final_source) != {
            "schema_id", "required_status", "source_hash_mode", "required_sources"
        }
        or final_source.get("schema_id")
        != "sr_v2_robustness_final_source_manifest/v1"
        or final_source.get("required_status") != "reviewed_final"
        or final_source.get("source_hash_mode") != "raw_bytes"
        or final_source.get("required_sources") != list(REQUIRED_SOURCE_PATHS)
    ):
        raise ValueError("Frozen 24-path final-source contract changed")
    return config


def _verify_protected_trees(root: Path, manifest: object) -> dict[str, str]:
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("schema_id")
        != "sr_v2_spatial_protected_tree_manifest/v1"
        or manifest.get("roots") != list(PROTECTED_TREES)
        or not isinstance(manifest.get("files"), Mapping)
    ):
        raise ValueError("Protected-tree manifest schema mismatch")
    expected = {
        str(relative): _require_hash(digest, f"protected file {relative}")
        for relative, digest in manifest["files"].items()
    }
    actual: dict[str, str] = {}
    for relative_root in PROTECTED_TREES:
        tree = (root / relative_root).resolve()
        if not tree.is_dir() or tree.is_symlink() or not tree.is_relative_to(root):
            raise ValueError("Protected tree is missing or unsafe")
        for path in sorted(tree.rglob("*")):
            if path.is_symlink():
                raise ValueError("Protected tree contains a symlink")
            if path.is_file():
                actual[path.relative_to(root).as_posix()] = _sha(path)
    if actual != expected:
        raise ValueError(
            "Protected tree exact inventory changed: "
            f"extra={sorted(set(actual) - set(expected))} "
            f"missing={sorted(set(expected) - set(actual))}"
        )
    return actual


def _validate_launch_provenance(
    envelope: object,
    *,
    envelope_hash: str,
    manifest: Mapping[str, Any],
    required_sources: Sequence[str],
) -> tuple[dict[str, Any], dict[str, str]]:
    envelope_fields = {
        "schema_id", "status", "clean_worktree", "launch_commit", "bundle_sha256",
        "source_manifest", "source_manifest_sha256",
    }
    if not isinstance(envelope, Mapping) or set(envelope) != envelope_fields:
        raise ValueError("Reviewed launch envelope exact schema mismatch")
    launch_commit = envelope.get("launch_commit")
    bundle_hash = envelope.get("bundle_sha256")
    if (
        envelope.get("schema_id") != "sr_v2_robustness_launch_envelope/v1"
        or envelope.get("status") != "reviewed_final"
        or envelope.get("clean_worktree") is not True
        or not isinstance(launch_commit, str)
        or len(launch_commit) != 40
        or any(character not in "0123456789abcdef" for character in launch_commit)
    ):
        raise ValueError("Reviewed launch envelope identity/status mismatch")
    _require_hash(bundle_hash, "bundle_sha256")
    source_manifest = envelope.get("source_manifest")
    source_fields = {
        "schema_id", "status", "joint_regression_passed", "source_hash_mode",
        "sources", "joint_regression_evidence", "joint_regression_evidence_sha256",
    }
    if not isinstance(source_manifest, Mapping) or set(source_manifest) != source_fields:
        raise ValueError("Reviewed final-source manifest exact schema mismatch")
    manifest_hash = _canonical_sha(source_manifest)
    sources = source_manifest.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise ValueError("Reviewed final-source source inventory is missing")
    normalized_sources = {
        str(relative): _require_hash(digest, f"reviewed source {relative}")
        for relative, digest in sources.items()
        if isinstance(relative, str) and relative
    }
    if len(normalized_sources) != len(sources) or not set(required_sources).issubset(
        normalized_sources
    ):
        missing = sorted(set(required_sources) - set(normalized_sources))
        raise ValueError(f"Reviewed union source manifest omits required sources: {missing}")
    if (
        source_manifest.get("schema_id")
        != "sr_v2_robustness_final_source_manifest/v1"
        or source_manifest.get("status") != "reviewed_final"
        or source_manifest.get("joint_regression_passed") is not True
        or source_manifest.get("source_hash_mode") != "raw_bytes"
        or envelope.get("source_manifest_sha256") != manifest_hash
        or manifest.get("launch_envelope_sha256") != envelope_hash
        or manifest.get("final_source_manifest_sha256") != manifest_hash
        or manifest.get("launch_commit") != launch_commit
        or manifest.get("bundle_sha256") != bundle_hash
        or manifest.get("joint_regression_evidence_sha256")
        != source_manifest.get("joint_regression_evidence_sha256")
    ):
        raise ValueError("Reviewed envelope/source/preparation provenance mismatch")
    _require_hash(
        source_manifest.get("joint_regression_evidence_sha256"),
        "joint_regression_evidence_sha256",
    )
    return dict(source_manifest), dict(sorted(normalized_sources.items()))


def _array_digest_schema(values: np.ndarray, dtype: str) -> dict[str, object]:
    expected = np.dtype(dtype)
    array = np.ascontiguousarray(np.asarray(values, dtype=expected))
    return {
        "dtype": expected.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
    }


def _expected_design_and_parameter_schema(
    frame: pd.DataFrame,
    counties: Sequence[str],
    graph_contract_sha256: str,
) -> tuple[dict[str, object], list[str]]:
    x = pd.DataFrame(index=frame.index)
    x["Intercept"] = 1.0
    rural = pd.Categorical(
        frame["primary_rurality"],
        categories=[
            "metro_large", "metro_other", "nonmetro_adjacent", "nonmetro_nonadjacent"
        ],
    )
    rural_dummies = pd.get_dummies(rural, prefix="primary_rurality", dtype=float)
    for column in rural_dummies.columns:
        if column != "primary_rurality_metro_large":
            x[column] = rural_dummies[column]
    svi = pd.Categorical(
        frame["svi_quartile"], categories=["Q1_lowest", "Q2", "Q3", "Q4_highest"]
    )
    svi_dummies = pd.get_dummies(svi, prefix="svi_quartile", dtype=float)
    for column in svi_dummies.columns:
        if column != "svi_quartile_Q1_lowest":
            x[column] = svi_dummies[column]
    x["z_pct_age65"] = pd.to_numeric(frame["z_pct_age65"], errors="coerce").fillna(0.0)
    x["z_pct_male"] = pd.to_numeric(frame["z_pct_male"], errors="coerce").fillna(0.0)
    x = x.fillna(0.0)
    states = sorted(frame["state_fips"].astype(str).unique())
    years = sorted(frame["year"].astype(str).unique())
    state_map = {state: index for index, state in enumerate(states)}
    year_map = {year: index for index, year in enumerate(years)}
    normalized_counties = frame["county_fips"].astype(str).str.strip().str.zfill(5)
    county_map = {county: index for index, county in enumerate(counties)}
    if tuple(sorted(normalized_counties.unique())) != tuple(counties):
        raise ValueError("Prepared model-frame counties differ from graph county order")
    row_county_index = normalized_counties.map(county_map).to_numpy(dtype=np.int64)
    design = {
        "schema_id": "sr_v2_spatial_design/v1",
        "columns": list(x.columns),
        "states": states,
        "years": years,
        "x": _array_digest_schema(x.to_numpy(dtype=np.float64), "<f8"),
        "offset": _array_digest_schema(
            np.log(
                pd.to_numeric(frame["population"], errors="coerce")
                .clip(lower=1)
                .to_numpy(dtype=np.float64)
            ),
            "<f8",
        ),
        "state_index": _array_digest_schema(
            frame["state_fips"].astype(str).map(state_map).to_numpy(dtype=np.int64),
            "<i8",
        ),
        "year_index": _array_digest_schema(
            frame["year"].astype(str).map(year_map).to_numpy(dtype=np.int64),
            "<i8",
        ),
        "row_county_index": _array_digest_schema(row_county_index, "<i8"),
        "graph_contract_sha256": graph_contract_sha256,
    }
    parameters = [
        *list(x.columns),
        *(f"state_effect[{state}]" for state in states),
        *(f"year_effect[{year}]" for year in years),
        "sigma_state", "sigma_year", "kappa", "sigma_county", "phi_structured",
    ]
    return design, parameters


def _expected_epoch_zero_target(
    frame: pd.DataFrame,
    counties: Sequence[str],
    manifest: Mapping[str, Any],
    config_path: Path,
) -> dict[str, object]:
    design, parameters = _expected_design_and_parameter_schema(
        frame, counties, str(manifest["graph_contract_sha256"])
    )
    deaths = float(frame.drop_duplicates("year")["q003_national_year_total"].sum())
    exposure = float(pd.to_numeric(frame["population"], errors="coerce").sum())
    intercept_mean = float(np.log(max(deaths / exposure, 1e-12)))
    prior = {
        "schema_id": "sr_v2_spatial_prior/v1",
        "base_prior": {
            "name": "default",
            "intercept_sd": 5.0,
            "nonintercept_beta_sd": 1.5,
            "state_scale_halfnormal_sd": 1.0,
            "year_scale_halfnormal_sd": 1.0,
            "log_kappa_mean": float(np.log(10.0)),
            "log_kappa_sd": 1.5,
        },
        "sigma_county": {
            "distribution": "HalfNormal", "sd": 1.0,
            "sampled_as": "log_sigma_county",
            "transformed_jacobian": "log_sigma_county",
        },
        "phi_structured": {
            "distribution": "Beta", "alpha": 1.0, "beta": 1.0,
            "sampled_as": "logit_phi_structured",
            "transformed_jacobian": "log_phi_plus_log_one_minus_phi",
        },
    }
    return {
        "schema_id": "sr_v2_spatial_target/v1",
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "config_sha256": _sha(config_path),
        "input_manifest_sha256": manifest["input_manifest_sha256"],
        "source_manifest_sha256": manifest["final_source_manifest_sha256"],
        "model_frame_semantic_sha256": manifest["model_frame_semantic_sha256"],
        "graph_contract_sha256": manifest["graph_contract_sha256"],
        "likelihood": "negative_binomial_2",
        "prior": prior,
        "intercept_mean_rule": "crude_national_log_rate",
        "intercept_mean_float_hex": intercept_mean.hex(),
        "design_schema": design,
        "parameter_schema": parameters,
        "extension_epoch": 0,
        "extension_authorization_sha256": "0" * 64,
    }


def _independent_runtime_design(
    frame: pd.DataFrame, counties: Sequence[str]
) -> dict[str, Any]:
    x = pd.DataFrame(index=frame.index)
    x["Intercept"] = 1.0
    rural = pd.Categorical(
        frame["primary_rurality"],
        categories=[
            "metro_large", "metro_other", "nonmetro_adjacent", "nonmetro_nonadjacent"
        ],
    )
    rural_dummies = pd.get_dummies(rural, prefix="primary_rurality", dtype=float)
    for column in rural_dummies.columns:
        if column != "primary_rurality_metro_large":
            x[column] = rural_dummies[column]
    svi = pd.Categorical(
        frame["svi_quartile"], categories=["Q1_lowest", "Q2", "Q3", "Q4_highest"]
    )
    svi_dummies = pd.get_dummies(svi, prefix="svi_quartile", dtype=float)
    for column in svi_dummies.columns:
        if column != "svi_quartile_Q1_lowest":
            x[column] = svi_dummies[column]
    x["z_pct_age65"] = pd.to_numeric(frame["z_pct_age65"], errors="coerce").fillna(0.0)
    x["z_pct_male"] = pd.to_numeric(frame["z_pct_male"], errors="coerce").fillna(0.0)
    x = x.fillna(0.0)
    states = sorted(frame["state_fips"].astype(str).unique())
    years = sorted(frame["year"].astype(str).unique())
    normalized_counties = frame["county_fips"].astype(str).str.strip().str.zfill(5)
    county_map = {county: index for index, county in enumerate(counties)}
    return {
        "x": x.to_numpy(dtype=np.float64),
        "columns": list(x.columns),
        "offset": np.log(
            pd.to_numeric(frame["population"], errors="coerce")
            .clip(lower=1)
            .to_numpy(dtype=np.float64)
        ),
        "state_index": frame["state_fips"].astype(str).map(
            {state: index for index, state in enumerate(states)}
        ).to_numpy(dtype=np.int64),
        "year_index": frame["year"].astype(str).map(
            {year: index for index, year in enumerate(years)}
        ).to_numpy(dtype=np.int64),
        "row_county_index": normalized_counties.map(county_map).to_numpy(
            dtype=np.int64
        ),
        "states": states,
        "years": years,
    }


def _independent_checkpoint_target(
    checkpoint: Mapping[str, Any],
    *,
    target: Mapping[str, Any],
    frame: pd.DataFrame,
    counties: Sequence[str],
    adjacency: sparse.csr_matrix,
    components: Sequence[np.ndarray],
    scales: Sequence[float],
) -> float:
    design = _independent_runtime_design(frame, counties)
    if (
        design["columns"] != target["design_schema"]["columns"]
        or design["states"] != target["design_schema"]["states"]
        or design["years"] != target["design_schema"]["years"]
    ):
        raise ValueError("Checkpoint target runtime design labels changed")
    state = checkpoint["current_state"]
    y = _array(state["y"], "<i8")
    beta = _array(state["beta"], "<f8")
    state_effect = _array(state["state_effect"], "<f8")
    year_effect = _array(state["year_effect"], "<f8")
    structured = _array(state["spatial_structured"], "<f8")
    unstructured = _array(state["spatial_unstructured"], "<f8")
    log_sigma_state = _finite_hex(
        state["log_sigma_state_hex"], "checkpoint log_sigma_state"
    )
    log_sigma_year = _finite_hex(
        state["log_sigma_year_hex"], "checkpoint log_sigma_year"
    )
    log_kappa = _finite_hex(state["log_kappa_hex"], "checkpoint log_kappa")
    log_sigma_county = _finite_hex(
        state["log_sigma_county_hex"], "checkpoint log_sigma_county"
    )
    logit_phi = _finite_hex(
        state["logit_phi_structured_hex"], "checkpoint logit_phi_structured"
    )
    sigma_county = float(np.exp(log_sigma_county))
    phi = float(expit(logit_phi))
    if not np.isfinite(sigma_county) or sigma_county <= 0.0 or not 0.0 < phi < 1.0:
        raise ValueError("Checkpoint BYM2 hyperparameters are outside support")
    county_effect = sigma_county * (
        np.sqrt(phi) * structured + np.sqrt(1.0 - phi) * unstructured
    )
    centered_state = state_effect - state_effect.mean()
    centered_year = year_effect - year_effect.mean()
    predictor = (
        design["offset"]
        + design["x"] @ beta
        + centered_state[design["state_index"]]
        + centered_year[design["year_index"]]
        + county_effect[design["row_county_index"]]
    )
    mu = np.exp(np.clip(predictor, -30, 30))
    kappa = float(np.exp(log_kappa))
    if not np.isfinite(kappa) or kappa <= 0.0:
        raise ValueError("Checkpoint NB2 kappa is outside support")
    y_float = np.asarray(y, dtype=float)
    clipped_mu = np.clip(np.asarray(mu, dtype=float), 1e-12, np.inf)
    likelihood = float(
        (
            gammaln(y_float + kappa)
            - gammaln(kappa)
            - gammaln(y_float + 1.0)
            + kappa * (np.log(kappa) - np.log(kappa + clipped_mu))
            + y_float * (np.log(clipped_mu) - np.log(kappa + clipped_mu))
        ).sum()
    )
    prior = target["prior"]["base_prior"]
    intercept_mean = float.fromhex(target["intercept_mean_float_hex"])
    density = (
        -0.5 * ((beta[0] - intercept_mean) / prior["intercept_sd"]) ** 2
        - np.log(prior["intercept_sd"])
    )
    if len(beta) > 1:
        density += float(
            (
                -0.5 * (beta[1:] / prior["nonintercept_beta_sd"]) ** 2
                - np.log(prior["nonintercept_beta_sd"])
            ).sum()
        )
    sigma_state = np.exp(log_sigma_state)
    sigma_year = np.exp(log_sigma_year)
    prior_state = centered_state - centered_state.mean()
    prior_year = centered_year - centered_year.mean()
    density += float(
        -0.5 * np.square(prior_state / sigma_state).sum()
        - max(len(prior_state) - 1, 0) * np.log(sigma_state)
    )
    density += float(
        -0.5 * np.square(prior_year / sigma_year).sum()
        - max(len(prior_year) - 1, 0) * np.log(sigma_year)
    )
    density += (
        -0.5 * (sigma_state / prior["state_scale_halfnormal_sd"]) ** 2
        - np.log(prior["state_scale_halfnormal_sd"])
        + log_sigma_state
    )
    density += (
        -0.5 * (sigma_year / prior["year_scale_halfnormal_sd"]) ** 2
        - np.log(prior["year_scale_halfnormal_sd"])
        + log_sigma_year
    )
    density += (
        -0.5 * ((log_kappa - prior["log_kappa_mean"]) / prior["log_kappa_sd"]) ** 2
        - np.log(prior["log_kappa_sd"])
    )
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    precision = (sparse.diags(degree, format="csr") - adjacency).tocsr()
    scale_by_county = np.zeros(len(counties), dtype=np.float64)
    for component, scale in zip(components, scales, strict=True):
        scale_by_county[np.asarray(component, dtype=np.int64)] = float(scale)
    scaled_precision = sparse.diags(scale_by_county, format="csr") @ precision
    structured_log_density = -0.5 * float(
        structured @ (scaled_precision @ structured)
    )
    unstructured_log_density = -0.5 * float(unstructured @ unstructured)
    sigma_log_density = (
        -0.5 * float(np.square(np.float64(sigma_county / 1.0)))
        + log_sigma_county
    )
    phi_log_density = float(np.log(phi) + np.log1p(-phi))
    spatial_density = (
        structured_log_density
        + unstructured_log_density
        + sigma_log_density
        + phi_log_density
    )
    density += float(spatial_density)
    result = float(density) + likelihood
    if not math.isfinite(result):
        raise ValueError("Checkpoint target recomputation is nonfinite")
    return result


def _validate_checkpoint_target(
    checkpoint: Mapping[str, Any],
    *,
    target: Mapping[str, Any],
    frame: pd.DataFrame,
    counties: Sequence[str],
    adjacency: sparse.csr_matrix,
    components: Sequence[np.ndarray],
    scales: Sequence[float],
    label: str,
) -> float:
    observed = _finite_hex(checkpoint["current_target"], "checkpoint current_target")
    recomputed = _independent_checkpoint_target(
        checkpoint,
        target=target,
        frame=frame,
        counties=counties,
        adjacency=adjacency,
        components=components,
        scales=scales,
    )
    if recomputed != observed:
        raise ValueError(f"{label} current target does not recompute exactly")
    return recomputed


def _validate_target_identity(
    identity: object,
    *,
    expected_target: Mapping[str, Any],
    chain_id: int,
    seeds: Mapping[str, int],
) -> dict[str, Any]:
    if not isinstance(identity, Mapping) or set(identity) != {
        "schema_version", "target", "target_fingerprint", "chain", "chain_fingerprint"
    }:
        raise ValueError("Spatial target identity exact schema mismatch")
    target = identity.get("target")
    if (
        identity.get("schema_version") != 2
        or not isinstance(target, Mapping)
        or set(target) != TARGET_EXACT_FIELDS
        or dict(target) != dict(expected_target)
    ):
        raise ValueError("Spatial target exact field/value contract mismatch")
    target_fingerprint = _canonical_sha(target)
    observed_chain = identity.get("chain")
    if not isinstance(observed_chain, Mapping):
        raise ValueError("Spatial chain identity must be a mapping")
    chain = {
        "target_fingerprint": target_fingerprint,
        "chain_id": chain_id,
        **dict(seeds),
    }
    if (
        set(observed_chain) != set(chain)
        or identity.get("target_fingerprint") != target_fingerprint
        or dict(observed_chain) != chain
        or identity.get("chain_fingerprint") != _canonical_sha(chain)
    ):
        raise ValueError("Spatial chain exact seed/fingerprint contract mismatch")
    return dict(identity)


def _expected_preparation_identity(
    manifest: Mapping[str, Any], mapping: Sequence[Mapping[str, Any]]
) -> str:
    return _canonical_sha(
        {
            "schema_id": "sr_v2_spatial_prepared_run/v1",
            "run_id": RUN_ID,
            "model_id": MODEL_ID,
            "operational_config_sha256": manifest["operational_config_sha256"],
            "launch_envelope_sha256": manifest["launch_envelope_sha256"],
            "final_source_manifest_sha256": manifest[
                "final_source_manifest_sha256"
            ],
            "launch_commit": manifest["launch_commit"],
            "bundle_sha256": manifest["bundle_sha256"],
            "joint_regression_evidence_sha256": manifest[
                "joint_regression_evidence_sha256"
            ],
            "production_eligible": True,
            "builder_provenance": {
                "frame_loader": "default_load_model_frame",
                "allocation_solver": "default_solve_feasible_allocation",
                "graph_preparer": "default_graph_artifacts",
                "envelope_loader": "default_reviewed_launch_envelope",
            },
            "input_manifest_sha256": manifest["input_manifest_sha256"],
            "graph_contract_sha256": manifest["graph_contract_sha256"],
            "chain_fingerprints": [row["chain_fingerprint"] for row in mapping],
        }
    )


def _validate_preparation_identity(
    manifest: Mapping[str, Any], mapping: Sequence[Mapping[str, Any]]
) -> str:
    expected = _expected_preparation_identity(manifest, mapping)
    if manifest.get("preparation_identity") != expected:
        raise ValueError("Prepared preparation_identity is not independently reproducible")
    return expected


def _validate_prepared_artifact_paths(manifest: Mapping[str, Any]) -> None:
    if (
        manifest.get("input_manifest") != "input_manifest.json"
        or manifest.get("model_frame") != "inputs/model_frame.parquet"
        or manifest.get("protected_tree_manifest")
        != "provenance/protected_tree_manifest.json"
    ):
        raise ValueError("Prepared manifest artifact paths are not generator-exact")
    mapping = manifest.get("chain_mapping")
    if not isinstance(mapping, list) or len(mapping) != 4:
        raise ValueError("Prepared chain mapping path contract requires four chains")
    for chain_id, row in enumerate(mapping, start=1):
        if not isinstance(row, Mapping) or (
            row.get("initial_allocation")
            != f"initializations/initial_allocation_chain_{chain_id:02d}.parquet"
            or row.get("initial_checkpoint")
            != (
                f"initial_checkpoints/chain_{chain_id:02d}/"
                "checkpoint_epoch_0_attempt_1_iter_000000000.json"
            )
        ):
            raise ValueError("Prepared chain artifact paths are not generator-exact")


def _validate_terminal_checkpoint_path(
    status: Mapping[str, Any], *, epoch: int, iteration: int
) -> str:
    attempt = _exact_integer(status.get("job_attempt"), "status job_attempt")
    expected = (
        f"checkpoints/checkpoint_epoch_{epoch}_attempt_{attempt}_"
        f"iter_{iteration:09d}.json"
    )
    if status.get("latest_checkpoint") != expected:
        raise ValueError("Terminal checkpoint path is not generator-exact")
    return expected


def _exact_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an exact integer")
    return value


def _finite_hex(value: object, label: str) -> float:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be canonical float.hex text")
    try:
        parsed = float.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{label} must be canonical float.hex text") from error
    if not math.isfinite(parsed) or parsed.hex() != value:
        raise ValueError(f"{label} must be finite canonical float.hex text")
    return parsed


def _load_canonical_checkpoint(path: Path) -> dict[str, Any]:
    _sidecar(path)
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Checkpoint must be canonical ASCII JSON") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise ValueError("Checkpoint JSON encoding is noncanonical")
    return payload


def _validate_checkpoint_payload(
    checkpoint: object,
    *,
    identity: Mapping[str, Any],
    seeds: Mapping[str, int],
    expected_epoch: int,
    expected_attempt: int,
    expected_iteration: int,
    expected_draws: int,
    expected_chunks: int,
    row_count: int,
    county_count: int,
    labels: np.ndarray | None = None,
    expected_y: np.ndarray | None = None,
) -> dict[str, Any]:
    if not isinstance(checkpoint, Mapping) or set(checkpoint) != CHECKPOINT_EXACT_FIELDS:
        raise ValueError("Spatial checkpoint exact v2 schema mismatch")
    target = identity["target"]
    design = target["design_schema"]
    expected_values = {
        "schema_version": 2,
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "target_fingerprint": identity["target_fingerprint"],
        "chain_fingerprint": identity["chain_fingerprint"],
        "extension_epoch": expected_epoch,
        "job_attempt": expected_attempt,
        "chain_id": identity["chain"]["chain_id"],
        "seeds": dict(seeds),
        "iteration": expected_iteration,
        "saved_draws": expected_draws,
        "next_draw_id": expected_draws + 1,
    }
    if any(checkpoint.get(key) != value for key, value in expected_values.items()):
        raise ValueError("Spatial checkpoint identity/seed/progress mismatch")
    for key in ("schema_version", "extension_epoch", "job_attempt", "chain_id", "iteration", "saved_draws", "next_draw_id"):
        _exact_integer(checkpoint[key], f"checkpoint {key}")
    if not isinstance(checkpoint.get("seeds"), Mapping) or set(checkpoint["seeds"]) != set(seeds):
        raise ValueError("Spatial checkpoint seed schema mismatch")
    state = checkpoint.get("current_state")
    state_fields = {
        "y", "beta", "state_effect", "year_effect", "log_sigma_state_hex",
        "log_sigma_year_hex", "log_kappa_hex", "spatial_structured",
        "spatial_unstructured", "log_sigma_county_hex", "logit_phi_structured_hex",
    }
    if not isinstance(state, Mapping) or set(state) != state_fields:
        raise ValueError("Spatial checkpoint current-state exact schema mismatch")
    arrays = {
        "y": _array(state["y"], "<i8"),
        "beta": _array(state["beta"], "<f8"),
        "state_effect": _array(state["state_effect"], "<f8"),
        "year_effect": _array(state["year_effect"], "<f8"),
        "spatial_structured": _array(state["spatial_structured"], "<f8"),
        "spatial_unstructured": _array(state["spatial_unstructured"], "<f8"),
    }
    expected_shapes = {
        "y": (row_count,),
        "beta": (len(design["columns"]),),
        "state_effect": (len(design["states"]),),
        "year_effect": (len(design["years"]),),
        "spatial_structured": (county_count,),
        "spatial_unstructured": (county_count,),
    }
    for name, array in arrays.items():
        if array.shape != expected_shapes[name] or (
            name != "y" and not np.isfinite(array).all()
        ):
            raise ValueError(f"Spatial checkpoint {name} shape/value mismatch")
    if expected_y is not None and not np.array_equal(arrays["y"], expected_y):
        raise ValueError("Spatial checkpoint latent state differs from expected allocation")
    if abs(float(arrays["state_effect"].mean())) > 1e-12 or abs(
        float(arrays["year_effect"].mean())
    ) > 1e-12:
        raise ValueError("Spatial checkpoint state/year effects are not centered")
    if labels is not None:
        structured = arrays["spatial_structured"]
        for component in np.unique(labels):
            indices = np.flatnonzero(labels == component)
            if len(indices) == 1 and np.any(structured[indices] != 0.0):
                raise ValueError("Spatial checkpoint singleton structured effect is nonzero")
            if len(indices) > 1 and abs(float(structured[indices].mean())) > 1e-12:
                raise ValueError("Spatial checkpoint structured effect is not component-centered")
    for name in (
        "log_sigma_state_hex", "log_sigma_year_hex", "log_kappa_hex",
        "log_sigma_county_hex", "logit_phi_structured_hex",
    ):
        _finite_hex(state[name], f"checkpoint {name}")
    _finite_hex(checkpoint.get("current_target"), "checkpoint current_target")
    rng = checkpoint.get("rng_state")
    if (
        not isinstance(rng, Mapping)
        or set(rng) != {"bit_generator", "state", "has_uint32", "uinteger"}
        or rng.get("bit_generator") != "PCG64"
        or not isinstance(rng.get("state"), Mapping)
        or set(rng["state"]) != {"state", "inc"}
    ):
        raise ValueError("Spatial checkpoint RNG exact schema mismatch")
    for name in ("state", "inc"):
        if _exact_integer(rng["state"][name], f"RNG {name}") < 0:
            raise ValueError("Spatial checkpoint RNG state must be nonnegative")
    for name in ("has_uint32", "uinteger"):
        if _exact_integer(rng[name], f"RNG {name}") < 0:
            raise ValueError("Spatial checkpoint RNG cache must be nonnegative")
    counters: dict[str, dict[str, int]] = {}
    for label in ("accepted", "proposed"):
        value = checkpoint.get(label)
        if not isinstance(value, Mapping) or set(value) != COUNTER_FIELDS:
            raise ValueError(f"Spatial checkpoint {label} exact counter schema mismatch")
        counters[label] = {
            name: _exact_integer(count, f"{label} {name}") for name, count in value.items()
        }
        if any(count < 0 for count in counters[label].values()):
            raise ValueError("Spatial checkpoint counters must be nonnegative")
    if any(
        counters["accepted"][name] > counters["proposed"][name]
        for name in COUNTER_FIELDS
    ):
        raise ValueError("Spatial checkpoint accepted counter exceeds proposals")
    for block in (
        "beta", "state", "year", "log_sigma_state", "log_sigma_year", "log_kappa",
        "spatial_hyperparameters",
    ):
        if counters["proposed"][block] != expected_iteration:
            raise ValueError("Spatial checkpoint scheduled block counter mismatch")
    if counters["proposed"]["mala"] != expected_iteration // 5:
        raise ValueError("Spatial checkpoint MALA schedule mismatch")
    adaptation = checkpoint.get("adaptation_state")
    adaptation_fields = {
        "multiplier_hex", "epsilon_structured_hex", "epsilon_unstructured_hex",
        "attempted", "accepted", "window_attempted", "window_accepted",
        "windows_completed", "adaptation_frozen",
    }
    if not isinstance(adaptation, Mapping) or set(adaptation) != adaptation_fields:
        raise ValueError("Spatial checkpoint adaptation exact schema mismatch")
    multiplier = _finite_hex(adaptation["multiplier_hex"], "MALA multiplier")
    epsilon_structured = _finite_hex(
        adaptation["epsilon_structured_hex"], "MALA epsilon structured"
    )
    epsilon_unstructured = _finite_hex(
        adaptation["epsilon_unstructured_hex"], "MALA epsilon unstructured"
    )
    adaptation_ints = {
        name: _exact_integer(adaptation[name], f"adaptation {name}")
        for name in (
            "attempted", "accepted", "window_attempted", "window_accepted",
            "windows_completed",
        )
    }
    adaptive_attempts = min(expected_iteration // 5, 9_000)
    expected_window_attempts = (
        adaptive_attempts % 100 if expected_iteration // 5 < 9_000 else 0
    )
    expected_frozen = expected_epoch > 0 or expected_iteration >= 45_000
    if (
        adaptation.get("adaptation_frozen") is not expected_frozen
        or any(value < 0 for value in adaptation_ints.values())
        or adaptation_ints["attempted"] != expected_iteration // 5
        or adaptation_ints["accepted"] != counters["accepted"]["mala"]
        or adaptation_ints["accepted"] > adaptation_ints["attempted"]
        or adaptation_ints["window_attempted"] != expected_window_attempts
        or adaptation_ints["windows_completed"] != adaptive_attempts // 100
        or adaptation_ints["window_accepted"]
        > adaptation_ints["window_attempted"]
        or adaptation_ints["window_accepted"] > adaptation_ints["accepted"]
        or epsilon_structured != 0.02 * multiplier
        or epsilon_unstructured != 0.04 * multiplier
        or not 0.1 <= multiplier <= 5.0
    ):
        raise ValueError("Spatial checkpoint adaptation values/schedule mismatch")
    records = checkpoint.get("committed_chunks")
    if not isinstance(records, list) or len(records) != expected_chunks:
        raise ValueError("Spatial checkpoint committed-chunk cardinality mismatch")
    pending = checkpoint.get("pending_buffers")
    if not isinstance(pending, Mapping) or set(pending) != {"scalar", "structured", "unstructured"}:
        raise ValueError("Spatial checkpoint pending-buffer exact schema mismatch")
    scalar_pending = pending["scalar"]
    scalar_fields = {
        "columns", "row_count", "chain_id", "draw_id", "extension_epoch",
        "parameter", "value",
    }
    if (
        not isinstance(scalar_pending, Mapping)
        or set(scalar_pending) != scalar_fields
        or scalar_pending.get("columns")
        != ["chain_id", "draw_id", "extension_epoch", "parameter", "value"]
        or _exact_integer(scalar_pending.get("row_count"), "pending row_count") != 0
        or scalar_pending.get("parameter") != []
    ):
        raise ValueError("Spatial checkpoint pending scalar exact schema mismatch")
    for name, dtype in (
        ("chain_id", "<i8"), ("draw_id", "<i8"), ("extension_epoch", "<i8"),
        ("value", "<f8"),
    ):
        if _array(scalar_pending[name], dtype).shape != (0,):
            raise ValueError("Spatial checkpoint pending scalar array is not empty")
    for name in ("structured", "unstructured"):
        values = _array(pending[name], "<f8")
        if values.shape != (0, county_count):
            raise ValueError("Spatial checkpoint pending spatial buffer is not empty")
    output = checkpoint.get("output_positions")
    if (
        not isinstance(output, Mapping)
        or set(output) != {"scalar_rows", "spatial_draws"}
        or _exact_integer(output.get("scalar_rows"), "scalar_rows")
        != expected_draws * len(target["parameter_schema"])
        or _exact_integer(output.get("spatial_draws"), "spatial_draws") != expected_draws
    ):
        raise ValueError("Spatial checkpoint output-position schema/value mismatch")
    if expected_draws != max(0, (expected_iteration - 45_000) // 30):
        raise ValueError("Spatial checkpoint retained schedule mismatch")
    return dict(checkpoint)


def _verify_prepared(
    root: Path, run_root: Path, config: Mapping[str, Any], config_path: Path
) -> tuple[dict[str, Any], Path]:
    sources = config.get("source_authorities")
    _inventory(root, sources)
    prepared = run_root / "prepared"
    path = prepared / "prepared_run_manifest.json"
    _sidecar(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping) or set(manifest) != PREPARED_MANIFEST_EXACT_FIELDS:
        raise ValueError("Prepared manifest exact schema mismatch")
    if (
        manifest.get("schema_id") != "sr_v2_spatial_prepared_run/v1"
        or manifest.get("run_id") != RUN_ID
        or manifest.get("model_id") != MODEL_ID
        or manifest.get("status") != "prepared_not_run"
        or manifest.get("submission_authorized") is not False
        or manifest.get("production_eligible") is not True
        or manifest.get("builder_provenance")
        != {
            "frame_loader": "default_load_model_frame",
            "allocation_solver": "default_solve_feasible_allocation",
            "graph_preparer": "default_graph_artifacts",
            "envelope_loader": "default_reviewed_launch_envelope",
        }
        or manifest.get("operational_config_sha256") != _sha(config_path)
        or manifest.get("input_manifest") != "input_manifest.json"
        or manifest.get("model_frame") != "inputs/model_frame.parquet"
        or manifest.get("protected_tree_manifest")
        != "provenance/protected_tree_manifest.json"
    ):
        raise ValueError("Prepared manifest identity/status mismatch")
    _validate_prepared_artifact_paths(manifest)
    _inventory(
        prepared,
        manifest.get("prepared_artifact_sha256"),
        exact_files=True,
        allowed_files=(
            "prepared_run_manifest.json",
            "prepared_run_manifest.json.sha256",
        ),
    )
    envelope_path = prepared / "provenance/launch_envelope.json"
    envelope_hash = _sidecar(envelope_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    source_manifest, reviewed_sources = _validate_launch_provenance(
        envelope,
        envelope_hash=envelope_hash,
        manifest=manifest,
        required_sources=config["final_source_manifest"]["required_sources"],
    )
    _inventory(root, reviewed_sources)
    evidence = _safe(root, source_manifest.get("joint_regression_evidence"))
    if _sha(evidence) != source_manifest.get("joint_regression_evidence_sha256"):
        raise ValueError("Joint-regression evidence changed")
    copied_source = prepared / "provenance/final_source_manifest.json"
    _sidecar(copied_source)
    if json.loads(copied_source.read_text(encoding="utf-8")) != source_manifest:
        raise ValueError("Copied final-source manifest differs from the envelope")
    input_path = prepared / str(manifest.get("input_manifest", ""))
    if _sidecar(input_path) != manifest.get("input_manifest_sha256"):
        raise ValueError("Prepared input-manifest hash mismatch")
    input_manifest = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(input_manifest, Mapping) or set(input_manifest) != INPUT_MANIFEST_EXACT_FIELDS:
        raise ValueError("Prepared input-manifest exact schema mismatch")
    if manifest.get("source_authorities") != config.get("source_authorities"):
        raise ValueError("Prepared source authorities differ from frozen config")
    bindings = {
        "schema_id": "sr_v2_spatial_input_manifest/v1",
        "run_id": RUN_ID,
        "operational_config_sha256": _sha(config_path),
        "source_authorities": manifest["source_authorities"],
        "launch_envelope_sha256": manifest["launch_envelope_sha256"],
        "final_source_manifest_sha256": manifest["final_source_manifest_sha256"],
        "launch_commit": manifest["launch_commit"],
        "bundle_sha256": manifest["bundle_sha256"],
        "joint_regression_evidence_sha256": manifest["joint_regression_evidence_sha256"],
        "source_model_frame_sha256": config["source_authorities"][
            "data/processed/bayes_constrained/model_frame.parquet"
        ],
        "prepared_model_frame_sha256": manifest["model_frame_sha256"],
        "model_frame_semantic_sha256": manifest["model_frame_semantic_sha256"],
        "graph_contract_sha256": manifest["graph_contract_sha256"],
    }
    if any(input_manifest.get(key) != value for key, value in bindings.items()):
        raise ValueError("Prepared input-manifest identity chain mismatch")
    _inventory(prepared, input_manifest.get("graph_artifact_sha256"))
    source_frame_path = _safe(root, "data/processed/bayes_constrained/model_frame.parquet")
    prepared_frame_path = _safe(prepared, manifest.get("model_frame"))
    if (
        _sha(source_frame_path) != input_manifest["source_model_frame_sha256"]
        or _sha(prepared_frame_path) != input_manifest["prepared_model_frame_sha256"]
    ):
        raise ValueError("Prepared/source model-frame raw-byte identity mismatch")
    source_frame = pd.read_parquet(source_frame_path)
    prepared_frame = pd.read_parquet(prepared_frame_path)
    if (
        _model_frame_semantic_sha256(source_frame)
        != _model_frame_semantic_sha256(prepared_frame)
        or _model_frame_semantic_sha256(prepared_frame)
        != manifest["model_frame_semantic_sha256"]
    ):
        raise ValueError("Prepared/source model-frame semantic identity mismatch")
    counties, adjacency, labels, components, scales = _graph_from_prepared(
        prepared, config
    )
    expected_target = _expected_epoch_zero_target(
        prepared_frame, counties, manifest, config_path
    )
    if (
        len(expected_target["parameter_schema"]) != 71
        or manifest.get("parameter_schema") != expected_target["parameter_schema"]
    ):
        raise ValueError("Prepared parameter schema differs from independent design")
    county_path = prepared / "graph/county_order.txt"
    edge_path = prepared / "graph/edge_list.txt"
    component_rows = [
        {
            "component_id": component_id,
            "minimum_fips": counties[int(component[0])],
            "size": len(component),
            "singleton": len(component) == 1,
            "scale_hex": float(scale).hex(),
        }
        for component_id, (component, scale) in enumerate(
            zip(components, scales, strict=True)
        )
    ]
    graph_identity = {
        "components": [
            {
                "members": [counties[int(index)] for index in component],
                "scale_hex": float(scale).hex(),
            }
            for component, scale in zip(components, scales, strict=True)
        ],
        "counties_sha256": _sha(county_path),
        "edges_sha256": _sha(edge_path),
    }
    expected_graph_hash = _canonical_sha(graph_identity)
    expected_graph_contract = {
        "schema_id": "sr_v2_spatial_graph_contract/v1",
        "run_id": RUN_ID,
        "nodes": len(counties),
        "undirected_edges": len(edge_path.read_text(encoding="utf-8").splitlines()),
        "components": len(components),
        "nonisolated_nodes": sum(len(component) for component in components if len(component) > 1),
        "county_order_sha256": _sha(county_path),
        "edge_list_sha256": _sha(edge_path),
        "component_scales": component_rows,
        "graph_contract_sha256": expected_graph_hash,
    }
    graph_contract_path = prepared / "graph/graph_contract.json"
    graph_contract = json.loads(graph_contract_path.read_text(encoding="utf-8"))
    if (
        graph_contract != expected_graph_contract
        or manifest.get("graph_contract") != expected_graph_contract
        or manifest.get("graph_contract_sha256") != expected_graph_hash
    ):
        raise ValueError("Prepared graph contract differs from independent reconstruction")
    protected_path = prepared / str(manifest.get("protected_tree_manifest", ""))
    protected_hash = _sidecar(protected_path)
    if protected_hash != manifest.get("protected_tree_manifest_sha256"):
        raise ValueError("Prepared protected-tree manifest hash mismatch")
    _verify_protected_trees(
        root, json.loads(protected_path.read_text(encoding="utf-8"))
    )
    mapping = manifest.get("chain_mapping")
    if not isinstance(mapping, list) or len(mapping) != 4:
        raise ValueError("Preparation must bind exactly four chains")
    mapping_fields = {
        "array_index", "chain_id", "chain_seed", "allocation_initialization_seed",
        "spatial_initialization_seed", "target_identity", "target_fingerprint",
        "chain_fingerprint", "initial_allocation", "initial_allocation_sha256",
        "initial_checkpoint", "initial_checkpoint_sha256",
    }
    allocation_hashes: set[str] = set()
    chain_fingerprints: set[str] = set()
    for chain_id, row in enumerate(mapping, start=1):
        seeds = {
            "chain_seed": CHAIN_SEEDS[chain_id - 1],
            "allocation_initialization_seed": ALLOCATION_SEEDS[chain_id - 1],
            "spatial_initialization_seed": SPATIAL_SEEDS[chain_id - 1],
        }
        if (
            not isinstance(row, Mapping)
            or set(row) != mapping_fields
            or row.get("array_index") != chain_id
            or row.get("chain_id") != chain_id
            or any(row.get(key) != value for key, value in seeds.items())
            or row.get("initial_allocation")
            != f"initializations/initial_allocation_chain_{chain_id:02d}.parquet"
            or row.get("initial_checkpoint")
            != (
                f"initial_checkpoints/chain_{chain_id:02d}/"
                "checkpoint_epoch_0_attempt_1_iter_000000000.json"
            )
        ):
            raise ValueError("Prepared chain mapping exact schema/seed mismatch")
        allocation_path = _safe(prepared, row["initial_allocation"])
        checkpoint_path = _safe(prepared, row["initial_checkpoint"])
        if (
            _sha(allocation_path) != row.get("initial_allocation_sha256")
            or _sidecar(checkpoint_path) != row.get("initial_checkpoint_sha256")
        ):
            raise ValueError("Prepared chain initialization hash mismatch")
        allocation = pd.read_parquet(allocation_path)
        expected_columns = ["county_fips", "year", "q002_count_status", "latent_count"]
        if (
            list(allocation.columns) != expected_columns
            or len(allocation) != len(prepared_frame)
            or not allocation[["county_fips", "year", "q002_count_status"]].equals(
                prepared_frame[["county_fips", "year", "q002_count_status"]].reset_index(drop=True)
            )
            or allocation["latent_count"].to_numpy().dtype != np.dtype("<i8")
        ):
            raise ValueError("Prepared allocation exact frame/schema mismatch")
        _validate_terminal_counts(
            allocation["latent_count"].to_numpy(dtype=np.int64), prepared_frame
        )
        identity = _validate_target_identity(
            row.get("target_identity"),
            expected_target=expected_target,
            chain_id=chain_id,
            seeds=seeds,
        )
        if (
            row.get("target_fingerprint") != identity.get("target_fingerprint")
            or row.get("chain_fingerprint") != identity.get("chain_fingerprint")
        ):
            raise ValueError("Prepared target/chain fingerprint binding mismatch")
        checkpoint = _load_canonical_checkpoint(checkpoint_path)
        _validate_checkpoint_payload(
            checkpoint,
            identity=identity,
            seeds=seeds,
            expected_epoch=0,
            expected_attempt=1,
            expected_iteration=0,
            expected_draws=0,
            expected_chunks=0,
            row_count=len(prepared_frame),
            county_count=len(counties),
            labels=labels,
            expected_y=allocation["latent_count"].to_numpy(dtype=np.int64),
        )
        _validate_checkpoint_target(
            checkpoint,
            target=identity["target"],
            frame=prepared_frame,
            counties=counties,
            adjacency=adjacency,
            components=components,
            scales=scales,
            label="Prepared checkpoint",
        )
        allocation_hashes.add(str(row["initial_allocation_sha256"]))
        chain_fingerprints.add(str(row["chain_fingerprint"]))
    if len(allocation_hashes) != 4 or len(chain_fingerprints) != 4:
        raise ValueError("Prepared starts/fingerprints must be distinct across four chains")
    _validate_preparation_identity(manifest, mapping)
    return manifest, prepared


def _graph_from_prepared(
    prepared: Path, config: Mapping[str, Any]
) -> tuple[list[str], sparse.csr_matrix, np.ndarray, tuple[np.ndarray, ...], tuple[float, ...]]:
    county_path = prepared / "graph/county_order.txt"
    edge_path = prepared / "graph/edge_list.txt"
    counties = county_path.read_text(encoding="utf-8").splitlines()
    if (
        not counties
        or counties != sorted(counties)
        or len(set(counties)) != len(counties)
        or any(len(value) != 5 or not value.isdigit() for value in counties)
    ):
        raise ValueError("Prepared county order is not exact sorted five-digit FIPS")
    index = {county: offset for offset, county in enumerate(counties)}
    edge_rows = edge_path.read_text(encoding="utf-8").splitlines()
    edges: list[tuple[str, str]] = []
    for row in edge_rows:
        parts = row.split("|")
        if len(parts) != 2 or parts[0] >= parts[1] or any(part not in index for part in parts):
            raise ValueError("Prepared edge list is malformed or noncanonical")
        edges.append((parts[0], parts[1]))
    if edges != sorted(set(edges)):
        raise ValueError("Prepared edge list is not unique lexicographic order")
    rows = np.asarray([index[left] for left, _ in edges] + [index[right] for _, right in edges])
    cols = np.asarray([index[right] for _, right in edges] + [index[left] for left, _ in edges])
    adjacency = sparse.csr_matrix(
        (np.ones(len(rows), dtype=np.float64), (rows, cols)),
        shape=(len(counties), len(counties)),
    )
    component_count, labels = connected_components(adjacency, directed=False)
    components = tuple(
        np.flatnonzero(labels == component_id).astype(np.int64)
        for component_id in range(component_count)
    )
    components = tuple(sorted(components, key=lambda part: counties[int(part[0])]))
    recomputed: list[float] = []
    for component in components:
        if len(component) == 1:
            recomputed.append(0.0)
            continue
        block = adjacency[component][:, component].toarray().astype(np.float64)
        precision = np.diag(block.sum(axis=1)) - block
        covariance = np.linalg.pinv(precision, hermitian=True)
        diagonal = np.diag(covariance)
        if not np.isfinite(diagonal).all() or np.any(diagonal <= 0.0):
            raise ValueError("Independent component pseudoinverse is invalid")
        recomputed.append(float(np.exp(np.mean(np.log(diagonal), dtype=np.float64))))
    component_table = pd.read_csv(prepared / "graph/components.csv", dtype=str)
    expected_table = pd.DataFrame(
        {
            "component_id": [str(value) for value in range(len(components))],
            "minimum_fips": [counties[int(part[0])] for part in components],
            "size": [str(len(part)) for part in components],
            "singleton": ["true" if len(part) == 1 else "false" for part in components],
            "scale_hex": [float(value).hex() for value in recomputed],
        }
    )
    if not component_table.equals(expected_table):
        raise ValueError("Independent graph-component/scale recomputation differs")
    certificate = config["graph_certificate"]
    if (
        len(counties) != certificate["nodes"]
        or len(edges) != certificate["undirected_edges"]
        or len(components) != certificate["components"]
        or int(sum(len(part) for part in components if len(part) > 1))
        != certificate["nonisolated_nodes"]
        or hashlib.sha256(county_path.read_bytes()).hexdigest()
        != certificate["county_order_sha256"]
        or hashlib.sha256(edge_path.read_bytes()).hexdigest()
        != certificate["edge_list_sha256"]
    ):
        raise ValueError("Independent graph cardinality/hash certificate differs")
    certified = {
        row["minimum_fips"]: row["scale_hex"]
        for row in certificate["non_singleton_components"]
    }
    observed = {
        counties[int(part[0])]: float(scale).hex()
        for part, scale in zip(components, recomputed, strict=True)
        if len(part) > 1
    }
    if observed != certified:
        raise ValueError("Independent graph-scale hex certificate differs")
    return counties, adjacency, labels, components, tuple(recomputed)


def _array(payload: object, dtype: str) -> np.ndarray:
    if not isinstance(payload, Mapping) or set(payload) != {"dtype", "shape", "data_base64"}:
        raise ValueError("Checkpoint array payload schema mismatch")
    expected = np.dtype(dtype)
    shape_payload = payload["shape"]
    encoded = payload["data_base64"]
    if (
        payload["dtype"] != expected.str
        or not isinstance(shape_payload, list)
        or not isinstance(encoded, str)
    ):
        raise ValueError("Checkpoint array dtype/shape mismatch")
    shape = tuple(
        _exact_integer(value, "checkpoint array shape") for value in shape_payload
    )
    if any(value < 0 for value in shape):
        raise ValueError("Checkpoint array shape must be nonnegative")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (TypeError, ValueError) as error:
        raise ValueError("Checkpoint array base64 is invalid") from error
    if math.prod(shape) * expected.itemsize != len(raw):
        raise ValueError("Checkpoint array byte length mismatch")
    result = np.frombuffer(raw, dtype=expected).reshape(shape).copy()
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise ValueError("Checkpoint array base64 is noncanonical")
    return result


def _expected_draw_epoch(draw_id: int) -> int:
    if 1 <= draw_id <= 4_500:
        return 0
    if draw_id <= 7_500:
        return 1
    if draw_id <= 10_500:
        return 2
    if draw_id <= 13_500:
        return 3
    raise ValueError("Draw id lies outside the frozen schedule")


def _verify_schedule(
    chain_root: Path,
    chain_id: int,
    epoch: int,
    draws: int,
    status: Mapping[str, Any],
) -> dict[str, object]:
    if status.get("executor_builder") != "exact_public_chain_loop":
        raise ValueError("Independent verification requires actual public-loop evidence")
    records: list[dict[str, object]] = []
    manifest_hashes: dict[str, str] = {}
    evidence_fields = {
        "schema_id", "run_id", "chain_id", "extension_epoch", "job_attempt",
        "start_saved_draws", "end_saved_draws", "record_count", "ledger_path",
        "ledger_sha256", "evidence_builder", "production_executor", "capture_order",
        "count_constraint_failures", "spatial_constraint_failures",
        "historical_latent_y_stored",
        "independent_historical_y_reconstruction_possible", "verification_boundary",
    }
    for evidence_epoch in range(epoch + 1):
        evidence_root = chain_root / f"evidence/epoch_{evidence_epoch}"
        manifests = sorted(evidence_root.glob("attempt_*/attempt_evidence.json"))
        if not manifests:
            raise ValueError("Retained-assertion evidence manifest is missing")
        for evidence_path in manifests:
            evidence_hash = _sidecar(evidence_path)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            if (
                not isinstance(evidence, Mapping)
                or set(evidence) != evidence_fields
                or
                evidence.get("schema_id") != "sr_v2_spatial_attempt_evidence/v1"
                or evidence.get("run_id") != RUN_ID
                or evidence.get("chain_id") != chain_id
                or evidence.get("extension_epoch") != evidence_epoch
                or evidence.get("job_attempt")
                != int(evidence_path.parent.name.removeprefix("attempt_"))
                or evidence.get("start_saved_draws") != len(records)
                or evidence.get("evidence_builder") != "actual_public_chain_loop"
                or evidence.get("production_executor") is not True
                or evidence.get("capture_order")
                != "after_latent_target_base6_hyper_and_scheduled_mala"
                or evidence.get("count_constraint_failures") != 0
                or evidence.get("spatial_constraint_failures") != 0
                or evidence.get("historical_latent_y_stored") is not False
                or evidence.get("independent_historical_y_reconstruction_possible")
                is not False
            ):
                raise ValueError("Retained-assertion evidence contract mismatch")
            ledger = evidence_path.parent / str(evidence.get("ledger_path", ""))
            _inventory(
                evidence_path.parent,
                {str(evidence.get("ledger_path", "")): evidence.get("ledger_sha256")},
                exact_files=True,
                allowed_files=("attempt_evidence.json", "attempt_evidence.json.sha256"),
            )
            if _sha(ledger) != evidence.get("ledger_sha256"):
                raise ValueError("Retained-assertion ledger hash mismatch")
            lines = ledger.read_bytes().splitlines()
            if len(lines) != evidence.get("record_count"):
                raise ValueError("Retained-assertion ledger cardinality mismatch")
            for line in lines:
                record = json.loads(line)
                unsigned = {
                    key: record[key]
                    for key in record
                    if key != "assertion_sha256"
                }
                if record.get("assertion_sha256") != _canonical_sha(unsigned):
                    raise ValueError("Retained-assertion record digest mismatch")
                records.append(record)
            if evidence.get("end_saved_draws") != len(records):
                raise ValueError("Retained-assertion end position mismatch")
            manifest_hashes[evidence_path.relative_to(chain_root).as_posix()] = evidence_hash
    if len(records) != draws:
        raise ValueError("Retained-assertion cumulative cardinality mismatch")
    for draw_id, record in enumerate(records, start=1):
        if (
            record.get("schema_id") != "sr_v2_spatial_retained_assertion/v1"
            or record.get("chain_id") != chain_id
            or record.get("draw_id") != draw_id
            or record.get("cumulative_iteration") != 45_000 + 30 * draw_id
            or record.get("extension_epoch") != _expected_draw_epoch(draw_id)
            or record.get("chunk_id") != (draw_id - 1) // 250 + 1
            or record.get("count_constraints_asserted") is not True
            or record.get("spatial_constraints_asserted") is not True
            or len(_require_hash(record.get("latent_y_sha256"), "latent y digest"))
            != 64
            or len(
                _require_hash(
                    record.get("structured_effect_sha256"),
                    "structured-effect digest",
                )
            )
            != 64
        ):
            raise ValueError("Retained-assertion schedule/content mismatch")
    digest = hashlib.sha256(
        b"".join(_canonical_bytes(record) + b"\n" for record in records)
    ).hexdigest()
    bound = status.get("retained_assertion_evidence")
    if (
        not isinstance(bound, Mapping)
        or bound.get("records") != draws
        or bound.get("ledger_sha256") != digest
        or bound.get("manifest_sha256") != manifest_hashes
        or bound.get("historical_latent_y_stored") is not False
        or bound.get("independent_historical_y_reconstruction_possible") is not False
    ):
        raise ValueError("Status does not bind retained-assertion evidence")
    return {"records": draws, "ledger_sha256": digest}


def _latest_immutable_status(
    chain_root: Path, chain_id: int
) -> tuple[dict[str, Any], Path]:
    attempts_root = chain_root / "attempts"
    if not attempts_root.is_dir() or attempts_root.is_symlink():
        raise ValueError("Immutable attempt root is missing or unsafe")
    candidates: list[tuple[int, int, Path, dict[str, Any]]] = []
    for path in sorted(attempts_root.glob("epoch_*/attempt_*/status.json")):
        if path.is_symlink():
            raise ValueError("Immutable status must not be a symlink")
        try:
            epoch = int(path.parents[1].name.removeprefix("epoch_"))
            attempt = int(path.parent.name.removeprefix("attempt_"))
        except ValueError as error:
            raise ValueError("Immutable status path is malformed") from error
        if (
            path.parents[1].name != f"epoch_{epoch}"
            or path.parent.name != f"attempt_{attempt}"
            or epoch not in range(4)
            or attempt not in range(1, 4)
        ):
            raise ValueError("Immutable status path violates epoch/attempt bounds")
        _sidecar(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("chain_id") != chain_id
            or payload.get("extension_epoch") != epoch
            or payload.get("job_attempt") != attempt
        ):
            raise ValueError("Immutable status path/payload identity mismatch")
        candidates.append((epoch, attempt, path, payload))
    if not candidates:
        raise ValueError("No immutable attempt status exists")
    keys = [(epoch, attempt) for epoch, attempt, _path, _payload in candidates]
    if len(keys) != len(set(keys)):
        raise ValueError("Immutable attempt position is not unique")
    _epoch, _attempt, immutable, status = max(candidates, key=lambda row: row[:2])
    allowed = [
        immutable.relative_to(chain_root).as_posix(),
        immutable.with_name(immutable.name + ".sha256")
        .relative_to(chain_root)
        .as_posix(),
    ]
    for name in ("chain_status.json", "chain_status.json.sha256"):
        pointer = chain_root / name
        if os.path.lexists(pointer):
            if not pointer.is_file() or pointer.is_symlink():
                raise ValueError("Mutable status pointer is unsafe")
            allowed.append(name)
    _inventory(
        chain_root,
        status.get("artifact_sha256"),
        exact_files=True,
        allowed_files=tuple(allowed),
    )
    return status, immutable


def _frame_scalar_token(value: Any) -> bytes:
    if value is None or value is pd.NA:
        return b"null"
    if isinstance(value, (bool, np.bool_)):
        return b"bool:1" if bool(value) else b"bool:0"
    if isinstance(value, (int, np.integer)):
        return f"int:{int(value)}".encode("ascii")
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if np.isnan(numeric):
            return b"null"
        if not np.isfinite(numeric):
            raise ValueError("Model-frame semantic hash rejects infinity")
        return f"float:{numeric.hex()}".encode("ascii")
    if isinstance(value, pd.Timestamp):
        return f"timestamp:{value.isoformat()}".encode("utf-8")
    if isinstance(value, str):
        return b"str:" + value.encode("utf-8")
    raise ValueError("Unsupported model-frame semantic scalar")


def _model_frame_semantic_sha256(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()

    def add(payload: bytes) -> None:
        digest.update(len(payload).to_bytes(8, "little", signed=False))
        digest.update(payload)

    add(b"sr_v2_spatial_model_frame_semantic/v1")
    add(str(len(frame)).encode("ascii"))
    for key in sorted(frame.attrs):
        if not isinstance(key, str):
            raise ValueError("Model-frame attribute name is not a string")
        add(b"attr:" + key.encode("utf-8"))
        add(_frame_scalar_token(frame.attrs[key]))
    for column in frame.columns:
        if not isinstance(column, str):
            raise ValueError("Model-frame column name is not a string")
        add(column.encode("utf-8"))
        add(str(frame[column].dtype).encode("ascii"))
        for value in frame[column].array:
            add(_frame_scalar_token(value))
    return digest.hexdigest()


def _validate_terminal_counts(y: np.ndarray, frame: pd.DataFrame) -> None:
    required = {
        "county_fips", "state_fips", "year", "q002_lower", "q002_upper",
        "q002_count_status", "q001_period_lower", "q001_period_upper",
        "q004_state_year_total", "q003_national_year_total",
    }
    if not required.issubset(frame.columns) or y.dtype != np.dtype("<i8") or y.shape != (len(frame),):
        raise ValueError("Terminal latent-count frame/schema mismatch")
    lower = frame["q002_lower"].to_numpy(dtype=np.int64)
    upper = frame["q002_upper"].to_numpy(dtype=np.int64)
    status = frame["q002_count_status"].astype(str).to_numpy()
    if np.any(y < 0) or np.any(y < lower) or np.any(y > upper):
        raise ValueError("Terminal latent counts violate row bounds")
    exact = status == "exact"
    zero = status == "zero"
    suppressed = status == "suppressed_1_9"
    if (
        not np.array_equal(y[exact], lower[exact])
        or np.any(y[zero] != 0)
        or np.any((y[suppressed] < 1) | (y[suppressed] > 9))
    ):
        raise ValueError("Terminal latent counts violate status constraints")
    work = frame[
        ["county_fips", "state_fips", "year", "q001_period_lower",
         "q001_period_upper", "q004_state_year_total", "q003_national_year_total"]
    ].copy()
    work["_y"] = y
    county = work.groupby("county_fips", sort=False)["_y"].sum()
    period = frame.drop_duplicates("county_fips").set_index("county_fips")
    period = period.loc[county.index]
    if np.any(county.to_numpy() < period["q001_period_lower"].to_numpy()) or np.any(
        county.to_numpy() > period["q001_period_upper"].to_numpy()
    ):
        raise ValueError("Terminal latent counts violate county-period bounds")
    state_year = work.groupby(["state_fips", "year"], sort=False)["_y"].sum()
    state_target = frame.drop_duplicates(["state_fips", "year"]).set_index(
        ["state_fips", "year"]
    )["q004_state_year_total"].loc[state_year.index]
    national = work.groupby("year", sort=False)["_y"].sum()
    national_target = frame.drop_duplicates("year").set_index("year")[
        "q003_national_year_total"
    ].loc[national.index]
    if not np.array_equal(state_year.to_numpy(dtype=np.int64), state_target.to_numpy(dtype=np.int64)):
        raise ValueError("Terminal latent counts violate state-year totals")
    if not np.array_equal(national.to_numpy(dtype=np.int64), national_target.to_numpy(dtype=np.int64)):
        raise ValueError("Terminal latent counts violate national-year totals")
    if int(y.sum()) != int(national_target.sum()) or len(county) != frame["county_fips"].nunique():
        raise ValueError("Terminal latent counts violate full coverage/total")


def _load_extension_authorization(
    run_root: Path,
    *,
    to_epoch: int,
    prepared_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if to_epoch not in (1, 2, 3):
        raise ValueError("Extension authorization epoch must be in 1..3")
    authorization_path = run_root / f"extension_authorization_epoch_{to_epoch}.json"
    _sidecar(authorization_path)
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorization_fields = {
        "schema_id", "run_id", "from_extension_epoch", "to_extension_epoch",
        "reason_convergence_only", "reviewer", "reviewed_utc", "authorization_sha256",
        "prior_preparation_identity", "prior_pre_gate_manifest_sha256",
        "prior_independent_verification_sha256", "prior_release_manifest_sha256",
        "prior_gate_decision_sha256",
    }
    if not isinstance(authorization, Mapping) or set(authorization) != authorization_fields:
        raise ValueError("Extension authorization exact schema mismatch")
    unsigned = {
        key: authorization[key]
        for key in authorization
        if key != "authorization_sha256"
    }
    if (
        authorization.get("schema_id")
        != "sr_v2_spatial_extension_authorization/v1"
        or authorization.get("run_id") != RUN_ID
        or authorization.get("from_extension_epoch") != to_epoch - 1
        or authorization.get("to_extension_epoch") != to_epoch
        or authorization.get("reason_convergence_only") is not True
        or not isinstance(authorization.get("reviewer"), str)
        or not authorization["reviewer"].strip()
        or not isinstance(authorization.get("reviewed_utc"), str)
        or not authorization["reviewed_utc"].strip()
        or authorization.get("authorization_sha256") != _canonical_sha(unsigned)
    ):
        raise ValueError("Extension authorization identity/review mismatch")
    prior_evidence = {
        "prior_pre_gate_manifest_sha256": run_root
        / f"epochs/epoch_{to_epoch - 1}/merge/pre_gate_manifest.json",
        "prior_independent_verification_sha256": run_root
        / f"epochs/epoch_{to_epoch - 1}/verification/independent_spatial_sensitivity_verification.json",
        "prior_release_manifest_sha256": run_root
        / f"epochs/epoch_{to_epoch - 1}/release/spatial_sensitivity_release_manifest.json",
        "prior_gate_decision_sha256": run_root
        / f"epochs/epoch_{to_epoch - 1}/gate/gate_decision.json",
    }
    for field, prior_path in prior_evidence.items():
        if _sidecar(prior_path) != authorization.get(field):
            raise ValueError("Extension authorization prior evidence hash mismatch")
    prior_gate = json.loads(
        prior_evidence["prior_gate_decision_sha256"].read_text(encoding="utf-8")
    )
    if (
        authorization.get("prior_preparation_identity")
        != prepared_manifest["preparation_identity"]
        or prior_gate.get("status") != "HOLD"
        or prior_gate.get("reason") != "convergence_only"
        or prior_gate.get("extension_eligible") is not True
        or prior_gate.get("preparation_identity")
        != prepared_manifest["preparation_identity"]
        or prior_gate.get("pre_gate_manifest_sha256")
        != authorization.get("prior_pre_gate_manifest_sha256")
        or prior_gate.get("independent_verification_sha256")
        != authorization.get("prior_independent_verification_sha256")
        or prior_gate.get("release_manifest_sha256")
        != authorization.get("prior_release_manifest_sha256")
    ):
        raise ValueError("Extension authorization does not bind convergence-only HOLD")
    return dict(authorization)


_CHUNK_RECORD_FIELDS = {
    "schema_id", "chain_id", "extension_epoch", "chunk_id", "draw_start",
    "draw_end", "draw_count", "scalar_path", "scalar_sha256", "spatial_path",
    "spatial_sha256", "graph_contract_sha256", "county_order_sha256",
    "county_count", "parameter_schema",
}


def _validate_raw_chunk(
    *,
    chunk_root: Path,
    record: Mapping[str, Any],
    chain_id: int,
    chunk_id: int,
    parameter_schema: Sequence[str],
    counties: Sequence[str],
    labels: np.ndarray,
    graph_contract_sha256: str,
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    if not isinstance(record, Mapping) or set(record) != _CHUNK_RECORD_FIELDS:
        raise ValueError("Raw chunk record exact schema mismatch")
    draw_start = (chunk_id - 1) * 250 + 1
    draw_end = chunk_id * 250
    record_epoch = _expected_draw_epoch(draw_start)
    expected_scalar = f"scalar_chunk_{chunk_id:06d}.parquet"
    expected_spatial = f"spatial_chunk_{chunk_id:06d}.npz"
    county_order_hash = hashlib.sha256(
        "".join(f"{county}\n" for county in counties).encode("utf-8")
    ).hexdigest()
    if (
        record.get("schema_id") != "sr_v2_spatial_draw_chunk/v1"
        or type(record.get("chain_id")) is not int
        or record.get("chain_id") != chain_id
        or type(record.get("extension_epoch")) is not int
        or record.get("extension_epoch") != record_epoch
        or type(record.get("chunk_id")) is not int
        or record.get("chunk_id") != chunk_id
        or record.get("draw_start") != draw_start
        or record.get("draw_end") != draw_end
        or record.get("draw_count") != 250
        or record.get("scalar_path") != expected_scalar
        or record.get("spatial_path") != expected_spatial
        or record.get("graph_contract_sha256") != graph_contract_sha256
        or record.get("county_order_sha256") != county_order_hash
        or record.get("county_count") != len(counties)
        or record.get("parameter_schema") != list(parameter_schema)
    ):
        raise ValueError("Raw chunk identity/schedule mismatch")
    scalar_path = _safe(chunk_root, expected_scalar)
    spatial_path = _safe(chunk_root, expected_spatial)
    if _sha(scalar_path) != record.get("scalar_sha256") or _sha(spatial_path) != record.get("spatial_sha256"):
        raise ValueError("Raw chunk bytes changed")
    scalar = pd.read_parquet(scalar_path)
    columns = ["chain_id", "draw_id", "extension_epoch", "parameter", "value"]
    expected_draws = np.arange(draw_start, draw_end + 1, dtype=np.int64)
    if (
        list(scalar.columns) != columns
        or len(scalar) != 250 * len(parameter_schema)
        or scalar["chain_id"].to_numpy().dtype != np.dtype("<i8")
        or scalar["draw_id"].to_numpy().dtype != np.dtype("<i8")
        or scalar["extension_epoch"].to_numpy().dtype != np.dtype("<i8")
        or scalar["value"].to_numpy().dtype != np.dtype("<f8")
        or not scalar["parameter"].map(lambda value: isinstance(value, str)).all()
        or not np.isfinite(scalar["value"].to_numpy()).all()
        or not np.array_equal(scalar["chain_id"].to_numpy(), np.full(len(scalar), chain_id, dtype=np.int64))
        or not np.array_equal(scalar["draw_id"].to_numpy(), np.repeat(expected_draws, len(parameter_schema)))
        or not np.array_equal(scalar["extension_epoch"].to_numpy(), np.full(len(scalar), record_epoch, dtype=np.int64))
        or scalar["parameter"].tolist() != list(parameter_schema) * 250
        or scalar.duplicated(["chain_id", "draw_id", "parameter"]).any()
    ):
        raise ValueError("Raw scalar chunk exact grid/dtype/cardinality mismatch")
    with np.load(spatial_path, allow_pickle=False) as archive:
        if set(archive.files) != {"chain_id", "extension_epoch", "draw_id", "structured", "unstructured"}:
            raise ValueError("Raw spatial chunk exact array schema mismatch")
        arrays = {name: archive[name].copy() for name in archive.files}
    structured = arrays["structured"]
    unstructured = arrays["unstructured"]
    if (
        arrays["chain_id"].dtype != np.dtype("<i8")
        or arrays["chain_id"].shape != ()
        or int(arrays["chain_id"].item()) != chain_id
        or arrays["extension_epoch"].dtype != np.dtype("<i8")
        or arrays["extension_epoch"].shape != ()
        or int(arrays["extension_epoch"].item()) != record_epoch
        or arrays["draw_id"].dtype != np.dtype("<i8")
        or arrays["draw_id"].shape != (250,)
        or not np.array_equal(arrays["draw_id"], expected_draws)
        or structured.dtype != np.dtype("<f8")
        or unstructured.dtype != np.dtype("<f8")
        or structured.shape != (250, len(counties))
        or unstructured.shape != (250, len(counties))
        or not np.isfinite(structured).all()
        or not np.isfinite(unstructured).all()
    ):
        raise ValueError("Raw spatial chunk exact identity/dtype/shape mismatch")
    for component_id in np.unique(labels):
        indices = np.flatnonzero(labels == component_id)
        if len(indices) == 1:
            if np.any(structured[:, indices] != 0.0):
                raise ValueError("Raw singleton structured draw is not exact zero")
        elif np.max(np.abs(structured[:, indices].mean(axis=1))) > 1e-12:
            raise ValueError("Raw structured draws are not component-centered")
    return scalar, arrays


def _verify_chains(
    run_root: Path,
    prepared_manifest: Mapping[str, Any],
    epoch: int,
    frame: pd.DataFrame,
    counties: Sequence[str],
    adjacency: sparse.csr_matrix,
    labels: np.ndarray,
    components: Sequence[np.ndarray],
    scales: Sequence[float],
) -> tuple[
    pd.DataFrame,
    dict[str, np.ndarray],
    list[dict[str, Any]],
    dict[str, str],
    list[dict[str, Any]],
]:
    expected = EPOCH_CONTRACT[epoch]
    parameter_schema = list(prepared_manifest["parameter_schema"])
    scalar_parts: list[pd.DataFrame] = []
    spatial_parts: dict[str, list[np.ndarray]] = {
        "chain_id": [],
        "extension_epoch": [],
        "draw_id": [],
        "structured": [],
        "unstructured": [],
    }
    statuses: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    ledger_hashes: dict[str, str] = {}
    terminal_checkpoints: list[dict[str, Any]] = []
    singleton = np.asarray(
        [len(np.flatnonzero(labels == labels[index])) == 1 for index in range(len(labels))]
    )
    for chain_id in range(1, 5):
        chain_root = run_root / f"chains/chain_{chain_id:02d}"
        status, immutable_status = _latest_immutable_status(chain_root, chain_id)
        seeds = {
            "chain_seed": CHAIN_SEEDS[chain_id - 1],
            "allocation_initialization_seed": ALLOCATION_SEEDS[chain_id - 1],
            "spatial_initialization_seed": SPATIAL_SEEDS[chain_id - 1],
        }
        if (
            set(status) != CHAIN_STATUS_EXACT_FIELDS
            or status.get("schema_id") != "sr_v2_spatial_chain_status/v1"
            or status.get("run_id") != RUN_ID
            or status.get("model_id") != MODEL_ID
            or status.get("status") != "completed"
            or status.get("chain_id") != chain_id
            or status.get("array_index") != chain_id
            or status.get("extension_epoch") != epoch
            or type(status.get("job_attempt")) is not int
            or status.get("job_attempt") not in (1, 2, 3)
            or status.get("iterations") != expected["iterations"]
            or status.get("retained_draws") != expected["draws"]
            or status.get("chunks") != expected["chunks"]
            or status.get("seeds") != seeds
            or status.get("preparation_identity")
            != prepared_manifest["preparation_identity"]
            or status.get("launch_envelope_sha256")
            != prepared_manifest["launch_envelope_sha256"]
            or status.get("final_source_manifest_sha256")
            != prepared_manifest["final_source_manifest_sha256"]
            or status.get("failure_category") is not None
            or status.get("retryable") is not False
            or status.get("submission_authorized") is not False
            or not isinstance(status.get("updated_utc"), str)
            or not status["updated_utc"].strip()
        ):
            raise ValueError("Independent chain status/seed/cardinality check failed")
        _validate_terminal_checkpoint_path(
            status, epoch=epoch, iteration=expected["iterations"]
        )
        identity = status.get("identity")
        if not isinstance(identity, Mapping) or set(identity) != {
            "schema_version",
            "target",
            "target_fingerprint",
            "chain",
            "chain_fingerprint",
        }:
            raise ValueError("Chain identity schema mismatch")
        if identity.get("schema_version") != 2:
            raise ValueError("Chain identity schema version mismatch")
        prepared_row = prepared_manifest["chain_mapping"][chain_id - 1]
        if (
            prepared_row.get("array_index") != chain_id
            or prepared_row.get("chain_id") != chain_id
            or prepared_row.get("chain_seed") != seeds["chain_seed"]
            or prepared_row.get("allocation_initialization_seed")
            != seeds["allocation_initialization_seed"]
            or prepared_row.get("spatial_initialization_seed")
            != seeds["spatial_initialization_seed"]
        ):
            raise ValueError("Prepared chain mapping/seed identity mismatch")
        base_identity = prepared_row.get("target_identity")
        if not isinstance(base_identity, Mapping) or not isinstance(
            base_identity.get("target"), Mapping
        ):
            raise ValueError("Prepared base target identity is missing")
        expected_target = dict(base_identity["target"])
        if epoch == 0:
            authorization = None
            expected_target["extension_epoch"] = 0
            expected_target["extension_authorization_sha256"] = "0" * 64
        else:
            authorization = _load_extension_authorization(
                run_root,
                to_epoch=epoch,
                prepared_manifest=prepared_manifest,
            )
            expected_target["extension_epoch"] = epoch
            expected_target["extension_authorization_sha256"] = authorization[
                "authorization_sha256"
            ]
        identity = _validate_target_identity(
            identity,
            expected_target=expected_target,
            chain_id=chain_id,
            seeds=seeds,
        )
        if epoch == 0:
            if identity != base_identity:
                raise ValueError("Epoch-zero chain identity differs from preparation")
        else:
            prior_candidates = sorted(
                chain_root.glob(f"attempts/epoch_{epoch - 1}/attempt_*/status.json")
            )
            if not prior_candidates:
                raise ValueError("Prior epoch immutable chain status is missing")
            prior_path = max(
                prior_candidates,
                key=lambda path: int(path.parent.name.removeprefix("attempt_")),
            )
            _sidecar(prior_path)
            prior_status = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_expected = EPOCH_CONTRACT[epoch - 1]
            if (
                prior_status.get("status") != "completed"
                or prior_status.get("extension_epoch") != epoch - 1
                or prior_status.get("iterations") != prior_expected["iterations"]
                or prior_status.get("retained_draws") != prior_expected["draws"]
                or prior_status.get("chunks") != prior_expected["chunks"]
                or prior_status.get("seeds") != seeds
            ):
                raise ValueError("Prior epoch terminal chain status is invalid")
            prior_identity = prior_status.get("identity")
            if not isinstance(prior_identity, Mapping):
                raise ValueError("Prior epoch identity is missing")
            prior_expected_target = dict(base_identity["target"])
            prior_expected_target["extension_epoch"] = epoch - 1
            if epoch - 1 == 0:
                prior_expected_target["extension_authorization_sha256"] = "0" * 64
            else:
                prior_authorization = _load_extension_authorization(
                    run_root,
                    to_epoch=epoch - 1,
                    prepared_manifest=prepared_manifest,
                )
                prior_expected_target["extension_authorization_sha256"] = (
                    prior_authorization["authorization_sha256"]
                )
            _validate_target_identity(
                prior_identity,
                expected_target=prior_expected_target,
                chain_id=chain_id,
                seeds=seeds,
            )
            if identity["target"] != {
                **prior_identity["target"],
                "extension_epoch": epoch,
                "extension_authorization_sha256": authorization[
                    "authorization_sha256"
                ],
            }:
                raise ValueError("Extension identity is not the exact authorized continuation")
        target_fingerprint = _canonical_sha(identity["target"])
        chain_fingerprint = _canonical_sha(identity["chain"])
        if (
            target_fingerprint != identity["target_fingerprint"]
            or chain_fingerprint != identity["chain_fingerprint"]
            or status.get("target_fingerprint") != target_fingerprint
            or status.get("chain_fingerprint") != chain_fingerprint
            or identity["target"].get("extension_epoch") != epoch
            or identity["chain"].get("chain_id") != chain_id
        ):
            raise ValueError("Chain fingerprint is not independently reproducible")
        fingerprints.add(chain_fingerprint)
        checkpoint_path = _safe(chain_root, status.get("latest_checkpoint"))
        if _sidecar(checkpoint_path) != status.get("latest_checkpoint_sha256"):
            raise ValueError("Latest checkpoint identity/hash mismatch")
        checkpoint = _load_canonical_checkpoint(checkpoint_path)
        _validate_checkpoint_payload(
            checkpoint,
            identity=identity,
            seeds=seeds,
            expected_epoch=epoch,
            expected_attempt=status["job_attempt"],
            expected_iteration=expected["iterations"],
            expected_draws=expected["draws"],
            expected_chunks=expected["chunks"],
            row_count=len(frame),
            county_count=len(counties),
            labels=labels,
        )
        _validate_checkpoint_target(
            checkpoint,
            target=identity["target"],
            frame=frame,
            counties=counties,
            adjacency=adjacency,
            components=components,
            scales=scales,
            label="Terminal checkpoint",
        )
        proposed = checkpoint.get("proposed")
        accepted = checkpoint.get("accepted")
        for name in (
            "beta",
            "state",
            "year",
            "log_sigma_state",
            "log_sigma_year",
            "log_kappa",
            "spatial_hyperparameters",
        ):
            if proposed.get(name) != expected["iterations"]:
                raise ValueError("Base/hyper update counter does not match every iteration")
        if proposed.get("mala") != expected["iterations"] // 5:
            raise ValueError("MALA counter does not match every fifth cumulative iteration")
        if any(
            not isinstance(value, int)
            or value < 0
            or value > proposed.get(name, -1)
            for name, value in accepted.items()
        ):
            raise ValueError("Checkpoint acceptance counters are invalid")
        adaptation = checkpoint.get("adaptation_state")
        if (
            not isinstance(adaptation, Mapping)
            or adaptation.get("adaptation_frozen") is not True
            or adaptation.get("attempted") != proposed["mala"]
        ):
            raise ValueError("Terminal MALA adaptation/counter state is invalid")
        y = _array(checkpoint["current_state"]["y"], "<i8")
        _validate_terminal_counts(y, frame)
        structured_checkpoint = _array(
            checkpoint["current_state"]["spatial_structured"], "<f8"
        )
        if (
            structured_checkpoint.shape != (len(counties),)
            or not np.isfinite(structured_checkpoint).all()
            or not np.array_equal(
                structured_checkpoint[singleton],
                np.zeros(int(singleton.sum()), dtype=np.float64),
            )
        ):
            raise ValueError("Terminal structured state violates singleton constraints")
        for component_id in np.unique(labels):
            indices = np.flatnonzero(labels == component_id)
            if len(indices) > 1 and abs(float(structured_checkpoint[indices].mean())) > 1e-12:
                raise ValueError("Terminal structured state is not component-centered")
        records = checkpoint.get("committed_chunks")
        if not isinstance(records, list) or len(records) != expected["chunks"]:
            raise ValueError("Terminal checkpoint chunk count mismatch")
        ledger = _verify_schedule(
            chain_root, chain_id, epoch, expected["draws"], status
        )
        ledger_hashes[str(chain_id)] = str(ledger["ledger_sha256"])
        chunk_root = chain_root / "chunks"
        manifest_path = chunk_root / "spatial_chunk_manifest.json"
        chunk_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(chunk_manifest, Mapping)
            or set(chunk_manifest) != {"schema_id", "records"}
            or chunk_manifest.get("schema_id") != "sr_v2_spatial_chunk_manifest/v1"
            or chunk_manifest.get("records") != records
        ):
            raise ValueError("Chunk manifest differs from terminal checkpoint")
        expected_chunk_files = {"spatial_chunk_manifest.json"}
        for chunk_id, record in enumerate(records, start=1):
            scalar_chunk, arrays = _validate_raw_chunk(
                chunk_root=chunk_root,
                record=record,
                chain_id=chain_id,
                chunk_id=chunk_id,
                parameter_schema=parameter_schema,
                counties=counties,
                labels=labels,
                graph_contract_sha256=str(prepared_manifest["graph_contract_sha256"]),
            )
            scalar_parts.append(scalar_chunk)
            spatial_parts["chain_id"].append(
                np.full(250, int(arrays["chain_id"].item()), dtype=np.int64)
            )
            spatial_parts["extension_epoch"].append(
                np.full(250, int(arrays["extension_epoch"].item()), dtype=np.int64)
            )
            spatial_parts["draw_id"].append(arrays["draw_id"])
            spatial_parts["structured"].append(arrays["structured"])
            spatial_parts["unstructured"].append(arrays["unstructured"])
            expected_chunk_files.update(
                {str(record["scalar_path"]), str(record["spatial_path"])}
            )
        actual_chunk_files = {
            path.name for path in chunk_root.iterdir()
            if path.is_file() and not path.is_symlink()
        }
        if actual_chunk_files != expected_chunk_files or any(
            path.is_symlink() for path in chunk_root.iterdir()
        ):
            raise ValueError("Raw chunk directory contains orphan/missing/unsafe files")
        statuses.append(status)
        terminal_checkpoints.append(checkpoint)
    if len(fingerprints) != 4:
        raise ValueError("Copied/duplicate chains are forbidden")
    scalar = pd.concat(scalar_parts, ignore_index=True).sort_values(
        ["chain_id", "draw_id", "parameter"], kind="stable"
    ).reset_index(drop=True)
    spatial = {key: np.concatenate(parts, axis=0) for key, parts in spatial_parts.items()}
    order = np.lexsort((spatial["draw_id"], spatial["chain_id"]))
    spatial = {key: value[order] for key, value in spatial.items()}
    return scalar, spatial, statuses, ledger_hashes, terminal_checkpoints


def _diagnostics(
    scalar: pd.DataFrame,
    spatial: Mapping[str, np.ndarray],
    counties: Sequence[str],
    labels: np.ndarray,
    parameter_schema: Sequence[str],
) -> pd.DataFrame:
    import arviz as az

    if az.__version__ != "1.2.0":
        raise ValueError("Independent diagnostics require ArviZ 1.2.0")
    chains = [1, 2, 3, 4]
    draw_ids = sorted(set(spatial["draw_id"].tolist()))
    expected_grid = [(chain, draw) for chain in chains for draw in draw_ids]
    if list(zip(spatial["chain_id"].tolist(), spatial["draw_id"].tolist())) != expected_grid:
        raise ValueError("Merged spatial arrays lack the exact equal chain/draw grid")
    draw_count = len(draw_ids)
    structured = spatial["structured"].reshape(4, draw_count, len(counties))
    unstructured = spatial["unstructured"].reshape(4, draw_count, len(counties))
    scalar_index = scalar.pivot(
        index=["chain_id", "draw_id"], columns="parameter", values="value"
    ).reindex(pd.MultiIndex.from_tuples(expected_grid, names=["chain_id", "draw_id"]))
    if list(scalar_index.columns) != sorted(parameter_schema):
        scalar_index = scalar_index.reindex(columns=list(parameter_schema))
    if scalar_index.isna().any().any() or list(scalar_index.columns) != list(parameter_schema):
        raise ValueError("Merged scalar grid/schema is incomplete")
    sigma = scalar_index["sigma_county"].to_numpy().reshape(4, draw_count)
    phi = scalar_index["phi_structured"].to_numpy().reshape(4, draw_count)
    if np.any(sigma <= 0) or np.any((phi <= 0) | (phi >= 1)):
        raise ValueError("Spatial hyperparameter support violation")
    combined = sigma[:, :, None] * (
        np.sqrt(phi)[:, :, None] * structured
        + np.sqrt(1.0 - phi)[:, :, None] * unstructured
    )

    def row(name: str, values: np.ndarray) -> dict[str, object]:
        result = {
            "parameter": name,
            "r_hat": float(az.rhat(values, method="rank")),
            "ess_bulk": float(az.ess(values, method="bulk")),
            "ess_tail": float(az.ess(values, method="tail", prob=[0.05, 0.95])),
            "arviz_version": "1.2.0",
            "constraint_failures": 0,
        }
        if not np.isfinite([result["r_hat"], result["ess_bulk"], result["ess_tail"]]).all():
            raise ValueError(f"Independent diagnostic is nonfinite for {name}")
        return result

    rows = [
        row(parameter, scalar_index[parameter].to_numpy().reshape(4, draw_count))
        for parameter in parameter_schema
    ]
    singleton = np.asarray(
        [len(np.flatnonzero(labels == labels[index])) == 1 for index in range(len(labels))]
    )
    for index, county in enumerate(counties):
        if not singleton[index]:
            rows.append(row(f"spatial_structured[{county}]", structured[:, :, index]))
        rows.append(row(f"spatial_unstructured[{county}]", unstructured[:, :, index]))
        rows.append(row(f"county_combined[{county}]", combined[:, :, index]))
    return pd.DataFrame(rows)[
        ["parameter", "r_hat", "ess_bulk", "ess_tail", "arviz_version", "constraint_failures"]
    ]


def _threshold_summary(diagnostics: pd.DataFrame) -> dict[str, object]:
    focus = [*COMPARISON_ROWS, "sigma_county", "phi_structured"]
    focus_rows = diagnostics.loc[diagnostics["parameter"].isin(focus)]
    if len(focus_rows) != 10:
        raise ValueError("Independent diagnostics omit focus parameters")
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


def _county_summary(
    scalar: pd.DataFrame,
    spatial: Mapping[str, np.ndarray],
    diagnostics: pd.DataFrame,
    counties: Sequence[str],
    labels: np.ndarray,
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
    diagnostic_index = diagnostics.set_index("parameter")
    singleton_sizes = {
        int(component): int(np.sum(labels == component)) for component in np.unique(labels)
    }
    rows: list[dict[str, object]] = []
    for index, county in enumerate(counties):
        structured = spatial["structured"][:, index]
        unstructured = spatial["unstructured"][:, index]
        combined = sigma * (
            np.sqrt(phi) * structured + np.sqrt(1.0 - phi) * unstructured
        )
        lower, upper = np.quantile(combined, [0.025, 0.975], method="linear")
        diagnostic = diagnostic_index.loc[f"county_combined[{county}]"]
        rows.append(
            {
                "county_fips": county,
                "component_id": int(labels[index]),
                "singleton": singleton_sizes[int(labels[index])] == 1,
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


def _acceptance_summary(
    statuses: Sequence[Mapping[str, Any]],
    checkpoints: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for status, checkpoint in zip(statuses, checkpoints, strict=True):
        if set(checkpoint["proposed"]) != set(checkpoint["accepted"]):
            raise ValueError("Terminal acceptance/proposal counter universe mismatch")
        for transition in sorted(checkpoint["proposed"]):
            proposed = checkpoint["proposed"][transition]
            accepted = checkpoint["accepted"][transition]
            if type(proposed) is not int or type(accepted) is not int or not 0 <= accepted <= proposed:
                raise ValueError("Terminal transition counters are malformed")
            rows.append(
                {
                    "chain_id": status["chain_id"],
                    "transition": transition,
                    "accepted": accepted,
                    "proposed": proposed,
                    "acceptance_rate": accepted / proposed if proposed else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _constraint_summary(extension_epoch: int) -> dict[str, object]:
    expected = EPOCH_CONTRACT[extension_epoch]
    return {
        "schema_id": "sr_v2_spatial_constraint_summary/v1",
        "count_constraint_failures": 0,
        "spatial_constraint_failures": 0,
        "retained_draw_assertions_per_chain": expected["draws"],
        "historical_latent_y_stored": False,
        "independent_historical_y_reconstruction_possible": False,
    }


def _diagnostics_summary(
    diagnostics: pd.DataFrame, extension_epoch: int
) -> dict[str, object]:
    return {
        "schema_id": "sr_v2_spatial_diagnostics_summary/v1",
        "extension_epoch": extension_epoch,
        "rows": len(diagnostics),
        "arviz_version": "1.2.0",
        **_threshold_summary(diagnostics),
    }


def _validate_recorded_csv(
    path: Path,
    expected: pd.DataFrame,
    label: str,
    *,
    dtype: Mapping[str, object] | None = None,
) -> None:
    recorded = pd.read_csv(path, dtype=dtype, float_precision="round_trip")
    if list(recorded.columns) != list(expected.columns) or not recorded.equals(expected):
        raise ValueError(f"{label} differs from independent recomputation")


def _validate_recorded_json(path: Path, expected: Mapping[str, object], label: str) -> None:
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if recorded != expected:
        raise ValueError(f"{label} differs from independent recomputation")


def _comparison_bytes(primary: pd.DataFrame, scalar: pd.DataFrame) -> bytes:
    required_primary = {
        "parameter",
        "posterior_mean",
        "credible_interval_lower_95",
        "credible_interval_upper_95",
    }
    if not required_primary.issubset(primary.columns):
        raise ValueError("Primary comparison summary schema mismatch")
    primary = primary.loc[primary["parameter"].isin(COMPARISON_ROWS)].set_index("parameter")
    if list(primary.index) != list(COMPARISON_ROWS):
        raise ValueError("Primary comparison rows/order mismatch")
    draws = scalar.loc[scalar["parameter"].isin(COMPARISON_ROWS)]
    rows: list[list[str]] = []
    for parameter in COMPARISON_ROWS:
        primary_mean = float(primary.loc[parameter, "posterior_mean"])
        primary_lower = float(primary.loc[parameter, "credible_interval_lower_95"])
        primary_upper = float(primary.loc[parameter, "credible_interval_upper_95"])
        if not np.isfinite([primary_mean, primary_lower, primary_upper]).all() or primary_mean == 0:
            raise ValueError("Primary comparison values must be finite/nonzero")
        raw = draws.loc[draws["parameter"].eq(parameter), "value"].to_numpy(dtype=np.float64)
        reporting = np.exp(raw) if parameter in COMPARISON_ROWS[:6] else raw
        spatial_mean = float(np.mean(reporting, dtype=np.float64))
        spatial_lower, spatial_upper = map(
            float, np.quantile(reporting, [0.025, 0.975], method="linear")
        )
        delta = spatial_mean - primary_mean
        relative = delta / abs(primary_mean)
        values = (
            primary_mean,
            primary_lower,
            primary_upper,
            spatial_mean,
            spatial_lower,
            spatial_upper,
            delta,
            relative,
        )
        if not np.isfinite(values).all():
            raise ValueError("Comparison contains nonfinite values")
        overlap = max(primary_lower, spatial_lower) <= min(primary_upper, spatial_upper)
        rows.append(
            [
                parameter,
                "incidence_rate_ratio"
                if parameter in COMPARISON_ROWS[:6]
                else "standardized_log_rate_coefficient",
                *(format(value, ".17g") for value in values),
                "true" if overlap else "false",
            ]
        )
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=",", lineterminator="\n")
    writer.writerow(COMPARISON_FIELDS)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _verify_merged_semantics(
    *,
    root: Path,
    prepared: Mapping[str, Any],
    extension_epoch: int,
    raw_scalar: pd.DataFrame,
    raw_spatial: Mapping[str, np.ndarray],
    statuses: Sequence[Mapping[str, Any]],
    terminal_checkpoints: Sequence[Mapping[str, Any]],
    counties: Sequence[str],
    labels: np.ndarray,
    pre_gate: Mapping[str, Any],
    merge_root: Path,
) -> dict[str, Any]:
    expected = EPOCH_CONTRACT[extension_epoch]
    merged_scalar = pd.read_parquet(merge_root / "posterior_parameter_draws.parquet")
    merged_scalar = merged_scalar.sort_values(
        ["chain_id", "draw_id", "parameter"], kind="stable"
    ).reset_index(drop=True)
    if not merged_scalar.equals(raw_scalar):
        raise ValueError("Merged scalar draws are not byte-content-equivalent to raw chunks")
    with np.load(merge_root / "draws_spatial.npz", allow_pickle=False) as merged_file:
        merged_spatial = {key: merged_file[key].copy() for key in merged_file.files}
    if set(merged_spatial) != set(raw_spatial) or any(
        not np.array_equal(merged_spatial[key], raw_spatial[key]) for key in raw_spatial
    ):
        raise ValueError("Merged spatial draws differ from raw chunks")
    diagnostics = _diagnostics(
        raw_scalar,
        raw_spatial,
        counties,
        labels,
        prepared["parameter_schema"],
    )
    _validate_recorded_csv(
        merge_root / "spatial_diagnostics.csv",
        diagnostics,
        "Recorded diagnostics",
    )
    county_expected = _county_summary(
        raw_scalar, raw_spatial, diagnostics, counties, labels
    )
    _validate_recorded_csv(
        merge_root / "county_effect_summary.csv",
        county_expected,
        "County-effect summary",
        dtype={"county_fips": str},
    )
    acceptance_expected = _acceptance_summary(statuses, terminal_checkpoints)
    _validate_recorded_csv(
        merge_root / "acceptance_summary.csv",
        acceptance_expected,
        "Acceptance summary",
    )
    _validate_recorded_json(
        merge_root / "constraint_summary.json",
        _constraint_summary(extension_epoch),
        "Constraint summary",
    )
    threshold = _threshold_summary(diagnostics)
    _validate_recorded_json(
        merge_root / "spatial_diagnostics_summary.json",
        _diagnostics_summary(diagnostics, extension_epoch),
        "Diagnostics summary",
    )
    if pre_gate.get("threshold_summary") != threshold:
        raise ValueError("Pre-gate threshold summary differs from independent recomputation")
    if len(counties) != 3_142 or len(prepared["parameter_schema"]) != 71:
        raise ValueError("Production verifier requires 3,142 counties and 71 parameters")
    if len(diagnostics) != 9_483 or not diagnostics["arviz_version"].eq("1.2.0").all():
        raise ValueError("Production verifier requires exactly 9,483 ArviZ 1.2.0 diagnostics")
    primary = pd.read_csv(
        root / "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv",
        float_precision="round_trip",
    )
    comparison = _comparison_bytes(primary, raw_scalar)
    candidate_path = merge_root / "primary_vs_spatial.candidate.csv"
    if candidate_path.read_bytes() != comparison:
        raise ValueError("Candidate comparison differs byte-for-byte from recomputation")
    if pre_gate.get("candidate_sha256") != hashlib.sha256(comparison).hexdigest():
        raise ValueError("Candidate comparison manifest hash mismatch")
    if (
        pre_gate.get("iterations_per_chain") != expected["iterations"]
        or pre_gate.get("draws_per_chain") != expected["draws"]
        or pre_gate.get("chunks_per_chain") != expected["chunks"]
    ):
        raise ValueError("Merged semantic epoch cardinality mismatch")
    return {
        "diagnostics": diagnostics,
        "threshold": threshold,
        "comparison": comparison,
        "candidate_sha256": hashlib.sha256(comparison).hexdigest(),
    }


def _verify_benchmark(run_root: Path, prepared: Mapping[str, Any]) -> dict[str, Any]:
    path = run_root / "benchmark/benchmark_report.json"
    report_hash = _sidecar(path)
    report = json.loads(path.read_text(encoding="utf-8"))
    required_fields = {
        "schema_id",
        "run_id",
        "preparation_identity",
        "target_fingerprint",
        "launch_envelope_sha256",
        "final_source_manifest_sha256",
        "builder",
        "array_index",
        "iterations",
        "elapsed_seconds",
        "iterations_per_second",
        "projection_overhead_factor",
        "projected_hours",
        "projected_hours_limit_inclusive",
        "peak_rss_gib",
        "peak_rss_gib_limit_inclusive",
        "paired_chunk_draws",
        "paired_chunk_scalar_rows",
        "paired_chunk_bytes",
        "paired_chunk_elapsed_seconds",
        "paired_chunk_mib_per_second",
        "paired_chunk_record_sha256",
        "paired_chunk_builder",
        "paired_chunk_scientific_data",
        "passed",
        "scientific_draws_published",
        "submission_authorized",
    }
    if not isinstance(report, Mapping) or set(report) != required_fields:
        raise ValueError("Benchmark evidence schema mismatch")
    targets = {row["target_fingerprint"] for row in prepared["chain_mapping"]}
    if (
        report.get("schema_id") != "sr_v2_spatial_benchmark/v1"
        or report.get("run_id") != RUN_ID
        or report.get("preparation_identity") != prepared["preparation_identity"]
        or report.get("target_fingerprint") not in targets
        or report.get("launch_envelope_sha256") != prepared["launch_envelope_sha256"]
        or report.get("final_source_manifest_sha256")
        != prepared["final_source_manifest_sha256"]
        or report.get("builder") != "exact_prepared_public_chain"
        or report.get("iterations") != 2_000
        or report.get("passed") is not True
        or report.get("scientific_draws_published") is not False
        or report.get("projected_hours") > 65.0
        or report.get("peak_rss_gib") > 56.0
        or report.get("paired_chunk_draws") != 250
        or report.get("paired_chunk_scalar_rows") != 17_750
        or type(report.get("paired_chunk_bytes")) is not int
        or report.get("paired_chunk_bytes") <= 0
        or report.get("paired_chunk_builder") != "actual_commit_spatial_draw_chunk"
        or report.get("paired_chunk_scientific_data") is not False
        or len(_require_hash(report.get("paired_chunk_record_sha256"), "paired chunk record")) != 64
        or not math.isclose(
            float(report.get("iterations_per_second")),
            2_000 / float(report.get("elapsed_seconds")),
            rel_tol=1e-12,
            abs_tol=0.0,
        )
        or float(report.get("paired_chunk_elapsed_seconds")) <= 0.0
        or float(report.get("paired_chunk_mib_per_second")) <= 0.0
        or not math.isclose(
            float(report.get("paired_chunk_mib_per_second")),
            int(report.get("paired_chunk_bytes"))
            / float(report.get("paired_chunk_elapsed_seconds"))
            / 1024**2,
            rel_tol=1e-12,
            abs_tol=0.0,
        )
        or not math.isclose(
            float(report.get("projected_hours")),
            float(report.get("elapsed_seconds")) / 2_000 * 180_000 * 1.2 / 3_600,
            rel_tol=1e-12,
            abs_tol=0.0,
        )
    ):
        raise ValueError("Benchmark evidence/identity/limits mismatch")
    return {"sha256": report_hash, "report": report}


def _load_pre_gate(run_root: Path, epoch: int) -> tuple[dict[str, Any], Path]:
    merge_root = run_root / f"epochs/epoch_{epoch}/merge"
    path = merge_root / "pre_gate_manifest.json"
    _sidecar(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping) or set(manifest) != PRE_GATE_EXACT_FIELDS:
        raise ValueError("Pre-gate exact schema mismatch")
    _inventory(
        merge_root,
        manifest.get("artifact_sha256"),
        exact_files=True,
        allowed_files=(
            "pre_gate_manifest.json",
            "pre_gate_manifest.json.sha256",
        ),
    )
    if (
        manifest.get("schema_id") != "sr_v2_spatial_pre_gate_manifest/v1"
        or manifest.get("run_id") != RUN_ID
        or manifest.get("model_id") != MODEL_ID
        or manifest.get("extension_epoch") != epoch
        or manifest.get("submission_authorized") is not False
    ):
        raise ValueError("Pre-gate extension epoch mismatch")
    return manifest, merge_root


def _verification_artifact_snapshot(
    run_root: Path, extension_epoch: int
) -> dict[str, str]:
    excluded = {
        "spatial_sensitivity_gate.json",
        "primary_vs_spatial.csv",
        f"epochs/epoch_{extension_epoch}/verification/"
        "independent_spatial_sensitivity_verification.json",
        f"epochs/epoch_{extension_epoch}/verification/"
        "independent_spatial_sensitivity_verification.json.sha256",
        f"epochs/epoch_{extension_epoch}/release/"
        "spatial_sensitivity_release_manifest.json",
        f"epochs/epoch_{extension_epoch}/release/"
        "spatial_sensitivity_release_manifest.json.sha256",
        f"epochs/epoch_{extension_epoch}/gate/gate_decision.json",
        f"epochs/epoch_{extension_epoch}/gate/gate_decision.json.sha256",
    }
    snapshot: dict[str, str] = {}
    for path in sorted(run_root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Verification artifact snapshot rejects symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(run_root).as_posix()
        if relative in excluded:
            continue
        if any(part.startswith(".") for part in Path(relative).parts):
            raise ValueError("Verification artifact snapshot rejects temporary/lock files")
        snapshot[relative] = _sha(path)
    if not snapshot:
        raise ValueError("Verification artifact snapshot cannot be empty")
    return dict(sorted(snapshot.items()))


def _validate_verification_snapshot(
    run_root: Path,
    extension_epoch: int,
    verification: Mapping[str, Any],
) -> dict[str, str]:
    snapshot = verification.get("artifact_snapshot")
    if not isinstance(snapshot, Mapping) or not snapshot:
        raise ValueError("Independent verification artifact snapshot is missing")
    normalized: dict[str, str] = {}
    for relative, digest in snapshot.items():
        if not isinstance(relative, str) or not relative:
            raise ValueError("Independent verification snapshot path is malformed")
        normalized[relative] = _require_hash(digest, f"snapshot {relative}")
    if (
        dict(snapshot) != dict(sorted(normalized.items()))
        or verification.get("artifact_snapshot_sha256") != _canonical_sha(normalized)
    ):
        raise ValueError("Independent verification artifact snapshot/hash mismatch")
    current = _verification_artifact_snapshot(run_root, extension_epoch)
    if current != normalized:
        raise ValueError("Artifacts changed after independent verification")
    return normalized


def _validate_passed_verification(
    verification: object,
    *,
    extension_epoch: int,
    prepared: Mapping[str, Any],
    benchmark_hash: str,
    pre_gate_hash: str,
) -> dict[str, Any]:
    if not isinstance(verification, dict) or set(verification) != VERIFICATION_EXACT_FIELDS:
        raise ValueError("Independent verification exact schema mismatch")
    expected_groups = {
        "source_checks": {
            "passed", "prepared_manifest_sha256", "input_manifest_sha256",
            "launch_envelope_sha256", "final_source_manifest_sha256",
        },
        "graph_checks": {
            "passed", "nodes", "components", "all_component_scales_recomputed",
            "largest_component_recomputed",
        },
        "chain_checks": {
            "passed", "chains", "iterations_per_chain", "draws_per_chain",
            "chunks_per_chain", "historical_latent_y_stored",
            "independent_historical_y_reconstruction_possible", "claim_boundary",
            "retained_assertion_ledger_sha256",
            "prepared_checkpoint_targets_recomputed",
            "terminal_checkpoint_targets_recomputed",
        },
        "diagnostic_checks": {
            "passed", "rows", "arviz_version", "thresholds_inclusive",
            "convergence_passed",
        },
        "comparison_checks": {"passed", "rows", "candidate_sha256", "byte_identical"},
        "benchmark_checks": {"passed", "report_sha256", "iterations", "paired_chunk_draws"},
        "protected_tree_checks": {
            "passed", "raw_source_hashes_reverified", "manifest_sha256", "files",
        },
    }
    for group, fields in expected_groups.items():
        value = verification.get(group)
        if not isinstance(value, Mapping) or set(value) != fields or value.get("passed") is not True:
            raise ValueError(f"Independent verification group failed/schema mismatch: {group}")
    snapshot = verification.get("artifact_snapshot")
    if not isinstance(snapshot, Mapping) or not snapshot:
        raise ValueError("Independent verification artifact snapshot is missing")
    normalized_snapshot = {
        str(relative): _require_hash(digest, f"snapshot {relative}")
        for relative, digest in snapshot.items()
        if isinstance(relative, str) and relative
    }
    if (
        len(normalized_snapshot) != len(snapshot)
        or dict(snapshot) != dict(sorted(normalized_snapshot.items()))
        or verification.get("artifact_snapshot_sha256")
        != _canonical_sha(normalized_snapshot)
    ):
        raise ValueError("Independent verification artifact snapshot/hash mismatch")
    expected = EPOCH_CONTRACT[extension_epoch]
    if (
        verification.get("schema_id")
        != "sr_v2_independent_spatial_sensitivity_verification/v1"
        or verification.get("run_id") != RUN_ID
        or verification.get("model_id") != MODEL_ID
        or verification.get("extension_epoch") != extension_epoch
        or verification.get("preparation_identity") != prepared["preparation_identity"]
        or verification.get("launch_envelope_sha256") != prepared["launch_envelope_sha256"]
        or verification.get("final_source_manifest_sha256")
        != prepared["final_source_manifest_sha256"]
        or verification.get("benchmark_report_sha256") != benchmark_hash
        or verification.get("pre_gate_manifest_sha256") != pre_gate_hash
        or verification.get("passed") is not True
        or verification.get("submission_authorized") is not False
        or verification["source_checks"]["input_manifest_sha256"]
        != prepared["input_manifest_sha256"]
        or verification["source_checks"]["launch_envelope_sha256"]
        != prepared["launch_envelope_sha256"]
        or verification["source_checks"]["final_source_manifest_sha256"]
        != prepared["final_source_manifest_sha256"]
        or verification["graph_checks"]
        != {
            "passed": True, "nodes": 3_142, "components": 18,
            "all_component_scales_recomputed": 18,
            "largest_component_recomputed": 3_099,
        }
        or verification["chain_checks"]["chains"] != 4
        or verification["chain_checks"]["iterations_per_chain"] != expected["iterations"]
        or verification["chain_checks"]["draws_per_chain"] != expected["draws"]
        or verification["chain_checks"]["chunks_per_chain"] != expected["chunks"]
        or verification["chain_checks"]["prepared_checkpoint_targets_recomputed"] != 4
        or verification["chain_checks"]["terminal_checkpoint_targets_recomputed"] != 4
        or verification["chain_checks"]["historical_latent_y_stored"] is not False
        or verification["chain_checks"]["independent_historical_y_reconstruction_possible"] is not False
        or verification["diagnostic_checks"]["rows"] != 9_483
        or verification["diagnostic_checks"]["arviz_version"] != "1.2.0"
        or verification["diagnostic_checks"]["thresholds_inclusive"] is not True
        or verification["comparison_checks"]["rows"] != list(COMPARISON_ROWS)
        or verification["comparison_checks"]["byte_identical"] is not True
        or verification["benchmark_checks"]
        != {"passed": True, "report_sha256": benchmark_hash, "iterations": 2_000, "paired_chunk_draws": 250}
        or verification["protected_tree_checks"]["raw_source_hashes_reverified"] is not True
        or verification["protected_tree_checks"]["manifest_sha256"]
        != prepared["protected_tree_manifest_sha256"]
    ):
        raise ValueError("Independent verification identity/cardinality contract failed")
    return verification


def independent_verify(
    *,
    extension_epoch: int,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    output_base_override: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    run_root = _run_root(root, output_base_override)
    _set_hold(
        root,
        reason="independent_verification_not_passed",
        stage="independent_verification",
        extension_epoch=extension_epoch,
        output_base_override=output_base_override,
    )
    destination = run_root / f"epochs/epoch_{extension_epoch}/verification"
    try:
        if isinstance(extension_epoch, bool) or extension_epoch not in range(4):
            raise ValueError("Verifier extension epoch must be exactly 0..3")
        config = _load_config(config_path)
        prepared_manifest, prepared_root = _verify_prepared(
            root, run_root, config, config_path
        )
        counties, adjacency, labels, components, scales = _graph_from_prepared(
            prepared_root, config
        )
        frame = pd.read_parquet(prepared_root / str(prepared_manifest["model_frame"]))
        benchmark = _verify_benchmark(run_root, prepared_manifest)
        raw_scalar, raw_spatial, statuses, ledger_hashes, terminal_checkpoints = _verify_chains(
            run_root,
            prepared_manifest,
            extension_epoch,
            frame,
            counties,
            adjacency,
            labels,
            components,
            scales,
        )
        pre_gate, merge_root = _load_pre_gate(run_root, extension_epoch)
        expected = EPOCH_CONTRACT[extension_epoch]
        if (
            pre_gate.get("iterations_per_chain") != expected["iterations"]
            or pre_gate.get("draws_per_chain") != expected["draws"]
            or pre_gate.get("chunks_per_chain") != expected["chunks"]
            or pre_gate.get("chains") != 4
            or pre_gate.get("preparation_identity")
            != prepared_manifest["preparation_identity"]
            or pre_gate.get("benchmark_report_sha256") != benchmark["sha256"]
            or pre_gate.get("retained_assertion_ledger_sha256") != ledger_hashes
        ):
            raise ValueError("Pre-gate identity/cardinality binding mismatch")
        semantics = _verify_merged_semantics(
            root=root,
            prepared=prepared_manifest,
            extension_epoch=extension_epoch,
            raw_scalar=raw_scalar,
            raw_spatial=raw_spatial,
            statuses=statuses,
            terminal_checkpoints=terminal_checkpoints,
            counties=counties,
            labels=labels,
            pre_gate=pre_gate,
            merge_root=merge_root,
        )
        diagnostics = semantics["diagnostics"]
        threshold = semantics["threshold"]
        comparison = semantics["comparison"]
        protected_manifest_path = prepared_root / str(
            prepared_manifest["protected_tree_manifest"]
        )
        protected_manifest = json.loads(
            protected_manifest_path.read_text(encoding="utf-8")
        )
        artifact_snapshot = _verification_artifact_snapshot(
            run_root, extension_epoch
        )
        result = {
            "schema_id": "sr_v2_independent_spatial_sensitivity_verification/v1",
            "run_id": RUN_ID,
            "model_id": MODEL_ID,
            "extension_epoch": extension_epoch,
            "preparation_identity": prepared_manifest["preparation_identity"],
            "launch_envelope_sha256": prepared_manifest["launch_envelope_sha256"],
            "final_source_manifest_sha256": prepared_manifest["final_source_manifest_sha256"],
            "benchmark_report_sha256": benchmark["sha256"],
            "pre_gate_manifest_sha256": _sha(merge_root / "pre_gate_manifest.json"),
            "passed": True,
            "source_checks": {
                "passed": True,
                "prepared_manifest_sha256": _sha(
                    prepared_root / "prepared_run_manifest.json"
                ),
                "input_manifest_sha256": prepared_manifest["input_manifest_sha256"],
                "launch_envelope_sha256": prepared_manifest["launch_envelope_sha256"],
                "final_source_manifest_sha256": prepared_manifest["final_source_manifest_sha256"],
            },
            "graph_checks": {
                "passed": True,
                "nodes": len(counties),
                "components": len(components),
                "all_component_scales_recomputed": len(scales),
                "largest_component_recomputed": max(len(part) for part in components),
            },
            "chain_checks": {
                "passed": True,
                "chains": len(statuses),
                "iterations_per_chain": expected["iterations"],
                "draws_per_chain": expected["draws"],
                "chunks_per_chain": expected["chunks"],
                "prepared_checkpoint_targets_recomputed": 4,
                "terminal_checkpoint_targets_recomputed": len(terminal_checkpoints),
                "historical_latent_y_stored": False,
                "independent_historical_y_reconstruction_possible": False,
                "claim_boundary": (
                    "The exact schedule and in-loop constraint assertions are verified; "
                    "historical latent y cannot be independently reconstructed."
                ),
                "retained_assertion_ledger_sha256": ledger_hashes,
            },
            "diagnostic_checks": {
                "passed": True,
                "rows": len(diagnostics),
                "arviz_version": "1.2.0",
                "thresholds_inclusive": True,
                "convergence_passed": threshold["passed"],
            },
            "comparison_checks": {
                "passed": True,
                "rows": list(COMPARISON_ROWS),
                "candidate_sha256": hashlib.sha256(comparison).hexdigest(),
                "byte_identical": True,
            },
            "benchmark_checks": {
                "passed": True,
                "report_sha256": benchmark["sha256"],
                "iterations": 2_000,
                "paired_chunk_draws": 250,
            },
            "protected_tree_checks": {
                "passed": True,
                "raw_source_hashes_reverified": True,
                "manifest_sha256": prepared_manifest[
                    "protected_tree_manifest_sha256"
                ],
                "files": len(protected_manifest["files"]),
            },
            "artifact_snapshot": artifact_snapshot,
            "artifact_snapshot_sha256": _canonical_sha(artifact_snapshot),
            "submission_authorized": False,
        }
        if set(result) != VERIFICATION_EXACT_FIELDS:
            raise AssertionError("Independent verification implementation/schema drift")
        path = _publish_immutable_json(
            destination, "independent_spatial_sensitivity_verification.json", result
        )
        result["verification_sha256"] = _sha(path)
        return result
    except BaseException as error:
        _set_hold(
            root,
            reason=f"independent_verification_failed:{type(error).__name__}",
            stage="independent_verification",
            extension_epoch=extension_epoch,
            output_base_override=output_base_override,
        )
        if not os.path.lexists(destination):
            failure = {
                "schema_id": "sr_v2_independent_spatial_sensitivity_verification/v1",
                "run_id": RUN_ID,
                "extension_epoch": extension_epoch,
                "passed": False,
                "failure_class": type(error).__name__,
                "submission_authorized": False,
            }
            _publish_immutable_json(
                destination,
                "independent_spatial_sensitivity_verification.json",
                failure,
            )
        raise


def _release_artifact_inventory(run_root: Path, extension_epoch: int) -> dict[str, str]:
    excluded = {
        "spatial_sensitivity_gate.json",
        "primary_vs_spatial.csv",
        f"epochs/epoch_{extension_epoch}/release/spatial_sensitivity_release_manifest.json",
        f"epochs/epoch_{extension_epoch}/release/spatial_sensitivity_release_manifest.json.sha256",
        f"epochs/epoch_{extension_epoch}/gate/gate_decision.json",
        f"epochs/epoch_{extension_epoch}/gate/gate_decision.json.sha256",
    }
    artifacts: dict[str, str] = {}
    for path in sorted(run_root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Release coverage rejects symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(run_root).as_posix()
        if relative in excluded:
            continue
        if any(part.startswith(".") for part in Path(relative).parts):
            raise ValueError("Release coverage rejects temporary/lock files")
        artifacts[relative] = _sha(path)
    if not artifacts:
        raise ValueError("Release coverage cannot be empty")
    return artifacts


def _validate_release(
    release: object,
    *,
    run_root: Path,
    extension_epoch: int,
    prepared: Mapping[str, Any],
    benchmark_hash: str,
    pre_gate_hash: str,
    verification_hash: str,
    verification_snapshot: Mapping[str, str],
    verification_snapshot_hash: str,
    candidate_relative: str,
    candidate_hash: str,
) -> dict[str, Any]:
    if not isinstance(release, dict) or set(release) != RELEASE_EXACT_FIELDS:
        raise ValueError("Release manifest exact schema mismatch")
    artifacts = release.get("artifacts")
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise ValueError("Release artifact inventory is missing")
    actual_inventory = _release_artifact_inventory(run_root, extension_epoch)
    if dict(artifacts) != actual_inventory:
        raise ValueError("Release artifact coverage is sparse, extra, or stale")
    _inventory(run_root, artifacts)
    current_snapshot = _verification_artifact_snapshot(run_root, extension_epoch)
    if dict(verification_snapshot) != current_snapshot:
        raise ValueError("Release does not match the independent-verifier artifact snapshot")
    planned = {
        "primary_vs_spatial.csv": {
            "source": candidate_relative,
            "sha256": candidate_hash,
        }
    }
    if (
        release.get("schema_id") != "sr_v2_spatial_sensitivity_release_manifest/v1"
        or release.get("run_id") != RUN_ID
        or release.get("model_id") != MODEL_ID
        or release.get("extension_epoch") != extension_epoch
        or release.get("preparation_identity") != prepared["preparation_identity"]
        or release.get("launch_envelope_sha256") != prepared["launch_envelope_sha256"]
        or release.get("final_source_manifest_sha256")
        != prepared["final_source_manifest_sha256"]
        or release.get("benchmark_report_sha256") != benchmark_hash
        or release.get("pre_gate_manifest_sha256") != pre_gate_hash
        or release.get("independent_verification_sha256") != verification_hash
        or type(release.get("verification_convergence_passed")) is not bool
        or release.get("verification_artifact_snapshot")
        != dict(verification_snapshot)
        or release.get("verification_artifact_snapshot_sha256")
        != verification_snapshot_hash
        or verification_snapshot_hash != _canonical_sha(dict(verification_snapshot))
        or release.get("artifact_inventory_sha256") != _canonical_sha(dict(artifacts))
        or release.get("planned_outputs") != planned
        or release.get("excludes")
        != ["primary_vs_spatial.csv", "spatial_sensitivity_gate.json"]
        or release.get("submission_authorized") is not False
    ):
        raise ValueError("Release manifest identity/planned-output contract mismatch")
    return release


def write_release_manifest(
    *,
    extension_epoch: int,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    output_base_override: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    run_root = _run_root(root, output_base_override)
    _set_hold(
        root,
        reason="release_manifest_not_verified",
        stage="release_manifest",
        extension_epoch=extension_epoch,
        output_base_override=output_base_override,
    )
    config = _load_config(config_path)
    prepared, _prepared_root = _verify_prepared(root, run_root, config, config_path)
    benchmark = _verify_benchmark(run_root, prepared)
    pre_gate, merge_root = _load_pre_gate(run_root, extension_epoch)
    pre_gate_path = merge_root / "pre_gate_manifest.json"
    pre_gate_hash = _sha(pre_gate_path)
    verification_path = (
        run_root
        / f"epochs/epoch_{extension_epoch}/verification/independent_spatial_sensitivity_verification.json"
    )
    verification_hash = _sidecar(verification_path)
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    verification = _validate_passed_verification(
        verification,
        extension_epoch=extension_epoch,
        prepared=prepared,
        benchmark_hash=benchmark["sha256"],
        pre_gate_hash=pre_gate_hash,
    )
    verification_snapshot = _validate_verification_snapshot(
        run_root, extension_epoch, verification
    )
    candidate = merge_root / "primary_vs_spatial.candidate.csv"
    candidate_hash = _sha(candidate)
    if candidate_hash != pre_gate.get("candidate_sha256"):
        raise ValueError("Release candidate hash differs from pre-gate manifest")
    final_path = run_root / "primary_vs_spatial.csv"
    if os.path.lexists(final_path):
        raise FileExistsError("Final comparison must not pre-exist release/gate")
    artifacts = _release_artifact_inventory(run_root, extension_epoch)
    release = {
        "schema_id": "sr_v2_spatial_sensitivity_release_manifest/v1",
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "extension_epoch": extension_epoch,
        "preparation_identity": prepared["preparation_identity"],
        "launch_envelope_sha256": prepared["launch_envelope_sha256"],
        "final_source_manifest_sha256": prepared["final_source_manifest_sha256"],
        "benchmark_report_sha256": benchmark["sha256"],
        "pre_gate_manifest_sha256": pre_gate_hash,
        "independent_verification_sha256": verification_hash,
        "verification_convergence_passed": verification["diagnostic_checks"][
            "convergence_passed"
        ],
        "verification_artifact_snapshot": verification_snapshot,
        "verification_artifact_snapshot_sha256": verification[
            "artifact_snapshot_sha256"
        ],
        "artifacts": dict(sorted(artifacts.items())),
        "artifact_inventory_sha256": _canonical_sha(dict(sorted(artifacts.items()))),
        "planned_outputs": {
            "primary_vs_spatial.csv": {
                "source": candidate.relative_to(run_root).as_posix(),
                "sha256": candidate_hash,
            }
        },
        "excludes": ["primary_vs_spatial.csv", "spatial_sensitivity_gate.json"],
        "submission_authorized": False,
    }
    if set(release) != RELEASE_EXACT_FIELDS:
        raise AssertionError("Release implementation/schema drift")
    _validate_release(
        release,
        run_root=run_root,
        extension_epoch=extension_epoch,
        prepared=prepared,
        benchmark_hash=benchmark["sha256"],
        pre_gate_hash=pre_gate_hash,
        verification_hash=verification_hash,
        verification_snapshot=verification_snapshot,
        verification_snapshot_hash=verification["artifact_snapshot_sha256"],
        candidate_relative=candidate.relative_to(run_root).as_posix(),
        candidate_hash=candidate_hash,
    )
    destination = run_root / f"epochs/epoch_{extension_epoch}/release"
    _publish_immutable_json(
        destination, "spatial_sensitivity_release_manifest.json", release
    )
    return release


def gate(
    *,
    extension_epoch: int,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    output_base_override: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    run_root = _run_root(root, output_base_override)
    _set_hold(
        root,
        reason="gate_checks_running",
        stage="gate",
        extension_epoch=extension_epoch,
        output_base_override=output_base_override,
    )
    try:
        config = _load_config(config_path)
        prepared, prepared_root = _verify_prepared(root, run_root, config, config_path)
        counties, adjacency, labels, components, scales = _graph_from_prepared(
            prepared_root, config
        )
        frame = pd.read_parquet(prepared_root / str(prepared["model_frame"]))
        benchmark = _verify_benchmark(run_root, prepared)
        pre_gate, merge_root = _load_pre_gate(run_root, extension_epoch)
        pre_gate_path = merge_root / "pre_gate_manifest.json"
        pre_gate_hash = _sha(pre_gate_path)
        raw_scalar, raw_spatial, statuses, ledger_hashes, terminal_checkpoints = _verify_chains(
            run_root,
            prepared,
            extension_epoch,
            frame,
            counties,
            adjacency,
            labels,
            components,
            scales,
        )
        verification_path = (
            run_root
            / f"epochs/epoch_{extension_epoch}/verification/independent_spatial_sensitivity_verification.json"
        )
        verification_hash = _sidecar(verification_path)
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        verification = _validate_passed_verification(
            verification,
            extension_epoch=extension_epoch,
            prepared=prepared,
            benchmark_hash=benchmark["sha256"],
            pre_gate_hash=pre_gate_hash,
        )
        verification_snapshot = _validate_verification_snapshot(
            run_root, extension_epoch, verification
        )
        if verification["source_checks"]["prepared_manifest_sha256"] != _sha(
            prepared_root / "prepared_run_manifest.json"
        ):
            raise ValueError("Verifier prepared-manifest hash binding changed")
        release_path = (
            run_root
            / f"epochs/epoch_{extension_epoch}/release/spatial_sensitivity_release_manifest.json"
        )
        release_hash = _sidecar(release_path)
        release = json.loads(release_path.read_text(encoding="utf-8"))
        candidate = merge_root / "primary_vs_spatial.candidate.csv"
        candidate_hash = _sha(candidate)
        release = _validate_release(
            release,
            run_root=run_root,
            extension_epoch=extension_epoch,
            prepared=prepared,
            benchmark_hash=benchmark["sha256"],
            pre_gate_hash=pre_gate_hash,
            verification_hash=verification_hash,
            verification_snapshot=verification_snapshot,
            verification_snapshot_hash=verification["artifact_snapshot_sha256"],
            candidate_relative=candidate.relative_to(run_root).as_posix(),
            candidate_hash=candidate_hash,
        )
        expected = EPOCH_CONTRACT[extension_epoch]
        if (
            pre_gate.get("builder") != "verified_raw_chunk_merge"
            or pre_gate.get("bounded_test_mode") is not False
            or pre_gate.get("production_shape") is not True
            or pre_gate.get("chains") != 4
            or pre_gate.get("iterations_per_chain") != expected["iterations"]
            or pre_gate.get("draws_per_chain") != expected["draws"]
            or pre_gate.get("chunks_per_chain") != expected["chunks"]
            or pre_gate.get("parameter_schema_rows") != 71
            or pre_gate.get("county_rows") != 3_142
            or pre_gate.get("diagnostic_rows") != 9_483
            or pre_gate.get("arviz_version") != "1.2.0"
            or pre_gate.get("count_constraint_failures") != 0
            or pre_gate.get("spatial_constraint_failures") != 0
            or pre_gate.get("comparison_rows") != list(COMPARISON_ROWS)
            or len(counties) != 3_142
            or max(len(part) for part in components) != 3_099
            or len(scales) != 18
            or pre_gate.get("retained_assertion_ledger_sha256") != ledger_hashes
            or pre_gate.get("chain_fingerprints")
            != sorted(str(status["chain_fingerprint"]) for status in statuses)
        ):
            raise ValueError("Final production gate contract failed")
        semantics = _verify_merged_semantics(
            root=root,
            prepared=prepared,
            extension_epoch=extension_epoch,
            raw_scalar=raw_scalar,
            raw_spatial=raw_spatial,
            statuses=statuses,
            terminal_checkpoints=terminal_checkpoints,
            counties=counties,
            labels=labels,
            pre_gate=pre_gate,
            merge_root=merge_root,
        )
        recomputed_candidate = semantics["comparison"]
        if (
            candidate.read_bytes() != recomputed_candidate
            or candidate_hash != pre_gate.get("candidate_sha256")
            or verification["comparison_checks"]["candidate_sha256"] != candidate_hash
        ):
            raise ValueError("Release/verifier candidate mapping mismatch")
        convergence_passed = pre_gate.get("threshold_summary", {}).get("passed") is True
        if release["verification_convergence_passed"] is not convergence_passed or verification[
            "diagnostic_checks"
        ]["convergence_passed"] is not convergence_passed:
            raise ValueError("Convergence decision differs across evidence chain")
        _validate_verification_snapshot(run_root, extension_epoch, verification)
        gate_common = {
            "schema_id": "sr_v2_spatial_sensitivity_gate/v1",
            "run_id": RUN_ID,
            "model_id": MODEL_ID,
            "extension_epoch": extension_epoch,
            "preparation_identity": prepared["preparation_identity"],
            "benchmark_report_sha256": benchmark["sha256"],
            "pre_gate_manifest_sha256": pre_gate_hash,
            "release_manifest_sha256": release_hash,
            "independent_verification_sha256": verification_hash,
            "submission_authorized": False,
            "interpretation_boundary": (
                "Ecological model-based sensitivity only; no effect is a person-level "
                "or causal estimate."
            ),
        }
        if not convergence_passed:
            hold = {
                **gate_common,
                "status": "HOLD",
                "passed": False,
                "action": (
                    "reviewed_extension_required"
                    if extension_epoch < 3
                    else "hold_no_further_extension"
                ),
                "reason": "convergence_only",
                "extension_eligible": extension_epoch < 3,
                "final_comparison_sha256": None,
            }
            _commit_gate_decision(run_root, extension_epoch, hold)
            return hold
        final = run_root / "primary_vs_spatial.csv"
        if os.path.lexists(final):
            if not final.is_file() or final.is_symlink() or _sha(final) != candidate_hash:
                raise FileExistsError("Conflicting final comparison already exists")
        else:
            _atomic_bytes(final, candidate.read_bytes())
        if _sha(final) != candidate_hash or final.read_bytes() != candidate.read_bytes():
            raise ValueError("Final comparison is not byte-identical to candidate")
        passed = {
            **gate_common,
            "status": "PASS",
            "passed": True,
            "action": "freeze_spatial_sensitivity",
            "reason": "all_fail_closed_criteria_passed",
            "extension_eligible": False,
            "final_comparison_sha256": candidate_hash,
        }
        _commit_gate_decision(run_root, extension_epoch, passed)
        return passed
    except BaseException as error:
        _set_hold(
            root,
            reason=f"gate_failed:{type(error).__name__}",
            stage="gate",
            extension_epoch=extension_epoch,
            output_base_override=output_base_override,
        )
        raise


def main() -> None:
    # This compile-time path is written before argparse/config/mode handling.
    _set_hold(ROOT, reason="gate_cli_started", stage="gate")
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--independent-verify", action="store_true")
    modes.add_argument("--write-release-manifest", action="store_true")
    modes.add_argument("--gate", action="store_true")
    parser.add_argument("--extension-epoch", required=True, type=int)
    args = parser.parse_args()
    if args.independent_verify:
        independent_verify(extension_epoch=args.extension_epoch)
    elif args.write_release_manifest:
        write_release_manifest(extension_epoch=args.extension_epoch)
    else:
        gate(extension_epoch=args.extension_epoch)


if __name__ == "__main__":
    main()
