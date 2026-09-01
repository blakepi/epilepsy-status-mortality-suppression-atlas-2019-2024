from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.constraints import assert_constraints, solve_feasible_allocation  # noqa: E402
from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.model import (  # noqa: E402
    active_prior_specification,
    crude_intercept_prior,
    initialize_theta,
    log_posterior_theta,
    make_design,
)
from bayes_constrained.sampler import SpatialMALAState  # noqa: E402
from bayes_constrained.spatial_bym2 import (  # noqa: E402
    SPATIAL_COUNTER_SCHEMA,
    build_bym2_graph,
    componentwise_center,
    frozen_graph_contract_from_execution,
    save_spatial_checkpoint,
    spatial_checkpoint_identity,
    spatial_design_schema,
    spatial_model_frame_sha256,
    spatial_parameter_schema,
    spatial_prior_schema,
)
from bayes_constrained.spatial_pipeline import (  # noqa: E402
    MODEL_ID,
    PREPARED_MANIFEST_EXACT_FIELDS,
    RUN_ID,
    atomic_json,
    canonical_json_bytes,
    canonical_sha256,
    exclusive_lock,
    load_reviewed_launch_envelope,
    load_spatial_execution_spec,
    publish_directory_no_clobber,
    recompute_component_scales,
    set_canonical_hold,
    sha256_file,
    snapshot_protected_trees,
    spatial_run_root,
    verify_hash_inventory,
    verify_sha256_sidecar,
)


_DEFAULT_ENVELOPE_LOADER = load_reviewed_launch_envelope


CONFIG_PATH = ROOT / "config" / "sr_v2_spatial_sensitivity_execution.yaml"
ADJACENCY_RELATIVE = Path(
    "outputs/scientific_reports_v2/spatial_residual_diagnostics/county_adjacency2024.txt"
)
MODEL_FRAME_RELATIVE = Path("data/processed/bayes_constrained/model_frame.parquet")


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_sidecar(path: Path) -> None:
    _write_bytes(path.with_name(path.name + ".sha256"), (sha256_file(path) + "\n").encode("ascii"))


