#!/usr/bin/env python3
"""Run one identity-bound SR-v2 BYM2 chain, retry, or reviewed extension."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.model import active_prior_specification, make_design
from bayes_constrained.sampler import SpatialChainExecutionError, run_spatial_mcmc_chain
from bayes_constrained.spatial_bym2 import (
    build_bym2_graph,
    commit_spatial_draw_chunk,
    load_spatial_checkpoint,
    save_spatial_checkpoint,
    spatial_checkpoint_identity,
)
from bayes_constrained.spatial_pipeline import (
    EPOCH_CONTRACT,
    RUN_ID,
    atomic_json,
    canonical_json_bytes,
    load_spatial_execution_spec,
    load_verified_chain_status,
    publish_directory_no_clobber,
    set_benchmark_failure_hold,
    set_canonical_hold,
    sha256_file,
    spatial_run_root,
    validate_extension_authorization,
    validate_prepared_source_envelope,
    verify_hash_inventory,
    verify_sha256_sidecar,
)


CONFIG_PATH = ROOT / "config/sr_v2_spatial_sensitivity_execution.yaml"
CHECKPOINT_EXIT_CODE = 75
FROZEN_CHAIN_SETTINGS: dict[str, object] = {
    "count_move_sweeps_per_iter": 0.1,
    "max_count_proposals_per_iter": 350,
    "blocked_refresh_frequency": 25,
    "blocked_refresh_attempts": 12,
    "max_cycle_half_length": 6,
    "move_weights": {
        "state_year_transfer": 0.50,
        "county_period_exploration": 0.15,
        "interval_path_transfer": 0.15,
        "swap_2x2": 0.15,
        "cycle_swap": 0.05,
    },
}


def _write_sidecar(path: Path) -> None:
    payload = (sha256_file(path) + "\n").encode("ascii")
    temporary = path.with_name(f".{path.name}.sha256.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path.with_name(path.name + ".sha256"))


def _load_status(chain_root: Path) -> dict[str, Any] | None:
    if chain_root.name != "chains" and chain_root.parent.name == "chains":
        run_root = chain_root.parent.parent
        chain_id = int(chain_root.name.removeprefix("chain_"))
        return load_verified_chain_status(run_root, chain_id)
    raise ValueError("Chain root does not follow the frozen run layout")


def _runtime_target(
    root: Path, validation: Mapping[str, Any]
) -> tuple[pd.DataFrame, Any, Any]:
    manifest = validation["manifest"]
    prepared = Path(str(validation["prepared_root"]))
    frame_path = prepared / str(manifest["model_frame"])
    if sha256_file(frame_path) != manifest["model_frame_sha256"]:
        raise ValueError("Prepared model-frame raw bytes changed")
    frame = pd.read_parquet(frame_path)
    adjacency_relative = (
        "outputs/scientific_reports_v2/spatial_residual_diagnostics/"
        "county_adjacency2024.txt"
    )
    graph = build_bym2_graph(
        frame,
        root / adjacency_relative,
        expected_sha256=manifest["source_authorities"][adjacency_relative],
    )
    if graph.contract_sha256 != manifest["graph_contract_sha256"]:
        raise ValueError("Prepared graph and reconstructed runtime graph differ")
    design = make_design(frame, spatial_graph=graph)
    return frame, design, active_prior_specification()


def _copy_initial_checkpoint(source: Path, destination: Path) -> Path:
    verify_sha256_sidecar(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sidecar = destination.with_name(destination.name + ".sha256")
    if os.path.lexists(destination) or os.path.lexists(sidecar):
        raise FileExistsError("Initial chain checkpoint target already exists")
    shutil.copyfile(source, destination)
    shutil.copyfile(source.with_name(source.name + ".sha256"), sidecar)
    verify_sha256_sidecar(destination)
    return destination


def _rebind_extension_checkpoint(
    *,
    prior_checkpoint: Path,
    checkpoint_dir: Path,
    chunk_dir: Path,
    prior_identity: Mapping[str, Any],
    new_identity: Mapping[str, Any],
    extension_epoch: int,
    frame: pd.DataFrame,
    design: Any,
    prior: Any,
) -> Path:
    loaded = load_spatial_checkpoint(
        prior_checkpoint,
        expected_identity=prior_identity,
        frame=frame,
        design=design,
        intercept_mean=float.fromhex(
            str(prior_identity["target"]["intercept_mean_float_hex"])
        ),
        prior=prior,
        chunk_dir=chunk_dir,
    )
    previous = EPOCH_CONTRACT[extension_epoch - 1]
    if (
        loaded["iteration"] != previous["iterations"]
        or loaded["saved_draws"] != previous["draws"]
        or loaded["adaptation_state"].get("adaptation_frozen") is not True
    ):
        raise ValueError("Extension must continue an exact frozen terminal checkpoint")
    destination = checkpoint_dir / (
        f"checkpoint_epoch_{extension_epoch}_attempt_1_"
        f"iter_{previous['iterations']:09d}.json"
    )
    save_spatial_checkpoint(
        destination,
        identity=new_identity,
        extension_epoch=extension_epoch,
        job_attempt=1,
        y=loaded["y"],
        theta=loaded["theta"],
        rng=loaded["rng"],
        frame=frame,
        design=design,
        intercept_mean=float.fromhex(
            str(new_identity["target"]["intercept_mean_float_hex"])
        ),
        prior=prior,
        iteration=loaded["iteration"],
        saved_draws=loaded["saved_draws"],
        current_target=loaded["current_target"],
        accepted=loaded["accepted"],
        proposed=loaded["proposed"],
        committed_chunks=loaded["committed_chunks"],
        pending_scalar=loaded["pending_scalar"],
        pending_structured=loaded["pending_structured"],
        pending_unstructured=loaded["pending_unstructured"],
        adaptation_state=loaded["adaptation_state"],
        next_draw_id=loaded["next_draw_id"],
        output_positions=loaded["output_positions"],
        chunk_dir=chunk_dir,
    )
    return destination


def _draw_epoch(draw_id: int) -> int:
    if draw_id <= 4_500:
        return 0
    if draw_id <= 7_500:
        return 1
    if draw_id <= 10_500:
        return 2
    if draw_id <= 13_500:
        return 3
    raise ValueError("Retained draw id exceeds the frozen extension contract")


def _write_attempt_evidence(
    chain_root: Path,
    *,
    chain_id: int,
    extension_epoch: int,
    job_attempt: int,
    start_saved_draws: int,
    records: object,
    evidence_builder: object,
    production_executor: bool,
) -> dict[str, object]:
    if not isinstance(records, list):
        raise ValueError("Public loop retained-assertion evidence must be a list")
    expected_fields = {
        "schema_id",
        "chain_id",
        "draw_id",
        "cumulative_iteration",
        "extension_epoch",
        "chunk_id",
        "capture_order",
        "count_constraints_asserted",
        "spatial_constraints_asserted",
        "latent_y_sha256",
        "structured_effect_sha256",
        "assertion_sha256",
    }
    normalized: list[dict[str, object]] = []
    for offset, raw in enumerate(records, start=1):
        if not isinstance(raw, Mapping) or set(raw) != expected_fields:
            raise ValueError("Retained-assertion record schema mismatch")
        record = dict(raw)
        draw_id = start_saved_draws + offset
        unsigned = {key: record[key] for key in record if key != "assertion_sha256"}
        if (
            record["schema_id"] != "sr_v2_spatial_retained_assertion/v1"
            or record["chain_id"] != chain_id
            or record["draw_id"] != draw_id
            or record["cumulative_iteration"] != 45_000 + 30 * draw_id
            or record["extension_epoch"] != _draw_epoch(draw_id)
            or record["chunk_id"] != (draw_id - 1) // 250 + 1
            or record["capture_order"]
            != "after_latent_target_base6_hyper_and_scheduled_mala"
            or record["count_constraints_asserted"] is not True
            or record["spatial_constraints_asserted"] is not True
            or len(str(record["latent_y_sha256"])) != 64
            or len(str(record["structured_effect_sha256"])) != 64
            or record["assertion_sha256"]
            != hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
        ):
            raise ValueError("Retained-assertion record identity/digest mismatch")
        normalized.append(record)
    if production_executor and evidence_builder != "actual_public_chain_loop":
        raise ValueError("Production evidence must come from the actual public chain loop")
    epoch_dir = chain_root / f"evidence/epoch_{extension_epoch}"
    epoch_dir.mkdir(parents=True, exist_ok=True)
    destination = epoch_dir / f"attempt_{job_attempt}"
    staging = Path(tempfile.mkdtemp(prefix=".attempt-evidence-", dir=epoch_dir))
    ledger = staging / "retained_assertions.jsonl"
    ledger_payload = b"".join(
        canonical_json_bytes(record) + b"\n" for record in normalized
    )
    with ledger.open("xb") as handle:
        handle.write(ledger_payload)
        handle.flush()
        os.fsync(handle.fileno())
    ledger_hash = sha256_file(ledger)
    evidence = {
        "schema_id": "sr_v2_spatial_attempt_evidence/v1",
        "run_id": RUN_ID,
        "chain_id": chain_id,
        "extension_epoch": extension_epoch,
        "job_attempt": job_attempt,
        "start_saved_draws": start_saved_draws,
        "end_saved_draws": start_saved_draws + len(normalized),
        "record_count": len(normalized),
        "ledger_path": "retained_assertions.jsonl",
        "ledger_sha256": ledger_hash,
        "evidence_builder": str(evidence_builder),
        "production_executor": production_executor,
        "capture_order": "after_latent_target_base6_hyper_and_scheduled_mala",
        "count_constraint_failures": 0,
        "spatial_constraint_failures": 0,
        "historical_latent_y_stored": False,
        "independent_historical_y_reconstruction_possible": False,
        "verification_boundary": (
            "The verifier checks the exact retained schedule and in-loop assertion "
            "evidence but cannot independently reconstruct historical latent y."
        ),
    }
    manifest = staging / "attempt_evidence.json"
    try:
        atomic_json(manifest, evidence)
        _write_sidecar(manifest)
        publish_directory_no_clobber(
            staging,
            destination,
            commit_marker="attempt_evidence.json.sha256",
        )
        return evidence
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _cumulative_evidence(
    chain_root: Path, *, chain_id: int, through_epoch: int, expected_draws: int
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    manifest_hashes: dict[str, str] = {}
    for epoch in range(through_epoch + 1):
        evidence_dir = chain_root / f"evidence/epoch_{epoch}"
        if not evidence_dir.is_dir():
            raise ValueError("Retained-assertion evidence epoch directory is missing")
        manifests = sorted(evidence_dir.glob("attempt_*/attempt_evidence.json"))
        if not manifests:
            raise ValueError("Retained-assertion evidence manifest is missing")
        expected_start = len(records)
        for manifest_path in manifests:
            verify_sha256_sidecar(manifest_path)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            ledger = manifest_path.parent / str(manifest.get("ledger_path", ""))
            if sha256_file(ledger) != manifest.get("ledger_sha256"):
                raise ValueError("Retained-assertion ledger SHA-256 mismatch")
            if manifest.get("start_saved_draws") != expected_start:
                raise ValueError("Retained-assertion attempts are not contiguous")
            raw_lines = ledger.read_bytes().splitlines()
            if len(raw_lines) != manifest.get("record_count"):
                raise ValueError("Retained-assertion ledger cardinality mismatch")
            attempt_records = [json.loads(line) for line in raw_lines]
            if manifest.get("end_saved_draws") != expected_start + len(attempt_records):
                raise ValueError("Retained-assertion manifest end position mismatch")
            records.extend(attempt_records)
            expected_start = len(records)
            manifest_hashes[
                manifest_path.relative_to(chain_root).as_posix()
            ] = sha256_file(manifest_path)
    if len(records) != expected_draws:
        raise ValueError("Cumulative retained-assertion evidence draw count mismatch")
    for draw_id, record in enumerate(records, start=1):
        unsigned = {key: record[key] for key in record if key != "assertion_sha256"}
        if (
            record.get("chain_id") != chain_id
            or record.get("draw_id") != draw_id
            or record.get("cumulative_iteration") != 45_000 + 30 * draw_id
            or record.get("extension_epoch") != _draw_epoch(draw_id)
            or record.get("count_constraints_asserted") is not True
            or record.get("spatial_constraints_asserted") is not True
            or record.get("assertion_sha256")
            != hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
        ):
            raise ValueError("Cumulative retained-assertion record mismatch")
    digest = hashlib.sha256(
        b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    ).hexdigest()
    return {
        "records": len(records),
        "ledger_sha256": digest,
        "manifest_sha256": manifest_hashes,
        "historical_latent_y_stored": False,
        "independent_historical_y_reconstruction_possible": False,
    }


def _artifact_inventory(chain_root: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for subdir in ("checkpoints", "chunks", "evidence", "attempts"):
        base = chain_root / subdir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                raise ValueError("Chain artifacts must not contain symlinks")
            if path.is_file():
                inventory[path.relative_to(chain_root).as_posix()] = sha256_file(path)
    return inventory


def _publish_status(chain_root: Path, payload: Mapping[str, object]) -> None:
    epoch = int(payload["extension_epoch"])
    attempt = int(payload["job_attempt"])
    destination = chain_root / f"attempts/epoch_{epoch}/attempt_{attempt}"
    staging = Path(tempfile.mkdtemp(prefix=".status-", dir=chain_root))
    try:
        status_path = staging / "status.json"
        atomic_json(status_path, payload)
        _write_sidecar(status_path)
        publish_directory_no_clobber(
            staging, destination, commit_marker="status.json.sha256"
        )
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    pointer = chain_root / "chain_status.json"
    atomic_json(pointer, payload)
    _write_sidecar(pointer)


def _verified_completed_noop(
    chain_root: Path, status: Mapping[str, Any], *, extension_epoch: int
) -> dict[str, Any]:
    expected = EPOCH_CONTRACT[extension_epoch]
    if (
        status.get("status") != "completed"
        or status.get("extension_epoch") != extension_epoch
        or status.get("iterations") != expected["iterations"]
        or status.get("retained_draws") != expected["draws"]
        or status.get("chunks") != expected["chunks"]
    ):
        raise ValueError("Completed-chain idempotence requires the exact epoch contract")
    return dict(status)


_CHECKPOINT_NAME = re.compile(
    r"^checkpoint_epoch_(?P<epoch>[0-3])_attempt_(?P<attempt>[1-3])_"
    r"iter_(?P<iteration>[0-9]{9})\.json$"
)


def _recover_latest_valid_checkpoint(
    *,
    checkpoint_dir: Path,
    fallback: Path,
    identity: Mapping[str, Any],
    extension_epoch: int,
    frame: pd.DataFrame,
    design: Any,
    prior: Any,
    chunk_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Return the numerically latest fully validated immutable checkpoint."""

    candidates: dict[Path, tuple[int, int]] = {}
    for path in checkpoint_dir.glob("checkpoint_*.json"):
        match = _CHECKPOINT_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Unexpected checkpoint filename: {path.name}")
        if int(match.group("epoch")) == extension_epoch:
            candidates[path.resolve()] = (
                int(match.group("iteration")),
                int(match.group("attempt")),
            )
    candidates.setdefault(fallback.resolve(), (-1, -1))
    valid: list[tuple[int, int, Path, dict[str, Any]]] = []
    invalid_complete: list[str] = []
    for path, filename_position in candidates.items():
        try:
            loaded = load_spatial_checkpoint(
                path,
                expected_identity=identity,
                frame=frame,
                design=design,
                intercept_mean=float.fromhex(
                    str(identity["target"]["intercept_mean_float_hex"])
                ),
                prior=prior,
                chunk_dir=chunk_dir,
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            if path.is_file() and path.with_name(path.name + ".sha256").is_file():
                invalid_complete.append(f"{path.name}:{type(error).__name__}")
            continue
        if loaded["extension_epoch"] != extension_epoch:
            continue
        position = (
            int(loaded["iteration"]),
            int(loaded["job_attempt"]),
        )
        if filename_position != (-1, -1) and position != filename_position:
            raise ValueError("Checkpoint filename/payload position mismatch")
        valid.append((*position, path, loaded))
    if invalid_complete:
        raise ValueError(
            "A fully published checkpoint failed validation: "
            + ",".join(sorted(invalid_complete))
        )
    if not valid:
        raise ValueError("No fully valid checkpoint is available for recovery")
    _iteration, _attempt, path, loaded = max(valid, key=lambda row: row[:2])
    return path, loaded


def _failure_taxonomy(error: BaseException) -> tuple[str, bool]:
    text = f"{type(error).__name__}:{error}".lower()
    rules = (
        ("source", ("source", "launch envelope", "worktree", "bundle")),
        ("graph", ("graph", "adjacency", "component scale")),
        ("constraint", ("constraint", "latent count", "sum-to-zero", "centered")),
        ("fingerprint", ("fingerprint", "identity mismatch", "seed identity")),
        ("nonfinite_value", ("nonfinite", "nan", "infinite")),
        (
            "evidence_integrity",
            ("evidence", "sha-256", "digest", "inventory", "schema", "symlink", "clobber"),
        ),
    )
    for category, needles in rules:
        if any(needle in text for needle in needles):
            return category, False
    if isinstance(
        error,
        (SpatialChainExecutionError, TimeoutError, InterruptedError, ConnectionError, RuntimeError),
    ):
        return "transient_runtime", True
    return "internal_nonretryable", False


def _require_retry_authority(status: Mapping[str, Any]) -> None:
    state = status.get("status")
    if state == "checkpointed":
        if status.get("retryable") is not True or status.get("failure_category") is not None:
            raise ValueError("Checkpointed status lacks explicit retry authority")
        return
    if state == "failed":
        if (
            status.get("retryable") is not True
            or status.get("failure_category") != "transient_runtime"
        ):
            raise ValueError("Failed chain is not an explicitly transient retry")
        return
    raise ValueError("Only checkpointed or failed status may retry")


def run_chain(
    *,
    run_id: str,
    array_index: int,
    extension_epoch: int,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    output_base_override: Path | None = None,
    prepared_validator: Callable[..., Mapping[str, Any]] = validate_prepared_source_envelope,
    runtime_loader: Callable[[Path, Mapping[str, Any]], tuple[pd.DataFrame, Any, Any]] = _runtime_target,
    chain_executor: Callable[..., Mapping[str, Any]] = run_spatial_mcmc_chain,
    bounded_test_mode: bool = False,
) -> dict[str, Any]:
    root = Path(root).resolve()
    set_canonical_hold(
        root,
        reason="chain_not_verified",
        stage="chain",
        extension_epoch=extension_epoch,
        output_base_override=output_base_override,
    )
    if run_id != RUN_ID:
        raise ValueError("Runner run-id does not match the frozen contract")
    spec = load_spatial_execution_spec(config_path)
    assignment = spec.assignment(array_index)
    if isinstance(extension_epoch, bool) or extension_epoch not in range(4):
        raise ValueError("Runner extension epoch must be exactly 0..3")
    validation = prepared_validator(
        root,
        config_path=config_path,
        output_base_override=output_base_override,
    )
    manifest = validation["manifest"]
    mapping = manifest["chain_mapping"]
    chain_row = next(
        row for row in mapping if row["array_index"] == assignment.array_index
    )
    if (
        chain_row["chain_id"] != assignment.chain_id
        or chain_row["chain_seed"] != assignment.chain_seed
        or chain_row["allocation_initialization_seed"]
        != assignment.allocation_initialization_seed
        or chain_row["spatial_initialization_seed"]
        != assignment.spatial_initialization_seed
    ):
        raise ValueError("Prepared chain mapping/seeds changed")
    run_root = spatial_run_root(root, output_base_override)
    chain_root = run_root / f"chains/chain_{assignment.chain_id:02d}"
    chain_root.mkdir(parents=True, exist_ok=True)
    status = _load_status(chain_root)
    if status is not None and status.get("status") == "completed" and status.get(
        "extension_epoch"
    ) == extension_epoch:
        return _verified_completed_noop(
            chain_root, status, extension_epoch=extension_epoch
        )
    frame, design, prior = runtime_loader(root, validation)
    checkpoint_dir = chain_root / "checkpoints"
    chunk_dir = chain_root / "chunks"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    if status is None:
        if extension_epoch != 0:
            raise ValueError("A chain cannot begin directly in an extension epoch")
        job_attempt = 1
        identity = chain_row["target_identity"]
        prepared = Path(str(validation["prepared_root"]))
        initial_source = prepared / str(chain_row["initial_checkpoint"])
        checkpoint = _copy_initial_checkpoint(
            initial_source,
            checkpoint_dir / initial_source.name,
        )
    elif status.get("extension_epoch") == extension_epoch:
        _require_retry_authority(status)
        prior_attempt = status.get("job_attempt")
        if isinstance(prior_attempt, bool) or not isinstance(prior_attempt, int):
            raise ValueError("Prior job attempt is malformed")
        if prior_attempt >= 3:
            raise ValueError("Attempt four is forbidden")
        job_attempt = prior_attempt + 1
        identity = status["identity"]
        checkpoint = chain_root / str(status["latest_checkpoint"])
        verify_sha256_sidecar(checkpoint)
    else:
        if status.get("extension_epoch") != extension_epoch - 1:
            raise ValueError("Extension epochs must be consecutive")
        extension = validate_extension_authorization(
            run_root, to_extension_epoch=extension_epoch
        )
        job_attempt = 1
        prior_identity = status["identity"]
        new_target = dict(prior_identity["target"])
        new_target["extension_epoch"] = extension_epoch
        new_target["extension_authorization_sha256"] = extension[
            "authorization_sha256"
        ]
        identity = spatial_checkpoint_identity(
            target=new_target,
            chain_id=assignment.chain_id,
            chain_seed=assignment.chain_seed,
            allocation_initialization_seed=assignment.allocation_initialization_seed,
            spatial_initialization_seed=assignment.spatial_initialization_seed,
        )
        checkpoint = _rebind_extension_checkpoint(
            prior_checkpoint=chain_root / str(status["latest_checkpoint"]),
            checkpoint_dir=checkpoint_dir,
            chunk_dir=chunk_dir,
            prior_identity=prior_identity,
            new_identity=identity,
            extension_epoch=extension_epoch,
            frame=frame,
            design=design,
            prior=prior,
        )
    production_dependencies = (
        prepared_validator is validate_prepared_source_envelope
        and runtime_loader is _runtime_target
        and chain_executor is run_spatial_mcmc_chain
        and manifest.get("production_eligible") is True
        and manifest.get("builder_provenance")
        == {
            "frame_loader": "default_load_model_frame",
            "allocation_solver": "default_solve_feasible_allocation",
            "graph_preparer": "default_graph_artifacts",
            "envelope_loader": "default_reviewed_launch_envelope",
        }
        and not bounded_test_mode
    )
    attempt_payload: dict[str, Any]
    try:
        result = dict(
            chain_executor(
                frame,
                design=design,
                identity=identity,
                checkpoint_path=checkpoint,
                checkpoint_dir=checkpoint_dir,
                chunk_dir=chunk_dir,
                job_attempt=job_attempt,
                settings=FROZEN_CHAIN_SETTINGS,
                prior=prior,
                checkpoint_every=500,
                max_runtime_minutes=72 * 60,
                stop_before_time_limit_minutes=15,
            )
        )
        state = str(result["status"])
        if state not in {"completed", "checkpointed"}:
            raise ValueError("Chain executor returned an invalid terminal state")
        expected = EPOCH_CONTRACT[extension_epoch]
        if state == "completed" and (
            result["iteration"] != expected["iterations"]
            or result["saved_draws"] != expected["draws"]
            or len(result["committed_chunks"]) != expected["chunks"]
        ):
            raise ValueError("Completed chain does not satisfy the exact epoch contract")
        latest = Path(str(result["latest_checkpoint"]))
        if latest.parent.resolve() != checkpoint_dir.resolve():
            raise ValueError("Chain executor returned an out-of-root checkpoint")
        verify_sha256_sidecar(latest)
        production_executor = production_dependencies
        _write_attempt_evidence(
            chain_root,
            chain_id=assignment.chain_id,
            extension_epoch=extension_epoch,
            job_attempt=job_attempt,
            start_saved_draws=int(result.get("start_saved_draws", -1)),
            records=result.get("retained_assertion_records"),
            evidence_builder=result.get("evidence_builder"),
            production_executor=production_executor,
        )
        cumulative_evidence = _cumulative_evidence(
            chain_root,
            chain_id=assignment.chain_id,
            through_epoch=extension_epoch,
            expected_draws=int(result["saved_draws"]),
        )
        inventory = _artifact_inventory(chain_root)
        attempt_payload = {
            "schema_id": "sr_v2_spatial_chain_status/v1",
            "run_id": RUN_ID,
            "model_id": spec.model_id,
            "preparation_identity": manifest["preparation_identity"],
            "launch_envelope_sha256": manifest["launch_envelope_sha256"],
            "final_source_manifest_sha256": manifest[
                "final_source_manifest_sha256"
            ],
            "chain_id": assignment.chain_id,
            "array_index": assignment.array_index,
            "extension_epoch": extension_epoch,
            "job_attempt": job_attempt,
            "status": state,
            "iterations": int(result["iteration"]),
            "retained_draws": int(result["saved_draws"]),
            "chunks": len(result["committed_chunks"]),
            "seeds": {
                "chain_seed": assignment.chain_seed,
                "allocation_initialization_seed": assignment.allocation_initialization_seed,
                "spatial_initialization_seed": assignment.spatial_initialization_seed,
            },
            "identity": identity,
            "target_fingerprint": identity["target_fingerprint"],
            "chain_fingerprint": identity["chain_fingerprint"],
            "latest_checkpoint": latest.relative_to(chain_root).as_posix(),
            "latest_checkpoint_sha256": sha256_file(latest),
            "artifact_sha256": inventory,
            "executor_builder": (
                "exact_public_chain_loop"
                if production_executor
                else "injected_bounded_test_executor"
            ),
            "retained_assertion_evidence": cumulative_evidence,
            "failure_category": None,
            "retryable": state == "checkpointed",
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "submission_authorized": False,
        }
        _publish_status(chain_root, attempt_payload)
        return attempt_payload
    except BaseException as error:
        recovered_checkpoint, recovered = _recover_latest_valid_checkpoint(
            checkpoint_dir=checkpoint_dir,
            fallback=checkpoint,
            identity=identity,
            extension_epoch=extension_epoch,
            frame=frame,
            design=design,
            prior=prior,
            chunk_dir=chunk_dir,
        )
        progress = (
            error.progress
            if isinstance(error, SpatialChainExecutionError)
            else None
        )
        evidence_destination = (
            chain_root
            / f"evidence/epoch_{extension_epoch}/attempt_{job_attempt}"
        )
        if not evidence_destination.exists():
            start_saved = int(
                progress.get("start_saved_draws", recovered["saved_draws"])
                if isinstance(progress, Mapping)
                else recovered["saved_draws"]
            )
            progress_records = (
                progress.get("retained_assertion_records", [])
                if isinstance(progress, Mapping)
                else []
            )
            keep = int(recovered["saved_draws"]) - start_saved
            if keep < 0 or not isinstance(progress_records, list) or keep > len(progress_records):
                raise ValueError("Recoverable loop evidence does not cover its checkpoint") from error
            _write_attempt_evidence(
                chain_root,
                chain_id=assignment.chain_id,
                extension_epoch=extension_epoch,
                job_attempt=job_attempt,
                start_saved_draws=start_saved,
                records=progress_records[:keep],
                evidence_builder=(
                    progress.get("evidence_builder")
                    if isinstance(progress, Mapping)
                    else "injected_failed_executor"
                ),
                production_executor=production_dependencies,
            )
        cumulative_evidence = _cumulative_evidence(
            chain_root,
            chain_id=assignment.chain_id,
            through_epoch=extension_epoch,
            expected_draws=int(recovered["saved_draws"]),
        )
        failure_category, retryable = _failure_taxonomy(error)
        inventory = _artifact_inventory(chain_root)
        failed = {
            "schema_id": "sr_v2_spatial_chain_status/v1",
            "run_id": RUN_ID,
            "model_id": spec.model_id,
            "preparation_identity": manifest["preparation_identity"],
            "launch_envelope_sha256": manifest["launch_envelope_sha256"],
            "final_source_manifest_sha256": manifest[
                "final_source_manifest_sha256"
            ],
            "chain_id": assignment.chain_id,
            "array_index": assignment.array_index,
            "extension_epoch": extension_epoch,
            "job_attempt": job_attempt,
            "status": "failed",
            "iterations": int(recovered["iteration"]),
            "retained_draws": int(recovered["saved_draws"]),
            "chunks": len(recovered["committed_chunks"]),
            "seeds": {
                "chain_seed": assignment.chain_seed,
                "allocation_initialization_seed": assignment.allocation_initialization_seed,
                "spatial_initialization_seed": assignment.spatial_initialization_seed,
            },
            "identity": identity,
            "target_fingerprint": identity["target_fingerprint"],
            "chain_fingerprint": identity["chain_fingerprint"],
            "latest_checkpoint": recovered_checkpoint.relative_to(chain_root).as_posix(),
            "latest_checkpoint_sha256": sha256_file(recovered_checkpoint),
            "artifact_sha256": inventory,
            "failure_class": type(error).__name__,
            "failure_category": failure_category,
            "retryable": retryable,
            "executor_builder": (
                "exact_public_chain_loop"
                if production_dependencies
                else "injected_bounded_test_executor"
            ),
            "retained_assertion_evidence": cumulative_evidence,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "submission_authorized": False,
        }
        _publish_status(chain_root, failed)
        set_canonical_hold(
            root,
            reason=f"chain_failed:{type(error).__name__}",
            stage="chain",
            extension_epoch=extension_epoch,
            output_base_override=output_base_override,
        )
        raise


def benchmark_prepared_target(
    *,
    root: Path,
    output_path: Path,
    iterations: int = 2_000,
    array_index: int = 1,
    output_base_override: Path | None = None,
    prepared_validator: Callable[..., Mapping[str, Any]] = validate_prepared_source_envelope,
    runtime_loader: Callable[[Path, Mapping[str, Any]], tuple[pd.DataFrame, Any, Any]] = _runtime_target,
    chain_executor: Callable[..., Mapping[str, Any]] = run_spatial_mcmc_chain,
    chunk_committer: Callable[..., Mapping[str, Any]] = commit_spatial_draw_chunk,
    elapsed_seconds_override: float | None = None,
    peak_rss_gib_override: float | None = None,
    bounded_test_mode: bool = False,
) -> dict[str, Any]:
    """Execute and record exactly 2,000 iterations of the prepared target.

    The scientific chain namespace is never touched.  Default dependencies are
    the same public chain loop and runtime target as production; injected
    dependencies are explicitly marked bounded-test and can never satisfy the
    final gate.
    """

    validation = prepared_validator(
        root,
        config_path=ROOT / "config/sr_v2_spatial_sensitivity_execution.yaml",
        output_base_override=output_base_override,
    )
    if iterations != 2_000 or array_index not in range(1, 5):
        raise ValueError("Benchmark requires exactly 2,000 iterations on one prepared chain")
    run_root = spatial_run_root(root, output_base_override)
    canonical_output = run_root / "benchmark/benchmark_report.json"
    output_path = Path(output_path).resolve()
    if output_path != canonical_output.resolve():
        raise ValueError("Benchmark report must use the canonical run-specific path")
    frame, design, prior = runtime_loader(Path(root).resolve(), validation)
    chain_row = validation["manifest"]["chain_mapping"][array_index - 1]
    work_parent = canonical_output.parent
    work_parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".benchmark-work-", dir=work_parent))
    try:
        checkpoint_dir = work / "checkpoints"
        chunk_dir = work / "chunks"
        source = Path(str(validation["prepared_root"])) / str(
            chain_row["initial_checkpoint"]
        )
        checkpoint = _copy_initial_checkpoint(
            source, checkpoint_dir / source.name
        )
        started = time.monotonic()
        result = dict(
            chain_executor(
                frame,
                design=design,
                identity=chain_row["target_identity"],
                checkpoint_path=checkpoint,
                checkpoint_dir=checkpoint_dir,
                chunk_dir=chunk_dir,
                job_attempt=1,
                settings=FROZEN_CHAIN_SETTINGS,
                prior=prior,
                checkpoint_every=500,
                max_runtime_minutes=120,
                stop_before_time_limit_minutes=5,
                stop_requested=lambda iteration: iteration >= 2_000,
            )
        )
        if (
            result.get("status") != "checkpointed"
            or result.get("iteration") != 2_000
            or result.get("saved_draws") != 0
            or result.get("committed_chunks") != []
        ):
            raise ValueError("Benchmark did not execute the exact 2,000-iteration no-draw prefix")
        parameter_schema = list(chain_row["target_identity"]["target"]["parameter_schema"])
        draw_ids = np.arange(1, 251, dtype=np.int64)
        values = np.zeros(250 * len(parameter_schema), dtype=np.float64)
        for name, replacement in (("sigma_county", 1.0), ("phi_structured", 0.5)):
            if name in parameter_schema:
                values[np.tile(np.asarray(parameter_schema) == name, 250)] = replacement
        scalar = pd.DataFrame(
            {
                "chain_id": np.full(len(values), int(chain_row["chain_id"]), dtype=np.int64),
                "draw_id": np.repeat(draw_ids, len(parameter_schema)),
                "extension_epoch": np.zeros(len(values), dtype=np.int64),
                "parameter": parameter_schema * 250,
                "value": values,
            }
        )
        paired_root = work / "paired_chunk"
        paired_started = time.monotonic()
        paired_record = dict(
            chunk_committer(
                paired_root,
                chain_id=int(chain_row["chain_id"]),
                extension_epoch=0,
                graph=design.spatial_graph,
                parameter_schema=parameter_schema,
                chunk_id=1,
                draw_ids=draw_ids,
                scalar_draws=scalar,
                structured=np.zeros((250, len(design.spatial_graph.counties)), dtype=np.float64),
                unstructured=np.zeros((250, len(design.spatial_graph.counties)), dtype=np.float64),
            )
        )
        paired_elapsed = time.monotonic() - paired_started
        paired_bytes = sum(
            (paired_root / str(paired_record[key])).stat().st_size
            for key in ("scalar_path", "spatial_path")
        )
    finally:
        if work.exists():
            shutil.rmtree(work)
    elapsed = (
        float(elapsed_seconds_override)
        if elapsed_seconds_override is not None
        else time.monotonic() - started
    )
    if peak_rss_gib_override is None:
        try:
            import resource
        except ImportError as error:
            raise RuntimeError(
                "Peak RSS must be measured on the Linux benchmark node"
            ) from error
        # Linux ru_maxrss is KiB.  Wahab is the only production benchmark host.
        rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024**2
    else:
        rss = float(peak_rss_gib_override)
    builder = (
        "exact_prepared_public_chain"
        if (
            chain_executor is run_spatial_mcmc_chain
            and prepared_validator is validate_prepared_source_envelope
            and runtime_loader is _runtime_target
            and chunk_committer is commit_spatial_draw_chunk
            and validation["manifest"].get("production_eligible") is True
            and not bounded_test_mode
            and elapsed_seconds_override is None
            and peak_rss_gib_override is None
        )
        else "injected_bounded_test_benchmark"
    )
    if not np.isfinite(elapsed) or elapsed <= 0 or not np.isfinite(rss) or rss < 0:
        raise ValueError("Benchmark timing/RSS evidence must be finite and positive")
    projected = (elapsed / iterations) * 180_000 * 1.2 / 3_600
    passed = projected <= 65.0 and rss <= 56.0
    payload = {
        "schema_id": "sr_v2_spatial_benchmark/v1",
        "run_id": RUN_ID,
        "preparation_identity": validation["manifest"]["preparation_identity"],
        "target_fingerprint": validation["manifest"]["chain_mapping"][array_index - 1][
            "target_fingerprint"
        ],
        "launch_envelope_sha256": validation["launch_envelope_sha256"],
        "final_source_manifest_sha256": validation["final_source_manifest_sha256"],
        "builder": builder,
        "array_index": array_index,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "iterations_per_second": iterations / elapsed,
        "projection_overhead_factor": 1.2,
        "projected_hours": projected,
        "projected_hours_limit_inclusive": 65.0,
        "peak_rss_gib": rss,
        "peak_rss_gib_limit_inclusive": 56.0,
        "paired_chunk_draws": 250,
        "paired_chunk_scalar_rows": 250 * len(parameter_schema),
        "paired_chunk_bytes": paired_bytes,
        "paired_chunk_elapsed_seconds": paired_elapsed,
        "paired_chunk_mib_per_second": paired_bytes / paired_elapsed / 1024**2,
        "paired_chunk_record_sha256": hashlib.sha256(
            canonical_json_bytes(paired_record)
        ).hexdigest(),
        "paired_chunk_builder": "actual_commit_spatial_draw_chunk",
        "paired_chunk_scientific_data": False,
        "passed": passed,
        "scientific_draws_published": False,
        "submission_authorized": False,
    }
    if output_path.exists() or output_path.with_name(output_path.name + ".sha256").exists():
        raise FileExistsError("Benchmark evidence is immutable")
    atomic_json(output_path, payload)
    _write_sidecar(output_path)
    if not passed:
        set_benchmark_failure_hold(
            root,
            reason="runtime_or_memory_threshold",
            output_base_override=output_base_override,
        )
    return payload


def main() -> None:
    # This executes before argparse so malformed/missing CLI cannot leave PASS.
    set_canonical_hold(
        ROOT, reason="chain_cli_started", stage="chain", extension_epoch=None
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--array-index", required=True, type=int)
    parser.add_argument("--extension-epoch", required=True, type=int)
    args = parser.parse_args()
    result = run_chain(
        run_id=args.run_id,
        array_index=args.array_index,
        extension_epoch=args.extension_epoch,
    )
    if result["status"] == "checkpointed":
        raise SystemExit(CHECKPOINT_EXIT_CODE)


if __name__ == "__main__":
    main()
