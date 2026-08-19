from __future__ import annotations

import csv
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml


RUN_ID = "sr-v2-spatial-sensitivity-20260818-v1"
MODEL_ID = "sr-v2-primary-nb2-bym2-v1"
OUTPUT_ROOT = "outputs/scientific_reports_v2/spatial_sensitivity"
PROTECTED_TREES = (
    "outputs/scientific_reports_v2/production_8chain",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics",
)
SPATIAL_FINAL_SOURCE_FILES = (
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
COMPARISON_SCALE = {
    **{row: "incidence_rate_ratio" for row in COMPARISON_ROWS[:6]},
    "z_pct_age65": "standardized_log_rate_coefficient",
    "z_pct_male": "standardized_log_rate_coefficient",
}
EXPECTED_SOURCE_AUTHORITIES = {
    "outputs/scientific_reports_v2/production_8chain/production_gate.json": "38be94b401138864cf6e4cb030f2bd53e9b8ad6ea24e080e0353824124784437",
    "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv": "2842efa4c95b018aed3626b58b33e42792c0348655225c3a89ec58b4109452e6",
    "outputs/scientific_reports_v2/production_8chain/posterior_parameter_draws.parquet": "0f3adc1a90bd411f3065e798867423d5bd2ae1cf0c61d99d7f5f53493b362064",
    "outputs/scientific_reports_v2/production_8chain/county_posterior_summary.csv": "f9eb36d8748da9a3c8f95c952a95de6d4845ecb963f329a2a61b9adb47ee056e",
    "data/processed/bayes_constrained/model_frame.parquet": "2f20555f4b690e1a495e2409dbb2f9bb128a6d3f7b0bb39f4017034aaf2a9e44",
    "config/scientific_reports_v2_robustness_registry.yaml": "072e039b78af11a0bb4d6532bb8fb09f70b81d825a38faa3cf89670ca7843814",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json": "5d3209d248add49cfd2a5a5379af3e831ec7f6136ed45654ca882cc399a190d1",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics/global_morans_i.csv": "a44ee5945c308f1455e799c0f22bed356ff118ff6a0de5da1d1f9315c3a836c8",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics/within_state_morans_i.csv": "6296899e8a789e219d245d109b55759dead7817f5ba93c75f0694f669231c995",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics/county_adjacency2024.txt": "912ca408163016864fe64aaf667b53ad03a19ce4acbc586d3ac508395bdac980",
}
EPOCH_CONTRACT = {
    0: {"iterations": 180_000, "draws": 4_500, "chunks": 18},
    1: {"iterations": 270_000, "draws": 7_500, "chunks": 30},
    2: {"iterations": 360_000, "draws": 10_500, "chunks": 42},
    3: {"iterations": 450_000, "draws": 13_500, "chunks": 54},
}
PREPARED_MANIFEST_EXACT_FIELDS = {
    "schema_id",
    "run_id",
    "model_id",
    "operational_config_sha256",
    "launch_envelope_sha256",
    "final_source_manifest_sha256",
    "launch_commit",
    "bundle_sha256",
    "joint_regression_evidence_sha256",
    "preparation_identity",
    "generated_utc",
    "status",
    "production_eligible",
    "builder_provenance",
    "input_manifest",
    "input_manifest_sha256",
    "source_authorities",
    "graph_contract",
    "graph_contract_sha256",
    "model_frame",
    "model_frame_sha256",
    "model_frame_semantic_sha256",
    "parameter_schema",
    "protected_tree_manifest",
    "protected_tree_manifest_sha256",
    "chain_mapping",
    "prepared_artifact_sha256",
    "interpretation_boundary",
    "submission_authorized",
}
INPUT_MANIFEST_EXACT_FIELDS = {
    "schema_id", "run_id", "operational_config_sha256", "source_authorities",
    "launch_envelope_sha256", "final_source_manifest_sha256", "launch_commit",
    "bundle_sha256", "joint_regression_evidence_sha256",
    "source_model_frame_sha256", "prepared_model_frame_sha256",
    "model_frame_semantic_sha256", "graph_contract_sha256",
    "graph_artifact_sha256",
}


@dataclass(frozen=True)
class SpatialAssignment:
    array_index: int
    chain_id: int
    chain_seed: int
    allocation_initialization_seed: int
    spatial_initialization_seed: int


@dataclass(frozen=True)
class SpatialExecutionSpec:
    path: Path
    schema_id: str
    run_id: str
    model_id: str
    source_authorities: dict[str, str]
    chain_map: tuple[SpatialAssignment, ...]
    epoch_contract: dict[int, dict[str, int]]
    raw: dict[str, Any]

    def assignment(self, array_index: int) -> SpatialAssignment:
        matches = [row for row in self.chain_map if row.array_index == array_index]
        if len(matches) != 1:
            raise ValueError(f"Array index must be exactly one of 1..4: {array_index}")
        return matches[0]


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_spatial_execution_spec(path: str | Path) -> SpatialExecutionSpec:
    config_path = Path(path).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Spatial execution config must be a mapping")
    expected_top = {
        "schema_id",
        "run_id",
        "model_id",
        "status",
        "source_authorities",
        "final_source_manifest",
        "launch_envelope",
        "canonical_serialization",
        "graph_certificate",
        "model",
        "seeds",
        "execution",
        "parameter_updates",
        "mala",
        "fingerprints",
        "comparison",
        "thresholds",
        "resources",
        "output_schemas",
        "release",
    }
    if set(raw) != expected_top:
        raise ValueError("Spatial execution config top-level keys changed")
    if (
        raw.get("schema_id") != "sr_v2_spatial_sensitivity_execution/v1"
        or raw.get("run_id") != RUN_ID
        or raw.get("model_id") != MODEL_ID
        or raw.get("status") != "triggered_frozen_execution_contract"
    ):
        raise ValueError("Spatial schema/run/model/status contract changed")
    sources = _sha256_mapping(raw.get("source_authorities"), label="source authorities")
    if sources != EXPECTED_SOURCE_AUTHORITIES:
        raise ValueError("Spatial frozen source authorities changed")
    final_source = raw.get("final_source_manifest")
    if final_source != {
        "schema_id": "sr_v2_robustness_final_source_manifest/v1",
        "required_status": "reviewed_final",
        "source_hash_mode": "raw_bytes",
        "required_sources": list(SPATIAL_FINAL_SOURCE_FILES),
    }:
        raise ValueError("Spatial final-source manifest contract changed")
    if raw.get("launch_envelope") != {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "required_status": "reviewed_final",
        "requires_clean_worktree": True,
    }:
        raise ValueError("Spatial launch-envelope contract changed")
    seeds = raw.get("seeds")
    if seeds != {
        "chain": [74291, 74292, 74293, 74294],
        "allocation_initialization": [74251, 74252, 74253, 74254],
        "spatial_initialization": [74261, 74262, 74263, 74264],
    }:
        raise ValueError("Spatial chain or initialization seeds changed")
    chain_map = tuple(
        SpatialAssignment(index + 1, index + 1, seeds["chain"][index], seeds["allocation_initialization"][index], seeds["spatial_initialization"][index])
        for index in range(4)
    )
    execution = raw.get("execution", {})
    if (
        execution.get("chains") != 4
        or execution.get("initial_epoch")
        != {
            "extension_epoch": 0,
            "iterations_per_chain": 180000,
            "burn_in": 45000,
            "thin": 30,
            "retained_draws_per_chain": 4500,
        }
        or execution.get("valid_total_iterations_and_draws")
        != [[180000, 4500], [270000, 7500], [360000, 10500], [450000, 13500]]
        or execution.get("extension_epoch_range") != [0, 3]
        or execution.get("job_attempt_range_per_epoch") != [1, 3]
        or execution.get("checkpoint_exit_code") != 75
        or execution.get("draw_chunk_size") != 250
    ):
        raise ValueError("Spatial iteration/extension/attempt contract changed")
    comparison = raw.get("comparison", {})
    if (
        comparison.get("rows") != list(COMPARISON_ROWS)
        or comparison.get("fields") != list(COMPARISON_FIELDS)
        or comparison.get("scale_by_row") != COMPARISON_SCALE
        or comparison.get("absolute_change") != "spatial_mean_minus_primary_mean"
        or comparison.get("relative_change")
        != "absolute_change_divided_by_abs_primary_mean_fail_if_zero_or_nonfinite"
        or comparison.get("interval_overlap")
        != "max_lower_less_than_or_equal_to_min_upper_closed_intervals"
    ):
        raise ValueError("Spatial comparison contract changed")
    graph = raw.get("graph_certificate", {})
    if (
        graph.get("nodes") != 3142
        or graph.get("undirected_edges") != 9233
        or graph.get("components") != 18
        or graph.get("nonisolated_nodes") != 3128
        or graph.get("county_order_sha256")
        != "250417302ddfc261014e7182e065ff0ebaef3a15437c8672fc05b9ab4a9c066b"
        or graph.get("edge_list_sha256")
        != "59412bc9722a119487977065892db16d6bb6931725821a0adb21886ec891df39"
    ):
        raise ValueError("Spatial graph certificate changed")
    return SpatialExecutionSpec(
        path=config_path,
        schema_id=str(raw["schema_id"]),
        run_id=str(raw["run_id"]),
        model_id=str(raw["model_id"]),
        source_authorities=sources,
        chain_map=chain_map,
        epoch_contract={key: dict(value) for key, value in EPOCH_CONTRACT.items()},
        raw=raw,
    )


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json(path: str | Path, payload: Mapping[str, object]) -> None:
    serialized = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    _atomic_bytes(Path(path), serialized)


def spatial_run_root(
    root: str | Path, output_base_override: str | Path | None = None
) -> Path:
    base = (
        Path(output_base_override).resolve()
        if output_base_override is not None
        else safe_relative_path(Path(root).resolve(), OUTPUT_ROOT)
    )
    return base / RUN_ID


def set_canonical_hold(
    root: str | Path,
    *,
    reason: str,
    stage: str,
    extension_epoch: int | None = None,
    output_base_override: str | Path | None = None,
) -> dict[str, object]:
    run_root = spatial_run_root(root, output_base_override)
    payload: dict[str, object] = {
        "schema_id": "sr_v2_spatial_sensitivity_gate/v1",
        "run_id": RUN_ID,
        "status": "HOLD",
        "passed": False,
        "stage": str(stage),
        "reason": str(reason),
        "submission_authorized": False,
        "interpretation_boundary": (
            "Ecological model-based sensitivity only; no effect is a person-level or causal estimate."
        ),
    }
    if extension_epoch is not None:
        payload["extension_epoch"] = int(extension_epoch)
    atomic_json(run_root / "spatial_sensitivity_gate.json", payload)
    return payload


def _dense_component_scale(precision: np.ndarray) -> float:
    covariance = np.linalg.pinv(
        np.asarray(precision, dtype=np.float64), hermitian=True
    )
    diagonal = np.diag(covariance)
    if (
        diagonal.shape != (len(precision),)
        or not np.isfinite(diagonal).all()
        or np.any(diagonal <= 0.0)
    ):
        raise ValueError("Component pseudoinverse has invalid marginal variances")
    scale = float(np.exp(np.mean(np.log(diagonal), dtype=np.float64)))
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("Component scale is nonfinite or nonpositive")
    return scale


def recompute_component_scales(
    adjacency: Any,
    components: Sequence[np.ndarray],
    *,
    scale_solver: Any | None = None,
) -> tuple[float, ...]:
    """Independently recompute every non-singleton ICAR component scale.

    There is deliberately no size cutoff or frozen-value fast path: the
    3,099-node production component is passed through the same solver as the
    17-, 10-, and 2-node components.
    """

    solver = _dense_component_scale if scale_solver is None else scale_solver
    result: list[float] = []
    for component in components:
        indices = np.asarray(component)
        if (
            indices.ndim != 1
            or np.issubdtype(indices.dtype, np.bool_)
            or not np.issubdtype(indices.dtype, np.integer)
            or len(indices) == 0
        ):
            raise ValueError("Graph components must contain exact integer indices")
        if len(indices) == 1:
            result.append(0.0)
            continue
        block = adjacency[indices][:, indices].toarray().astype(np.float64)
        precision = np.diag(block.sum(axis=1)) - block
        scale = float(solver(precision))
        if not np.isfinite(scale) or scale <= 0.0:
            raise ValueError("Independently recomputed component scale is invalid")
        result.append(scale)
    return tuple(result)


def safe_relative_path(
    root: str | Path, relative: str | Path, *, must_exist: bool = False
) -> Path:
    base = Path(root).resolve()
    candidate = Path(relative)
    if candidate.is_absolute() or candidate == Path(".") or ".." in candidate.parts:
        raise ValueError(f"Manifest path must be a safe nonempty relative path: {relative}")
    resolved = (base / candidate).resolve(strict=False)
    if not resolved.is_relative_to(base):
        raise ValueError(f"Manifest path escapes the repository root: {relative}")
    if must_exist and (not resolved.is_file() or resolved.is_symlink()):
        raise ValueError(f"Required manifest file is missing or a symlink: {relative}")
    return resolved


def verify_hash_inventory(
    root: str | Path,
    inventory: Mapping[str, str],
    *,
    exact_files: bool = False,
    allowed_files: Sequence[str] = (),
) -> dict[str, str]:
    base = Path(root).resolve()
    verified: dict[str, str] = {}
    for relative, expected in _sha256_mapping(
        inventory, label="artifact inventory"
    ).items():
        path = safe_relative_path(root, relative, must_exist=True)
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"Artifact SHA-256 mismatch for {relative}: expected {expected}, found {actual}"
            )
        verified[relative] = actual
    if exact_files:
        allowed = set(verified)
        for relative in allowed_files:
            allowed.add(
                safe_relative_path(base, relative, must_exist=True)
                .relative_to(base)
                .as_posix()
            )
        actual_files: set[str] = set()
        for path in base.rglob("*"):
            if path.is_symlink():
                raise ValueError("Exact artifact inventory must not contain symlinks")
            if path.is_file():
                actual_files.add(path.relative_to(base).as_posix())
        if actual_files != allowed:
            raise ValueError(
                "Exact artifact inventory mismatch: "
                f"extra={sorted(actual_files - allowed)} "
                f"missing={sorted(allowed - actual_files)}"
            )
    return verified