def _graph_artifacts(
    frame: pd.DataFrame,
    *,
    root: Path,
    spec,
) -> tuple[Any, dict[str, bytes]]:
    adjacency_path = root / ADJACENCY_RELATIVE
    graph = build_bym2_graph(
        frame,
        adjacency_path,
        expected_sha256=spec.source_authorities[ADJACENCY_RELATIVE.as_posix()],
        frozen_contract=frozen_graph_contract_from_execution(
            spec.raw["graph_certificate"]
        ),
    )
    recomputed = recompute_component_scales(graph.adjacency, graph.components)
    certified_rows = {
        str(row["minimum_fips"]): str(row["scale_hex"])
        for row in spec.raw["graph_certificate"]["non_singleton_components"]
    }
    scale_rows: list[dict[str, object]] = []
    component_lines = ["component_id,minimum_fips,size,singleton,scale_hex"]
    for component_id, (component, scale) in enumerate(
        zip(graph.components, recomputed, strict=True)
    ):
        minimum_fips = graph.counties[int(component[0])]
        singleton = len(component) == 1
        scale_hex = float(scale).hex()
        if singleton:
            if scale != 0.0 or not bool(graph.singleton_mask[int(component[0])]):
                raise ValueError("Independent singleton graph certificate mismatch")
        elif certified_rows.get(minimum_fips) != scale_hex:
            raise ValueError(
                "Independent graph-scale mismatch for component "
                f"{minimum_fips}: expected {certified_rows.get(minimum_fips)}, found {scale_hex}"
            )
        scale_rows.append(
            {
                "component_id": component_id,
                "minimum_fips": minimum_fips,
                "size": len(component),
                "singleton": singleton,
                "scale_hex": scale_hex,
            }
        )
        component_lines.append(
            f"{component_id},{minimum_fips},{len(component)},"
            f"{'true' if singleton else 'false'},{scale_hex}"
        )
    upper = np.transpose(np.triu(graph.adjacency.toarray(), k=1).nonzero())
    edges = sorted(
        (graph.counties[int(left)], graph.counties[int(right)])
        for left, right in upper
    )
    county_bytes = "".join(f"{county}\n" for county in graph.counties).encode("utf-8")
    edge_bytes = "".join(f"{left}|{right}\n" for left, right in edges).encode("utf-8")
    certificate = {
        "schema_id": "sr_v2_spatial_graph_contract/v1",
        "run_id": RUN_ID,
        "nodes": len(graph.counties),
        "undirected_edges": len(edges),
        "components": len(graph.components),
        "nonisolated_nodes": int((~graph.singleton_mask).sum()),
        "county_order_sha256": __import__("hashlib").sha256(county_bytes).hexdigest(),
        "edge_list_sha256": __import__("hashlib").sha256(edge_bytes).hexdigest(),
        "component_scales": scale_rows,
        "graph_contract_sha256": graph.contract_sha256,
    }
    expected = spec.raw["graph_certificate"]
    if (
        certificate["nodes"] != expected["nodes"]
        or certificate["undirected_edges"] != expected["undirected_edges"]
        or certificate["components"] != expected["components"]
        or certificate["nonisolated_nodes"] != expected["nonisolated_nodes"]
        or certificate["county_order_sha256"] != expected["county_order_sha256"]
        or certificate["edge_list_sha256"] != expected["edge_list_sha256"]
    ):
        raise ValueError("Independently reconstructed graph certificate mismatch")
    return graph, {
        "graph/county_order.txt": county_bytes,
        "graph/edge_list.txt": edge_bytes,
        "graph/components.csv": ("\n".join(component_lines) + "\n").encode("utf-8"),
        "graph/scale_certificate.json": canonical_json_bytes(
            {
                "schema_id": "sr_v2_spatial_scale_certificate/v1",
                "scales": scale_rows,
            }
        ),
        "graph/graph_contract.json": canonical_json_bytes(certificate),
    }


def _fresh_spatial_theta(
    frame: pd.DataFrame,
    allocation: np.ndarray,
    design,
    *,
    spatial_seed: int,
):
    theta = initialize_theta(frame, allocation, design)
    rng = np.random.default_rng(spatial_seed)
    theta.spatial_structured = componentwise_center(
        rng.normal(0.0, 0.05, size=len(design.spatial_graph.counties)),
        design.spatial_graph,
    )
    theta.spatial_unstructured = rng.normal(
        0.0, 0.05, size=len(design.spatial_graph.counties)
    ).astype(np.float64)
    theta.log_sigma_county = float(np.log(0.2) + rng.normal(0.0, 0.02))
    theta.logit_phi_structured = float(rng.normal(0.0, 0.05))
    return theta


def _epoch_zero_target(
    frame: pd.DataFrame,
    *,
    design: Any,
    config_sha256: str,
    input_manifest_sha256: str,
    final_source_manifest_sha256: str,
    graph_contract_sha256: str,
    prior: Any,
    intercept_mean: float,
) -> dict[str, object]:
    """Build the exact prepare-side epoch-zero target for independent matching."""

    return {
        "schema_id": "sr_v2_spatial_target/v1",
        "run_id": RUN_ID,
        "model_id": MODEL_ID,
        "config_sha256": config_sha256,
        "input_manifest_sha256": input_manifest_sha256,
        "source_manifest_sha256": final_source_manifest_sha256,
        "model_frame_semantic_sha256": spatial_model_frame_sha256(frame),
        "graph_contract_sha256": graph_contract_sha256,
        "likelihood": "negative_binomial_2",
        "prior": spatial_prior_schema(prior),
        "intercept_mean_rule": "crude_national_log_rate",
        "intercept_mean_float_hex": float(intercept_mean).hex(),
        "design_schema": spatial_design_schema(design),
        "parameter_schema": spatial_parameter_schema(design),
        "extension_epoch": 0,
        "extension_authorization_sha256": "0" * 64,
    }


def _verify_existing(prepared_root: Path, expected: dict[str, object]) -> dict[str, object]:
    manifest_path = prepared_root / "prepared_run_manifest.json"
    verify_sha256_sidecar(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != PREPARED_MANIFEST_EXACT_FIELDS:
        raise ValueError("Existing spatial preparation manifest schema changed")
    inventory = manifest.get("prepared_artifact_sha256")
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("Existing spatial preparation lacks an artifact inventory")
    verify_hash_inventory(
        prepared_root,
        inventory,
        exact_files=True,
        allowed_files=(
            "prepared_run_manifest.json",
            "prepared_run_manifest.json.sha256",
        ),
    )
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"Existing spatial preparation identity mismatch: {key}")
    return manifest


def prepare(
    *,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    launch_envelope_path: Path | None,
    output_base_override: Path | None = None,
    frame_loader: Callable[[], pd.DataFrame] = load_model_frame,
    allocation_solver: Callable[..., np.ndarray] = solve_feasible_allocation,
    graph_preparer: Callable[..., tuple[Any, dict[str, bytes]]] = _graph_artifacts,
    envelope_loader: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, object]:
    root = Path(root).resolve()
    run_root = spatial_run_root(root, output_base_override)
    set_canonical_hold(
        root,
        reason="preparation_not_verified",
        stage="prepare",
        extension_epoch=0,
        output_base_override=output_base_override,
    )
    try:
        spec = load_spatial_execution_spec(config_path)
        if launch_envelope_path is None:
            raise FileNotFoundError(
                "Reviewed external launch envelope is required before preparation"
            )
        verify_hash_inventory(root, spec.source_authorities)
        active_envelope_loader = (
            load_reviewed_launch_envelope
            if envelope_loader is None
            else envelope_loader
        )
        provenance = active_envelope_loader(root, launch_envelope_path)
        primary_gate = json.loads(
            (root / "outputs/scientific_reports_v2/production_8chain/production_gate.json").read_text(
                encoding="utf-8"
            )
        )
        if primary_gate.get("passed") is not True:
            raise ValueError("Frozen corrected primary gate is not passed")
        residual = json.loads(
            (root / "outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json").read_text(
                encoding="utf-8"
            )
        )
        if residual.get("recommended_action") != "run_spatial_random_effect_sensitivity":
            raise ValueError("Frozen residual diagnostic does not require the BYM2 sensitivity")
        config_hash = sha256_file(config_path)
        builder_provenance = {
            "frame_loader": (
                "default_load_model_frame"
                if frame_loader is load_model_frame
                else "injected_test_only"
            ),
            "allocation_solver": (
                "default_solve_feasible_allocation"
                if allocation_solver is solve_feasible_allocation
                else "injected_test_only"
            ),
            "graph_preparer": (
                "default_graph_artifacts"
                if graph_preparer is _graph_artifacts
                else "injected_test_only"
            ),
            "envelope_loader": (
                "default_reviewed_launch_envelope"
                if active_envelope_loader is _DEFAULT_ENVELOPE_LOADER
                else "injected_test_only"
            ),
        }
        production_eligible = all(
            not value.endswith("test_only")
            for value in builder_provenance.values()
        )
        expected_identity = {
            "schema_id": "sr_v2_spatial_prepared_run/v1",
            "run_id": RUN_ID,
            "model_id": MODEL_ID,
            "operational_config_sha256": config_hash,
            "launch_envelope_sha256": provenance["launch_envelope_sha256"],
            "final_source_manifest_sha256": provenance[
                "final_source_manifest_sha256"
            ],
            "launch_commit": provenance["launch_commit"],
            "bundle_sha256": provenance["bundle_sha256"],
            "joint_regression_evidence_sha256": provenance[
                "joint_regression_evidence_sha256"
            ],
            "production_eligible": production_eligible,
            "builder_provenance": builder_provenance,
        }
        prepared_root = run_root / "prepared"
        run_root.mkdir(parents=True, exist_ok=True)
        with exclusive_lock(run_root / ".prepare.lock"):
            if os.path.lexists(prepared_root):
                return _verify_existing(prepared_root, expected_identity)
            staging = Path(
                tempfile.mkdtemp(prefix=".prepared-", dir=run_root)
            )
            try:
                envelope_copy = staging / "provenance/launch_envelope.json"
                envelope_copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(launch_envelope_path, envelope_copy)
                shutil.copyfile(
                    Path(launch_envelope_path).with_name(
                        Path(launch_envelope_path).name + ".sha256"
                    ),
                    envelope_copy.with_name(envelope_copy.name + ".sha256"),
                )
                source_manifest_path = staging / "provenance/final_source_manifest.json"
                _write_bytes(
                    source_manifest_path,
                    canonical_json_bytes(provenance["source_manifest"]),
                )
                _write_sidecar(source_manifest_path)
                config_copy = staging / "config/sr_v2_spatial_sensitivity_execution.yaml"
                config_copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(config_path, config_copy)
                protected_tree_manifest = snapshot_protected_trees(root)
                protected_tree_path = (
                    staging / "provenance/protected_tree_manifest.json"
                )
                atomic_json(protected_tree_path, protected_tree_manifest)
                _write_sidecar(protected_tree_path)
                frame = frame_loader()
                frame_path = staging / "inputs/model_frame.parquet"
                frame_path.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(frame_path, index=False)
                graph, graph_payloads = graph_preparer(
                    frame, root=root, spec=spec
                )
                for relative, payload in graph_payloads.items():
                    _write_bytes(staging / relative, payload)
                design = make_design(frame, spatial_graph=graph)
                prior = active_prior_specification()
                intercept_mean = crude_intercept_prior(frame)
                parameter_schema = spatial_parameter_schema(design)
                if len(parameter_schema) != 71 and len(graph.counties) == 3142:
                    raise ValueError("Production spatial parameter schema must contain 71 rows")
                graph_contract_path = staging / "graph/graph_contract.json"
                graph_contract_payload = json.loads(
                    graph_contract_path.read_text(encoding="utf-8")
                )
                input_manifest = {
                    "schema_id": "sr_v2_spatial_input_manifest/v1",
                    "run_id": RUN_ID,
                    "operational_config_sha256": config_hash,
                    "source_authorities": spec.source_authorities,
                    "launch_envelope_sha256": provenance["launch_envelope_sha256"],
                    "final_source_manifest_sha256": provenance[
                        "final_source_manifest_sha256"
                    ],
                    "launch_commit": provenance["launch_commit"],
                    "bundle_sha256": provenance["bundle_sha256"],
                    "joint_regression_evidence_sha256": provenance[
                        "joint_regression_evidence_sha256"
                    ],
                    "source_model_frame_sha256": spec.source_authorities[
                        MODEL_FRAME_RELATIVE.as_posix()
                    ],
                    "prepared_model_frame_sha256": sha256_file(frame_path),
                    "model_frame_semantic_sha256": spatial_model_frame_sha256(frame),
                    "graph_contract_sha256": graph.contract_sha256,
                    "graph_artifact_sha256": {
                        relative: __import__("hashlib").sha256(payload).hexdigest()
                        for relative, payload in sorted(graph_payloads.items())
                    },
                }
                input_manifest_path = staging / "input_manifest.json"
                atomic_json(input_manifest_path, input_manifest)
                _write_sidecar(input_manifest_path)
                input_manifest_hash = sha256_file(input_manifest_path)
                chain_rows: list[dict[str, object]] = []
                allocation_hashes: set[str] = set()
                chain_fingerprints: set[str] = set()
                for assignment in spec.chain_map:
                    allocation = allocation_solver(
                        frame,
                        seed=assignment.allocation_initialization_seed,
                        objective="random",
                        time_limit_seconds=900,
                    )
                    allocation = np.asarray(allocation, dtype=np.int64)
                    assert_constraints(
                        allocation,
                        frame,
                        label=f"spatial_chain{assignment.chain_id}_fresh_start",
                    )
                    allocation_path = (
                        staging
                        / f"initializations/initial_allocation_chain_{assignment.chain_id:02d}.parquet"
                    )
                    allocation_path.parent.mkdir(parents=True, exist_ok=True)
                    allocation_frame = frame[["county_fips", "year", "q002_count_status"]].copy()
                    allocation_frame["latent_count"] = allocation
                    allocation_frame.to_parquet(allocation_path, index=False)
                    allocation_hash = sha256_file(allocation_path)
                    if allocation_hash in allocation_hashes:
                        raise ValueError(
                            "All four fresh feasible allocations must be byte-distinct"
                        )
                    allocation_hashes.add(allocation_hash)
                    theta = _fresh_spatial_theta(
                        frame,
                        allocation,
                        design,
                        spatial_seed=assignment.spatial_initialization_seed,
                    )
                    target = _epoch_zero_target(
                        frame,
                        design=design,
                        config_sha256=config_hash,
                        input_manifest_sha256=input_manifest_hash,
                        final_source_manifest_sha256=provenance[
                            "final_source_manifest_sha256"
                        ],
                        graph_contract_sha256=graph.contract_sha256,
                        prior=prior,
                        intercept_mean=intercept_mean,
                    )
                    if target["parameter_schema"] != parameter_schema:
                        raise AssertionError("Prepare-side target parameter schema drift")
                    identity = spatial_checkpoint_identity(
                        target=target,
                        chain_id=assignment.chain_id,
                        chain_seed=assignment.chain_seed,
                        allocation_initialization_seed=assignment.allocation_initialization_seed,
                        spatial_initialization_seed=assignment.spatial_initialization_seed,
                    )
                    if identity["chain_fingerprint"] in chain_fingerprints:
                        raise ValueError("All four chain fingerprints must be distinct")
                    chain_fingerprints.add(identity["chain_fingerprint"])
                    checkpoint_path = (
                        staging
                        / f"initial_checkpoints/chain_{assignment.chain_id:02d}/"
                        "checkpoint_epoch_0_attempt_1_iter_000000000.json"
                    )
                    counters = {name: 0 for name in SPATIAL_COUNTER_SCHEMA}
                    current_target = log_posterior_theta(
                        allocation,
                        theta,
                        design,
                        intercept_mean=intercept_mean,
                        prior=prior,
                    )
                    if not np.isfinite(current_target):
                        raise ValueError("Fresh spatial initialization has nonfinite target")
                    save_spatial_checkpoint(
                        checkpoint_path,
                        identity=identity,
                        extension_epoch=0,
                        job_attempt=1,
                        y=allocation,
                        theta=theta,
                        rng=np.random.default_rng(assignment.chain_seed),
                        frame=frame,
                        design=design,
                        intercept_mean=intercept_mean,
                        prior=prior,
                        iteration=0,
                        saved_draws=0,
                        current_target=current_target,
                        accepted=counters,
                        proposed=counters,
                        committed_chunks=[],
                        pending_scalar=pd.DataFrame(),
                        pending_structured=np.empty((0, len(graph.counties)), dtype=np.float64),
                        pending_unstructured=np.empty((0, len(graph.counties)), dtype=np.float64),
                        adaptation_state=SpatialMALAState().to_dict(),
                        next_draw_id=1,
                        output_positions={"scalar_rows": 0, "spatial_draws": 0},
                    )
                    chain_rows.append(
                        {
                            "array_index": assignment.array_index,
                            "chain_id": assignment.chain_id,
                            "chain_seed": assignment.chain_seed,
                            "allocation_initialization_seed": assignment.allocation_initialization_seed,
                            "spatial_initialization_seed": assignment.spatial_initialization_seed,
                            "target_identity": identity,
                            "target_fingerprint": identity["target_fingerprint"],
                            "chain_fingerprint": identity["chain_fingerprint"],
                            "initial_allocation": allocation_path.relative_to(staging).as_posix(),
                            "initial_allocation_sha256": allocation_hash,
                            "initial_checkpoint": checkpoint_path.relative_to(staging).as_posix(),
                            "initial_checkpoint_sha256": sha256_file(checkpoint_path),
                        }
                    )
                artifact_hashes: dict[str, str] = {}
                for path in staging.rglob("*"):
                    if path.is_symlink():
                        raise ValueError("Prepared spatial artifacts must not contain symlinks")
                    if path.is_file():
                        artifact_hashes[path.relative_to(staging).as_posix()] = sha256_file(path)
                preparation_identity = canonical_sha256(
                    {
                        **expected_identity,
                        "input_manifest_sha256": input_manifest_hash,
                        "graph_contract_sha256": graph.contract_sha256,
                        "chain_fingerprints": [row["chain_fingerprint"] for row in chain_rows],
                    }
                )
                manifest = {
                    **expected_identity,
                    "preparation_identity": preparation_identity,
                    "generated_utc": datetime.now(timezone.utc).isoformat(),
                    "status": "prepared_not_run",
                    "input_manifest": "input_manifest.json",
                    "input_manifest_sha256": input_manifest_hash,
                    "source_authorities": spec.source_authorities,
                    "graph_contract": graph_contract_payload,
                    "graph_contract_sha256": graph.contract_sha256,
                    "model_frame": "inputs/model_frame.parquet",
                    "model_frame_sha256": sha256_file(frame_path),
                    "model_frame_semantic_sha256": spatial_model_frame_sha256(frame),
                    "parameter_schema": parameter_schema,
                    "protected_tree_manifest": (
                        "provenance/protected_tree_manifest.json"
                    ),
                    "protected_tree_manifest_sha256": sha256_file(
                        protected_tree_path
                    ),
                    "chain_mapping": chain_rows,
                    "prepared_artifact_sha256": dict(sorted(artifact_hashes.items())),
                    "interpretation_boundary": spec.raw["model"]["interpretation_boundary"],
                    "submission_authorized": False,
                }
                if set(manifest) != PREPARED_MANIFEST_EXACT_FIELDS:
                    raise AssertionError("Prepared manifest implementation/schema drift")
                manifest_path = staging / "prepared_run_manifest.json"
                atomic_json(manifest_path, manifest)
                _write_sidecar(manifest_path)
                publish_directory_no_clobber(
                    staging,
                    prepared_root,
                    commit_marker="prepared_run_manifest.json.sha256",
                )
                set_canonical_hold(
                    root,
                    reason="prepared_not_run",
                    stage="prepare",
                    extension_epoch=0,
                    output_base_override=output_base_override,
                )
                return manifest
            except BaseException:
                if staging.exists():
                    shutil.rmtree(staging)
                raise
    except BaseException as error:
        set_canonical_hold(
            root,
            reason=f"prepare_failed:{type(error).__name__}",
            stage="prepare",
            extension_epoch=0,
            output_base_override=output_base_override,
        )
        raise


def main() -> None:
    set_canonical_hold(
        ROOT,
        reason="prepare_cli_started",
        stage="prepare",
        extension_epoch=0,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-envelope", required=True)
    args = parser.parse_args()
    prepare(launch_envelope_path=Path(args.launch_envelope))


if __name__ == "__main__":
    main()