def snapshot_protected_trees(root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    files: dict[str, str] = {}
    for relative_root in PROTECTED_TREES:
        tree = (base / relative_root).resolve()
        if not tree.is_dir() or tree.is_symlink() or not tree.is_relative_to(base):
            raise ValueError(f"Protected tree is missing or unsafe: {relative_root}")
        for path in sorted(tree.rglob("*")):
            if path.is_symlink():
                raise ValueError("Protected trees must not contain symlinks")
            if path.is_file():
                files[path.relative_to(base).as_posix()] = sha256_file(path)
    if not files:
        raise ValueError("Protected tree snapshot must contain files")
    return {
        "schema_id": "sr_v2_spatial_protected_tree_manifest/v1",
        "roots": list(PROTECTED_TREES),
        "files": files,
    }


def verify_protected_trees(
    root: str | Path, manifest: Mapping[str, Any]
) -> dict[str, str]:
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("schema_id")
        != "sr_v2_spatial_protected_tree_manifest/v1"
        or manifest.get("roots") != list(PROTECTED_TREES)
    ):
        raise ValueError("Protected-tree manifest contract mismatch")
    expected = _sha256_mapping(
        manifest.get("files"), label="protected-tree files"
    )
    current = snapshot_protected_trees(root)
    if current["files"] != expected:
        expected_paths = set(expected)
        actual_paths = set(current["files"])
        raise ValueError(
            "Protected trees changed: "
            f"extra={sorted(actual_paths - expected_paths)} "
            f"missing={sorted(expected_paths - actual_paths)}"
        )
    return expected


@contextmanager
def exclusive_lock(path: str | Path):
    lock = Path(path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = lock.open("x", encoding="ascii", newline="\n")
    except FileExistsError as error:
        raise FileExistsError(f"Exclusive operation lock already exists: {lock}") from error
    try:
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        os.fsync(handle.fileno())
        yield lock
    finally:
        handle.close()
        lock.unlink(missing_ok=True)


def publish_directory_no_clobber(
    staging: str | Path,
    destination: str | Path,
    *,
    commit_marker: str,
) -> None:
    source = Path(staging)
    target = Path(destination)
    marker = source / commit_marker
    if not marker.is_file() or marker.is_symlink():
        raise ValueError("Atomic publication commit marker is missing or unsafe")
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / f".{target.name}.publication.lock"
    with exclusive_lock(lock):
        if os.path.lexists(target):
            raise FileExistsError(
                f"Destination exists; refusing conflicting run: {target}"
            )
        try:
            # A same-filesystem directory rename is the single atomic commit
            # point. Linux renameat2 adds kernel-level NOREPLACE semantics;
            # Windows os.rename already refuses an existing destination.
            if sys.platform.startswith("linux"):
                import ctypes

                renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
                renameat2.argtypes = [
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_uint,
                ]
                renameat2.restype = ctypes.c_int
                result = renameat2(
                    -100,
                    os.fsencode(source),
                    -100,
                    os.fsencode(target),
                    1,
                )
                if result != 0:
                    code = ctypes.get_errno()
                    raise OSError(code, os.strerror(code), str(target))
            else:
                os.rename(source, target)
        except OSError as error:
            raise FileExistsError(
                f"Destination exists; refusing conflicting run: {target}"
            ) from error


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 string")
    return value


def _sha256_mapping(value: object, *, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{label} must be a nonempty path/hash mapping")
    return {
        str(path): _require_sha256(digest, label=f"{label} {path}")
        for path, digest in value.items()
    }


def verify_sha256_sidecar(path: str | Path) -> str:
    source = Path(path)
    sidecar = source.with_name(source.name + ".sha256")
    if not source.is_file() or source.is_symlink() or not sidecar.is_file() or sidecar.is_symlink():
        raise ValueError(f"Manifest or SHA-256 sidecar is missing or unsafe: {source}")
    expected = _require_sha256(
        sidecar.read_text(encoding="ascii").strip(), label="manifest sidecar"
    )
    actual = sha256_file(source)
    if actual != expected:
        raise ValueError(f"Manifest SHA-256 mismatch: expected {expected}, found {actual}")
    return actual


def load_reviewed_launch_envelope(
    root: str | Path, envelope_path: str | Path
) -> dict[str, Any]:
    """Verify the external reviewed raw-byte heavy+spatial launch authority."""

    base = Path(root).resolve()
    path = Path(envelope_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Reviewed external launch envelope is required before preparation: {path}"
        )
    envelope_hash = verify_sha256_sidecar(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Reviewed launch envelope is not valid JSON") from error
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_id") != "sr_v2_robustness_launch_envelope/v1"
        or payload.get("status") != "reviewed_final"
        or payload.get("clean_worktree") is not True
    ):
        raise ValueError("Reviewed launch envelope contract mismatch")
    launch_commit = str(payload.get("launch_commit", "")).lower()
    bundle_hash = str(payload.get("bundle_sha256", "")).lower()
    if len(launch_commit) != 40 or any(c not in "0123456789abcdef" for c in launch_commit):
        raise ValueError("Reviewed launch commit is invalid")
    _require_sha256(bundle_hash, label="bundle_sha256")
    source_manifest = payload.get("source_manifest")
    if (
        not isinstance(source_manifest, Mapping)
        or source_manifest.get("schema_id")
        != "sr_v2_robustness_final_source_manifest/v1"
        or source_manifest.get("status") != "reviewed_final"
        or source_manifest.get("joint_regression_passed") is not True
        or source_manifest.get("source_hash_mode") != "raw_bytes"
    ):
        raise ValueError("Reviewed final source manifest contract mismatch")
    manifest_hash = canonical_sha256(source_manifest)
    if payload.get("source_manifest_sha256") != manifest_hash:
        raise ValueError("Reviewed final source manifest SHA-256 mismatch")
    sources = _sha256_mapping(
        source_manifest.get("sources"), label="reviewed source manifest"
    )
    if not set(SPATIAL_FINAL_SOURCE_FILES).issubset(sources):
        missing = sorted(set(SPATIAL_FINAL_SOURCE_FILES) - set(sources))
        raise ValueError(f"Reviewed union source manifest omits spatial executables: {missing}")
    for relative, expected in sources.items():
        source = safe_relative_path(base, relative, must_exist=True)
        actual = sha256_file(source)
        if actual != expected:
            raise ValueError(
                f"Reviewed source SHA-256 mismatch for {relative}: expected {expected}, found {actual}"
            )
    evidence_relative = str(source_manifest.get("joint_regression_evidence", ""))
    evidence = safe_relative_path(base, evidence_relative, must_exist=True)
    evidence_hash = _require_sha256(
        source_manifest.get("joint_regression_evidence_sha256"),
        label="joint_regression_evidence_sha256",
    )
    if sha256_file(evidence) != evidence_hash:
        raise ValueError("Joint-regression evidence SHA-256 mismatch")
    return {
        "schema_id": "sr_v2_spatial_launch_provenance/v1",
        "source_manifest": dict(source_manifest),
        "sources": sources,
        "launch_envelope_path": str(path),
        "launch_envelope_sha256": envelope_hash,
        "final_source_manifest_sha256": manifest_hash,
        "launch_commit": launch_commit,
        "bundle_sha256": bundle_hash,
        "joint_regression_evidence": evidence_relative,
        "joint_regression_evidence_sha256": evidence_hash,
    }


def validate_prepared_source_envelope(
    root: str | Path,
    *,
    config_path: str | Path,
    output_base_override: str | Path | None = None,
) -> dict[str, Any]:
    """Revalidate the immutable preparation and its external launch authority.

    This is the shared, read-only staging/runner entrypoint.  It never creates
    launch authority and intentionally rehashes the repository sources, copied
    envelope, prepared inventory, and all manifest sidecars on every call.
    """

    base = Path(root).resolve()
    spec = load_spatial_execution_spec(config_path)
    verify_hash_inventory(base, spec.source_authorities)
    prepared = spatial_run_root(base, output_base_override) / "prepared"
    manifest_path = prepared / "prepared_run_manifest.json"
    manifest_hash = verify_sha256_sidecar(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ValueError("Prepared run manifest must be a mapping")
    if set(manifest) != PREPARED_MANIFEST_EXACT_FIELDS:
        raise ValueError("Prepared run manifest exact schema mismatch")
    required = {
        "schema_id": "sr_v2_spatial_prepared_run/v1",
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "operational_config_sha256": sha256_file(config_path),
        "status": "prepared_not_run",
        "submission_authorized": False,
        "production_eligible": True,
        "builder_provenance": {
            "frame_loader": "default_load_model_frame",
            "allocation_solver": "default_solve_feasible_allocation",
            "graph_preparer": "default_graph_artifacts",
            "envelope_loader": "default_reviewed_launch_envelope",
        },
    }
    if any(manifest.get(key) != value for key, value in required.items()):
        raise ValueError("Prepared run identity/status contract mismatch")
    inventory = manifest.get("prepared_artifact_sha256")
    if not isinstance(inventory, Mapping) or not inventory:
        raise ValueError("Prepared run artifact inventory is missing")
    verified_artifacts = verify_hash_inventory(
        prepared,
        inventory,
        exact_files=True,
        allowed_files=(
            "prepared_run_manifest.json",
            "prepared_run_manifest.json.sha256",
        ),
    )
    config_copy = prepared / "config/sr_v2_spatial_sensitivity_execution.yaml"
    if sha256_file(config_copy) != sha256_file(config_path):
        raise ValueError("Prepared operational config bytes changed")
    envelope_path = prepared / "provenance/launch_envelope.json"
    provenance = load_reviewed_launch_envelope(base, envelope_path)
    binding_fields = (
        "launch_envelope_sha256",
        "final_source_manifest_sha256",
        "launch_commit",
        "bundle_sha256",
        "joint_regression_evidence_sha256",
    )
    if any(manifest.get(field) != provenance.get(field) for field in binding_fields):
        raise ValueError("Prepared run and reviewed launch envelope are not identical")
    source_manifest_path = prepared / "provenance/final_source_manifest.json"
    verify_sha256_sidecar(source_manifest_path)
    if canonical_sha256(json.loads(source_manifest_path.read_text(encoding="utf-8"))) != provenance["final_source_manifest_sha256"]:
        raise ValueError("Prepared final-source manifest identity mismatch")
    input_manifest_path = prepared / str(manifest.get("input_manifest", ""))
    input_hash = verify_sha256_sidecar(input_manifest_path)
    if input_hash != manifest.get("input_manifest_sha256"):
        raise ValueError("Prepared input manifest identity mismatch")
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(input_manifest, Mapping) or set(input_manifest) != INPUT_MANIFEST_EXACT_FIELDS:
        raise ValueError("Prepared input manifest exact schema mismatch")
    input_bindings = {
        "schema_id": "sr_v2_spatial_input_manifest/v1",
        "run_id": RUN_ID,
        "operational_config_sha256": sha256_file(config_path),
        "source_authorities": manifest["source_authorities"],
        "launch_envelope_sha256": manifest["launch_envelope_sha256"],
        "final_source_manifest_sha256": manifest["final_source_manifest_sha256"],
        "launch_commit": manifest["launch_commit"],
        "bundle_sha256": manifest["bundle_sha256"],
        "joint_regression_evidence_sha256": manifest["joint_regression_evidence_sha256"],
        "source_model_frame_sha256": spec.source_authorities[
            "data/processed/bayes_constrained/model_frame.parquet"
        ],
        "prepared_model_frame_sha256": manifest["model_frame_sha256"],
        "model_frame_semantic_sha256": manifest["model_frame_semantic_sha256"],
        "graph_contract_sha256": manifest["graph_contract_sha256"],
    }
    if any(input_manifest.get(key) != value for key, value in input_bindings.items()):
        raise ValueError("Prepared input manifest identity chain mismatch")
    verify_hash_inventory(prepared, input_manifest.get("graph_artifact_sha256"))
    model_relative = "data/processed/bayes_constrained/model_frame.parquet"
    source_frame_path = safe_relative_path(base, model_relative, must_exist=True)
    prepared_frame_path = safe_relative_path(
        prepared, str(manifest.get("model_frame", "")), must_exist=True
    )
    if (
        sha256_file(source_frame_path) != input_manifest["source_model_frame_sha256"]
        or sha256_file(prepared_frame_path) != input_manifest["prepared_model_frame_sha256"]
    ):
        raise ValueError("Source/prepared model-frame raw-byte identity mismatch")
    from .spatial_bym2 import spatial_model_frame_sha256

    source_semantic = spatial_model_frame_sha256(pd.read_parquet(source_frame_path))
    prepared_semantic = spatial_model_frame_sha256(pd.read_parquet(prepared_frame_path))
    if source_semantic != prepared_semantic or prepared_semantic != manifest["model_frame_semantic_sha256"]:
        raise ValueError("Source/prepared model-frame semantic identity mismatch")
    protected_path = prepared / str(manifest.get("protected_tree_manifest", ""))
    protected_hash = verify_sha256_sidecar(protected_path)
    if protected_hash != manifest.get("protected_tree_manifest_sha256"):
        raise ValueError("Prepared protected-tree manifest identity mismatch")
    protected_manifest = json.loads(protected_path.read_text(encoding="utf-8"))
    verify_protected_trees(base, protected_manifest)
    mapping = manifest.get("chain_mapping")
    if not isinstance(mapping, list) or len(mapping) != 4:
        raise ValueError("Prepared run requires exactly four chain mappings")
    if [row.get("array_index") for row in mapping] != [1, 2, 3, 4]:
        raise ValueError("Prepared chain array mapping changed")
    return {
        "schema_id": "sr_v2_spatial_prepared_validation/v1",
        "manifest": dict(manifest),
        "manifest_sha256": manifest_hash,
        "prepared_root": str(prepared),
        "verified_artifact_sha256": verified_artifacts,
        **{field: provenance[field] for field in binding_fields},
    }


def load_verified_chain_status(
    run_root: str | Path, chain_id: int
) -> dict[str, Any] | None:
    """Resolve status from the unique latest immutable attempt.

    The mutable pointer and its sidecar are convenience files only.  A crash
    between their two atomic replacements cannot brick or advance the trust
    chain because selection is derived from immutable attempt directories.
    """

    if isinstance(chain_id, bool) or chain_id not in range(1, 5):
        raise ValueError("chain_id must be an exact integer in 1..4")
    run_root = Path(run_root).resolve()
    chain_root = run_root / f"chains/chain_{chain_id:02d}"
    attempts_root = chain_root / "attempts"
    if not attempts_root.exists():
        return None
    if attempts_root.is_symlink() or not attempts_root.is_dir():
        raise ValueError("Immutable attempt root is unsafe")
    candidates: list[tuple[int, int, Path, dict[str, Any]]] = []
    for immutable in sorted(attempts_root.glob("epoch_*/attempt_*/status.json")):
        if immutable.is_symlink():
            raise ValueError("Immutable chain status must not be a symlink")
        try:
            epoch = int(immutable.parents[1].name.removeprefix("epoch_"))
            attempt = int(immutable.parent.name.removeprefix("attempt_"))
        except ValueError as error:
            raise ValueError("Immutable attempt path is malformed") from error
        if (
            immutable.parents[1].name != f"epoch_{epoch}"
            or immutable.parent.name != f"attempt_{attempt}"
            or epoch not in range(4)
            or attempt not in range(1, 4)
        ):
            raise ValueError("Immutable attempt path is outside the frozen contract")
        verify_sha256_sidecar(immutable)
        value = json.loads(immutable.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("extension_epoch") != epoch
            or value.get("job_attempt") != attempt
            or value.get("chain_id") != chain_id
        ):
            raise ValueError("Immutable attempt status/path identity mismatch")
        candidates.append((epoch, attempt, immutable, value))
    if not candidates:
        raise ValueError("Attempt tree exists without an immutable status")
    keys = [(epoch, attempt) for epoch, attempt, _path, _value in candidates]
    if len(keys) != len(set(keys)):
        raise ValueError("Immutable attempt status position is not unique")
    epoch, attempt, immutable, payload = max(candidates, key=lambda row: row[:2])
    epoch = payload.get("extension_epoch")
    attempt = payload.get("job_attempt")
    if (
        isinstance(epoch, bool)
        or not isinstance(epoch, int)
        or epoch not in range(4)
        or isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or attempt not in range(1, 4)
    ):
        raise ValueError("Chain status epoch/attempt is malformed")
    inventory = payload.get("artifact_sha256")
    if not isinstance(inventory, Mapping) or not inventory:
        raise ValueError("Chain status lacks a nonempty artifact inventory")
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
                raise ValueError("Mutable chain-status pointer is unsafe")
            allowed.append(name)
    verify_hash_inventory(
        chain_root,
        inventory,
        exact_files=True,
        allowed_files=tuple(allowed),
    )
    latest = safe_relative_path(
        chain_root, payload.get("latest_checkpoint", ""), must_exist=True
    )
    latest_hash = verify_sha256_sidecar(latest)
    if latest_hash != payload.get("latest_checkpoint_sha256"):
        raise ValueError("Chain status latest-checkpoint hash mismatch")
    checkpoint = json.loads(latest.read_text(encoding="ascii"))
    if (
        checkpoint.get("schema_version") != 2
        or checkpoint.get("run_id") != RUN_ID
        or checkpoint.get("chain_id") != chain_id
        or checkpoint.get("extension_epoch") != epoch
        or checkpoint.get("chain_fingerprint")
        != payload.get("chain_fingerprint")
        or checkpoint.get("target_fingerprint")
        != payload.get("target_fingerprint")
    ):
        raise ValueError("Chain status and latest checkpoint identity mismatch")
    return dict(payload)


def select_retry_indexes(
    run_root: str | Path, *, extension_epoch: int
) -> dict[str, Any]:
    """Select only missing/incomplete indexes and their next bounded attempt."""

    epoch = int(extension_epoch)
    if isinstance(extension_epoch, bool) or epoch not in range(4):
        raise ValueError("extension_epoch must be an exact integer in 0..3")
    root = Path(run_root).resolve()
    selected: list[int] = []
    attempts: dict[str, int] = {}
    completed: list[int] = []
    fingerprints: set[str] = set()
    expected_epoch = EPOCH_CONTRACT[epoch]
    for chain_id in range(1, 5):
        status = load_verified_chain_status(root, chain_id)
        if status is None:
            if epoch != 0:
                raise ValueError("An extension cannot start from a missing chain status")
            selected.append(chain_id)
            attempts[str(chain_id)] = 1
            continue
        if status.get("run_id") != RUN_ID or status.get("chain_id") != chain_id:
            raise ValueError("Chain status identity mismatch")
        expected_seeds = {
            "chain_seed": 74_290 + chain_id,
            "allocation_initialization_seed": 74_250 + chain_id,
            "spatial_initialization_seed": 74_260 + chain_id,
        }
        if status.get("seeds") != expected_seeds:
            raise ValueError("Chain status seed identity mismatch")
        fingerprint = _require_sha256(
            status.get("chain_fingerprint"), label="chain_fingerprint"
        )
        if fingerprint in fingerprints:
            raise ValueError("Copied/duplicate chain fingerprint in retry selection")
        fingerprints.add(fingerprint)
        status_epoch = status.get("extension_epoch")
        state = status.get("status")
        attempt = status.get("job_attempt")
        if isinstance(status_epoch, bool) or not isinstance(status_epoch, int):
            raise ValueError("Chain status epoch is malformed")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt not in range(1, 4):
            raise ValueError("Chain status attempt is malformed")
        if status_epoch != epoch:
            raise ValueError("Within-epoch retry cannot cross an extension epoch")
        if state == "completed":
            if (
                status.get("iterations") != expected_epoch["iterations"]
                or status.get("retained_draws") != expected_epoch["draws"]
                or status.get("chunks") != expected_epoch["chunks"]
            ):
                raise ValueError("Completed retry status violates epoch cardinality")
            if status.get("retryable") is not False or status.get("failure_category") is not None:
                raise ValueError("Completed status must be terminal and failure-free")
            completed.append(chain_id)
            continue
        if state not in {"checkpointed", "failed"}:
            raise ValueError("Only checkpointed or failed chains may be retried")
        if state == "checkpointed":
            if status.get("retryable") is not True or status.get("failure_category") is not None:
                raise ValueError("Checkpointed status lacks explicit retry authority")
        elif (
            status.get("retryable") is not True
            or status.get("failure_category") != "transient_runtime"
        ):
            raise ValueError("Failed chain is not an explicitly transient retry")
        if attempt == 3:
            raise ValueError("Attempt three is terminal; attempt four is forbidden")
        selected.append(chain_id)
        attempts[str(chain_id)] = attempt + 1
    return {
        "schema_id": "sr_v2_spatial_retry_selection/v1",
        "run_id": RUN_ID,
        "extension_epoch": epoch,
        "selected_array_indexes": selected,
        "next_job_attempt_by_array_index": attempts,
        "verified_completed_indexes": completed,
    }


def validate_extension_authorization(
    run_root: str | Path, *, to_extension_epoch: int
) -> dict[str, Any]:
    """Validate reviewed convergence-only authority and select all four chains."""

    epoch = int(to_extension_epoch)
    if isinstance(to_extension_epoch, bool) or epoch not in range(1, 4):
        raise ValueError("to_extension_epoch must be an exact integer in 1..3")
    root = Path(run_root).resolve()
    path = root / f"extension_authorization_epoch_{epoch}.json"
    authorization_file_hash = verify_sha256_sidecar(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    required_fields = {
        "schema_id",
        "run_id",
        "from_extension_epoch",
        "to_extension_epoch",
        "reason_convergence_only",
        "reviewer",
        "reviewed_utc",
        "prior_preparation_identity",
        "prior_pre_gate_manifest_sha256",
        "prior_independent_verification_sha256",
        "prior_release_manifest_sha256",
        "prior_gate_decision_sha256",
        "authorization_sha256",
    }
    if not isinstance(payload, Mapping) or set(payload) != required_fields:
        raise ValueError("Extension authorization schema mismatch")
    unsigned = {key: payload[key] for key in payload if key != "authorization_sha256"}
    if (
        payload.get("schema_id") != "sr_v2_spatial_extension_authorization/v1"
        or payload.get("run_id") != RUN_ID
        or payload.get("from_extension_epoch") != epoch - 1
        or payload.get("to_extension_epoch") != epoch
        or payload.get("reason_convergence_only") is not True
        or not str(payload.get("reviewer", "")).strip()
        or not str(payload.get("reviewed_utc", "")).strip()
        or payload.get("authorization_sha256") != canonical_sha256(unsigned)
    ):
        raise ValueError("Extension authorization is not reviewed convergence-only authority")
    fingerprints: set[str] = set()
    preparation_identities: set[str] = set()
    launch_envelopes: set[str] = set()
    for chain_id in range(1, 5):
        status = load_verified_chain_status(root, chain_id)
        expected = EPOCH_CONTRACT[epoch - 1]
        expected_seeds = {
            "chain_seed": 74_290 + chain_id,
            "allocation_initialization_seed": 74_250 + chain_id,
            "spatial_initialization_seed": 74_260 + chain_id,
        }
        if (
            status is None
            or status.get("status") != "completed"
            or status.get("extension_epoch") != epoch - 1
            or status.get("iterations") != expected["iterations"]
            or status.get("retained_draws") != expected["draws"]
            or status.get("chunks") != expected["chunks"]
            or status.get("seeds") != expected_seeds
        ):
            raise ValueError("Every prior-epoch chain must be exactly completed before extension")
        fingerprint = _require_sha256(
            status.get("chain_fingerprint"), label="chain_fingerprint"
        )
        if fingerprint in fingerprints:
            raise ValueError("Copied/duplicate chain fingerprint before extension")
        fingerprints.add(fingerprint)
        preparation_identities.add(
            _require_sha256(
                status.get("preparation_identity"), label="preparation_identity"
            )
        )
        launch_envelopes.add(
            _require_sha256(
                status.get("launch_envelope_sha256"),
                label="launch_envelope_sha256",
            )
        )
    if len(preparation_identities) != 1 or len(launch_envelopes) != 1:
        raise ValueError("Extension chains do not share one preparation/envelope")
    prior_epoch = epoch - 1
    evidence_paths = {
        "prior_pre_gate_manifest_sha256": root
        / f"epochs/epoch_{prior_epoch}/merge/pre_gate_manifest.json",
        "prior_independent_verification_sha256": root
        / f"epochs/epoch_{prior_epoch}/verification/independent_spatial_sensitivity_verification.json",
        "prior_release_manifest_sha256": root
        / f"epochs/epoch_{prior_epoch}/release/spatial_sensitivity_release_manifest.json",
        "prior_gate_decision_sha256": root
        / f"epochs/epoch_{prior_epoch}/gate/gate_decision.json",
    }
    for field, evidence_path in evidence_paths.items():
        if verify_sha256_sidecar(evidence_path) != payload.get(field):
            raise ValueError(f"Extension authorization prior evidence mismatch: {field}")
    gate_decision = json.loads(
        evidence_paths["prior_gate_decision_sha256"].read_text(encoding="utf-8")
    )
    preparation_identity = next(iter(preparation_identities))
    if (
        payload.get("prior_preparation_identity") != preparation_identity
        or gate_decision.get("status") != "HOLD"
        or gate_decision.get("passed") is not False
        or gate_decision.get("reason") != "convergence_only"
        or gate_decision.get("extension_eligible") is not True
        or gate_decision.get("extension_epoch") != prior_epoch
        or gate_decision.get("preparation_identity") != preparation_identity
        or gate_decision.get("pre_gate_manifest_sha256")
        != payload.get("prior_pre_gate_manifest_sha256")
        or gate_decision.get("independent_verification_sha256")
        != payload.get("prior_independent_verification_sha256")
        or gate_decision.get("release_manifest_sha256")
        != payload.get("prior_release_manifest_sha256")
    ):
        raise ValueError("Extension authorization is not bound to convergence-only HOLD")
    return {
        "schema_id": "sr_v2_spatial_extension_selection/v1",
        "run_id": RUN_ID,
        "from_extension_epoch": epoch - 1,
        "to_extension_epoch": epoch,
        "selected_array_indexes": [1, 2, 3, 4],
        "job_attempt": 1,
        "authorization_path": path.name,
        "authorization_file_sha256": authorization_file_hash,
        "authorization_sha256": payload["authorization_sha256"],
    }


def set_benchmark_failure_hold(
    root: str | Path,
    *,
    reason: str,
    output_base_override: str | Path | None = None,
) -> dict[str, object]:
    return set_canonical_hold(
        root,
        reason=f"benchmark_failed:{reason}",
        stage="benchmark",
        extension_epoch=0,
        output_base_override=output_base_override,
    )


def validate_benchmark_evidence(
    run_root: str | Path,
    *,
    preparation_identity: str,
    target_fingerprints: Sequence[str],
    launch_envelope_sha256: str,
    final_source_manifest_sha256: str,
) -> dict[str, Any]:
    """Validate immutable Task-4 benchmark evidence at inclusive limits."""

    path = Path(run_root).resolve() / "benchmark/benchmark_report.json"
    report_hash = verify_sha256_sidecar(path)
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, Mapping):
        raise ValueError("Spatial benchmark report must be a mapping")
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
    if set(report) != required_fields:
        raise ValueError("Spatial benchmark report schema mismatch")
    if (
        report.get("schema_id") != "sr_v2_spatial_benchmark/v1"
        or report.get("run_id") != RUN_ID
        or report.get("preparation_identity") != preparation_identity
        or report.get("target_fingerprint") not in set(target_fingerprints)
        or report.get("launch_envelope_sha256") != launch_envelope_sha256
        or report.get("final_source_manifest_sha256")
        != final_source_manifest_sha256
        or report.get("builder") != "exact_prepared_public_chain"
        or report.get("iterations") != 2_000
        or report.get("projection_overhead_factor") != 1.2
        or report.get("projected_hours_limit_inclusive") != 65.0
        or report.get("peak_rss_gib_limit_inclusive") != 56.0
        or report.get("passed") is not True
        or report.get("scientific_draws_published") is not False
        or report.get("submission_authorized") is not False
        or report.get("paired_chunk_draws") != 250
        or report.get("paired_chunk_scalar_rows") != 17_750
        or report.get("paired_chunk_builder") != "actual_commit_spatial_draw_chunk"
        or report.get("paired_chunk_scientific_data") is not False
    ):
        raise ValueError("Spatial benchmark identity/status contract mismatch")
    projected = _finite_float(report.get("projected_hours"), label="projected_hours")
    rss = _finite_float(report.get("peak_rss_gib"), label="peak_rss_gib")
    elapsed = _finite_float(report.get("elapsed_seconds"), label="elapsed_seconds")
    rate = _finite_float(
        report.get("iterations_per_second"), label="iterations_per_second"
    )
    paired_bytes = report.get("paired_chunk_bytes")
    if isinstance(paired_bytes, bool) or not isinstance(paired_bytes, int) or paired_bytes <= 0:
        raise ValueError("Spatial benchmark paired-chunk byte count is invalid")
    paired_elapsed = _finite_float(
        report.get("paired_chunk_elapsed_seconds"), label="paired_chunk_elapsed_seconds"
    )
    paired_rate = _finite_float(
        report.get("paired_chunk_mib_per_second"), label="paired_chunk_mib_per_second"
    )
    _require_sha256(
        report.get("paired_chunk_record_sha256"), label="paired_chunk_record_sha256"
    )
    if (
        projected > 65.0
        or rss > 56.0
        or elapsed <= 0.0
        or rate <= 0.0
        or paired_elapsed <= 0.0
        or paired_rate <= 0.0
        or not math.isclose(
            paired_rate,
            paired_bytes / paired_elapsed / 1024**2,
            rel_tol=1e-12,
            abs_tol=0.0,
        )
        or not math.isclose(rate, 2_000 / elapsed, rel_tol=1e-12, abs_tol=0.0)
        or not math.isclose(
            projected,
            elapsed / 2_000 * 180_000 * 1.2 / 3_600,
            rel_tol=1e-12,
            abs_tol=0.0,
        )
    ):
        raise ValueError("Spatial benchmark exceeds or misstates its limits")
    return {"report": dict(report), "report_sha256": report_hash, "path": str(path)}


def _finite_float(value: Any, *, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def comparison_candidate_bytes(
    primary_summary: pd.DataFrame,
    spatial_scalar_draws: pd.DataFrame,
) -> bytes:
    """Return the frozen eight-row comparison as deterministic LF CSV bytes."""

    required_primary = {
        "parameter",
        "posterior_mean",
        "credible_interval_lower_95",
        "credible_interval_upper_95",
    }
    if not required_primary.issubset(primary_summary.columns):
        raise ValueError("Primary comparison summary schema is incomplete")
    primary = primary_summary.loc[
        primary_summary["parameter"].isin(COMPARISON_ROWS),
        list(required_primary),
    ].copy()
    if (
        len(primary) != len(COMPARISON_ROWS)
        or primary["parameter"].duplicated().any()
        or set(primary["parameter"]) != set(COMPARISON_ROWS)
    ):
        raise ValueError("Primary comparison summary must contain the exact eight rows")
    scalar_columns = {
        "chain_id",
        "draw_id",
        "extension_epoch",
        "parameter",
        "value",
    }
    if set(spatial_scalar_draws.columns) != scalar_columns:
        raise ValueError("Spatial comparison draw schema mismatch")
    draws = spatial_scalar_draws.loc[
        spatial_scalar_draws["parameter"].isin(COMPARISON_ROWS)
    ].copy()
    if set(draws["parameter"].unique()) != set(COMPARISON_ROWS):
        raise ValueError("Spatial comparison draws omit required parameters")
    if sorted(draws["chain_id"].unique().tolist()) != [1, 2, 3, 4]:
        raise ValueError("Spatial comparison draws require exactly chains 1..4")
    if draws.duplicated(["chain_id", "draw_id", "parameter"]).any():
        raise ValueError("Spatial comparison draws contain duplicate cells")
    values = draws["value"].to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("Spatial comparison draws contain nonfinite values")

    primary_index = primary.set_index("parameter")
    result: list[list[str]] = []
    for parameter in COMPARISON_ROWS:
        primary_row = primary_index.loc[parameter]
        primary_mean = _finite_float(
            primary_row["posterior_mean"], label=f"{parameter} primary_mean"
        )
        if primary_mean == 0.0:
            raise ValueError(f"{parameter} primary_mean must be nonzero")
        primary_lower = _finite_float(
            primary_row["credible_interval_lower_95"],
            label=f"{parameter} primary_lower_95",
        )
        primary_upper = _finite_float(
            primary_row["credible_interval_upper_95"],
            label=f"{parameter} primary_upper_95",
        )
        if primary_lower > primary_upper:
            raise ValueError(f"{parameter} primary interval is reversed")
        raw = draws.loc[draws["parameter"].eq(parameter), "value"].to_numpy(
            dtype=np.float64
        )
        reporting = np.exp(raw) if parameter in COMPARISON_ROWS[:6] else raw
        if not np.isfinite(reporting).all():
            raise ValueError(f"{parameter} reporting-scale draws are nonfinite")
        spatial_mean = float(np.mean(reporting, dtype=np.float64))
        spatial_lower, spatial_upper = map(
            float, np.quantile(reporting, [0.025, 0.975], method="linear")
        )
        delta = spatial_mean - primary_mean
        relative = delta / abs(primary_mean)
        overlap = max(primary_lower, spatial_lower) <= min(
            primary_upper, spatial_upper
        )
        numeric = (
            primary_mean,
            primary_lower,
            primary_upper,
            spatial_mean,
            spatial_lower,
            spatial_upper,
            delta,
            relative,
        )
        if not np.isfinite(numeric).all():
            raise ValueError(f"{parameter} comparison contains nonfinite values")
        result.append(
            [
                parameter,
                COMPARISON_SCALE[parameter],
                *(format(value, ".17g") for value in numeric),
                "true" if overlap else "false",
            ]
        )
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=",", lineterminator="\n")
    writer.writerow(COMPARISON_FIELDS)
    writer.writerows(result)
    return buffer.getvalue().encode("utf-8")


__all__ = [
    "COMPARISON_FIELDS",
    "COMPARISON_ROWS",
    "COMPARISON_SCALE",
    "EPOCH_CONTRACT",
    "EXPECTED_SOURCE_AUTHORITIES",
    "MODEL_ID",
    "OUTPUT_ROOT",
    "PROTECTED_TREES",
    "RUN_ID",
    "SPATIAL_FINAL_SOURCE_FILES",
    "SpatialAssignment",
    "SpatialExecutionSpec",
    "atomic_json",
    "canonical_json_bytes",
    "canonical_sha256",
    "comparison_candidate_bytes",
    "exclusive_lock",
    "load_reviewed_launch_envelope",
    "load_spatial_execution_spec",
    "publish_directory_no_clobber",
    "recompute_component_scales",
    "safe_relative_path",
    "set_canonical_hold",
    "set_benchmark_failure_hold",
    "sha256_file",
    "spatial_run_root",
    "select_retry_indexes",
    "snapshot_protected_trees",
    "validate_extension_authorization",
    "validate_benchmark_evidence",
    "validate_prepared_source_envelope",
    "verify_protected_trees",
    "verify_sha256_sidecar",
    "verify_hash_inventory",
]
