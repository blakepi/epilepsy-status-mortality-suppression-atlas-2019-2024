from __future__ import annotations

import csv
import ast
import importlib.util
import io
import json
from pathlib import Path
import sys
import hashlib
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CONFIG_PATH = ROOT / "config" / "sr_v2_spatial_sensitivity_execution.yaml"
PLAN_PATH = ROOT / "docs" / "superpowers" / "plans" / "2026-08-18-sr-v2-spatial-bym2.md"

COMPARISON_ROWS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
    "z_pct_age65",
    "z_pct_male",
]


def _load_script(filename: str, module_name: str):
    path = ROOT / "scripts" / filename
    assert path.is_file(), f"missing executable pipeline script: {filename}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _adjacency_payload(edges: list[tuple[str, str]], counties: list[str]) -> bytes:
    rows = ["County Name|County GEOID|Neighbor Name|Neighbor GEOID"]
    rows.extend(f"{county}|{county}|{county}|{county}" for county in counties)
    for left, right in edges:
        rows.extend((f"{left}|{left}|{right}|{right}", f"{right}|{right}|{left}|{left}"))
    return ("\n".join(rows) + "\n").encode("utf-8")


def _tiny_spatial_runtime(tmp_path: Path):
    import hashlib

    from bayes_constrained.model import (
        crude_intercept_prior,
        initialize_theta,
        log_posterior_theta,
        make_design,
    )
    from bayes_constrained.spatial_bym2 import (
        build_bym2_graph,
        SPATIAL_COUNTER_SCHEMA,
        save_spatial_checkpoint,
        spatial_checkpoint_identity,
        spatial_design_schema,
        spatial_model_frame_sha256,
        spatial_parameter_schema,
        spatial_prior_schema,
    )
    from bayes_constrained.sampler import SpatialMALAState

    tmp_path.mkdir(parents=True, exist_ok=True)
    counties = ["01001", "01003", "01005"]
    payload = _adjacency_payload(
        [("01001", "01003"), ("01003", "01005")], counties
    )
    adjacency = tmp_path / "adjacency.txt"
    adjacency.write_bytes(payload)
    rows: list[dict[str, object]] = []
    counts = {
        ("01001", "2019"): 1,
        ("01001", "2020"): 2,
        ("01003", "2019"): 2,
        ("01003", "2020"): 1,
        ("01005", "2019"): 1,
        ("01005", "2020"): 1,
    }
    rurality = {
        "01001": "metro_large",
        "01003": "metro_other",
        "01005": "nonmetro_adjacent",
    }
    for county in counties:
        period_total = sum(counts[(county, year)] for year in ("2019", "2020"))
        for year in ("2019", "2020"):
            rows.append(
                {
                    "county_fips": county,
                    "state_fips": "01",
                    "year": year,
                    "population": 1000.0,
                    "q002_count_status": "suppressed_1_9",
                    "q002_lower": 0,
                    "q002_upper": 5,
                    "q001_period_lower": 0,
                    "q001_period_upper": 10,
                    "q003_national_year_total": 4,
                    "q004_state_year_total": 4,
                    "primary_rurality": rurality[county],
                    "svi_quartile": "Q1_lowest",
                    "z_pct_age65": 0.0,
                    "z_pct_male": 0.0,
                    "latent_count": counts[(county, year)],
                    "period_total": period_total,
                }
            )
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = int(frame["latent_count"].sum())
    graph = build_bym2_graph(
        frame,
        adjacency,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )
    design = make_design(frame, spatial_graph=graph)
    y = frame["latent_count"].to_numpy(dtype=np.int64)
    theta = initialize_theta(frame, y, design)
    intercept_mean = crude_intercept_prior(frame)
    target = {
        "schema_id": "sr_v2_spatial_target/v1",
        "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
        "model_id": "sr-v2-primary-nb2-bym2-v1",
        "config_sha256": "1" * 64,
        "input_manifest_sha256": "2" * 64,
        "source_manifest_sha256": "3" * 64,
        "model_frame_semantic_sha256": spatial_model_frame_sha256(frame),
        "graph_contract_sha256": graph.contract_sha256,
        "likelihood": "negative_binomial_2",
        "prior": spatial_prior_schema(),
        "intercept_mean_rule": "crude_national_log_rate",
        "intercept_mean_float_hex": float(intercept_mean).hex(),
        "design_schema": spatial_design_schema(design),
        "parameter_schema": spatial_parameter_schema(design),
        "extension_epoch": 0,
        "extension_authorization_sha256": "0" * 64,
    }
    identity = spatial_checkpoint_identity(
        target=target,
        chain_id=1,
        chain_seed=74291,
        allocation_initialization_seed=74251,
        spatial_initialization_seed=74261,
    )
    counters = {name: 0 for name in SPATIAL_COUNTER_SCHEMA}
    checkpoint_dir = tmp_path / "checkpoints"
    chunk_dir = tmp_path / "chunks"
    initial = checkpoint_dir / "checkpoint_epoch_0_attempt_1_iter_000000000.json"
    save_spatial_checkpoint(
        initial,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=np.random.default_rng(74291),
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        iteration=0,
        saved_draws=0,
        current_target=log_posterior_theta(
            y, theta, design, intercept_mean=intercept_mean
        ),
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
    return frame, design, identity, initial, checkpoint_dir, chunk_dir


def test_comparison_contract_freezes_scales_signed_changes_and_lf_bytes() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    comparison = config["comparison"]
    assert comparison["rows"] == COMPARISON_ROWS
    assert comparison["scale_by_row"] == {
        **{row: "incidence_rate_ratio" for row in COMPARISON_ROWS[:6]},
        "z_pct_age65": "standardized_log_rate_coefficient",
        "z_pct_male": "standardized_log_rate_coefficient",
    }
    assert comparison["spatial_draw_transform"] == {
        "incidence_rate_ratio": "draw_wise_exp_then_summarize",
        "standardized_log_rate_coefficient": "identity_then_summarize",
    }
    assert comparison["absolute_change"] == "spatial_mean_minus_primary_mean"
    assert comparison["relative_change"] == (
        "absolute_change_divided_by_abs_primary_mean_fail_if_zero_or_nonfinite"
    )
    assert comparison["interval_overlap"] == (
        "max_lower_less_than_or_equal_to_min_upper_closed_intervals"
    )
    assert comparison["serialization"] == {
        "encoding": "utf-8",
        "delimiter": ",",
        "line_ending": "LF",
        "terminating_newline": True,
        "float_format": ".17g",
        "boolean_format": "lowercase_true_false",
        "header_order": comparison["fields"],
        "candidate_verifier_final_bytes": "byte_identical",
    }
    plan = PLAN_PATH.read_text(encoding="utf-8")
    assert "draw-wise `exp(beta)`" in plan
    assert "signed `spatial_mean - primary_mean`" in plan
    assert "Python `.17g`" in plan


def _write_reviewed_envelope(root: Path, envelope: Path) -> None:
    from bayes_constrained.spatial_pipeline import (
        SPATIAL_FINAL_SOURCE_FILES,
        canonical_sha256,
    )

    sources: dict[str, str] = {}
    for relative in SPATIAL_FINAL_SOURCE_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((relative + "\n").encode("utf-8"))
        sources[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = root / "evidence" / "joint-regression.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text('{"passed":true}\n', encoding="utf-8", newline="\n")
    source_manifest = {
        "schema_id": "sr_v2_robustness_final_source_manifest/v1",
        "status": "reviewed_final",
        "joint_regression_passed": True,
        "source_hash_mode": "raw_bytes",
        "sources": sources,
        "joint_regression_evidence": evidence.relative_to(root).as_posix(),
        "joint_regression_evidence_sha256": hashlib.sha256(
            evidence.read_bytes()
        ).hexdigest(),
    }
    payload = {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "status": "reviewed_final",
        "clean_worktree": True,
        "launch_commit": "a" * 40,
        "bundle_sha256": "b" * 64,
        "source_manifest": source_manifest,
        "source_manifest_sha256": canonical_sha256(source_manifest),
    }
    envelope.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    envelope.with_name(envelope.name + ".sha256").write_text(
        hashlib.sha256(envelope.read_bytes()).hexdigest() + "\n",
        encoding="ascii",
        newline="\n",
    )


def test_external_union_envelope_is_frozen_verified_and_never_self_certified(
    tmp_path: Path,
) -> None:
    from bayes_constrained.spatial_pipeline import (
        SPATIAL_FINAL_SOURCE_FILES,
        canonical_sha256,
        load_reviewed_launch_envelope,
    )

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["launch_envelope"] == {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "required_status": "reviewed_final",
        "requires_clean_worktree": True,
    }
    assert config["final_source_manifest"] == {
        "schema_id": "sr_v2_robustness_final_source_manifest/v1",
        "required_status": "reviewed_final",
        "source_hash_mode": "raw_bytes",
        "required_sources": list(SPATIAL_FINAL_SOURCE_FILES),
    }
    envelope = tmp_path / "reviewed-envelope.json"
    with pytest.raises(FileNotFoundError, match="external.*envelope"):
        load_reviewed_launch_envelope(tmp_path, envelope)
    _write_reviewed_envelope(tmp_path, envelope)
    loaded = load_reviewed_launch_envelope(tmp_path, envelope)
    assert loaded["launch_envelope_sha256"] == hashlib.sha256(
        envelope.read_bytes()
    ).hexdigest()
    assert loaded["final_source_manifest_sha256"] == canonical_sha256(
        loaded["source_manifest"]
    )
    assert loaded["launch_commit"] == "a" * 40
    assert loaded["bundle_sha256"] == "b" * 64
    tampered = tmp_path / SPATIAL_FINAL_SOURCE_FILES[0]
    tampered.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source SHA-256"):
        load_reviewed_launch_envelope(tmp_path, envelope)


def test_isolated_verifier_freezes_union_provenance_and_preparation_identity(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_frozen_provenance",
    )
    config = verifier._load_config(CONFIG_PATH)
    assert tuple(config["final_source_manifest"]["required_sources"]) == (
        verifier.REQUIRED_SOURCE_PATHS
    )
    assert len(verifier.REQUIRED_SOURCE_PATHS) == 24

    envelope_path = tmp_path / "reviewed-envelope.json"
    _write_reviewed_envelope(tmp_path, envelope_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope_sha = hashlib.sha256(envelope_path.read_bytes()).hexdigest()
    source_manifest = envelope["source_manifest"]
    prepared = {
        "operational_config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "launch_envelope_sha256": envelope_sha,
        "final_source_manifest_sha256": verifier._canonical_sha(source_manifest),
        "launch_commit": envelope["launch_commit"],
        "bundle_sha256": envelope["bundle_sha256"],
        "joint_regression_evidence_sha256": source_manifest[
            "joint_regression_evidence_sha256"
        ],
        "input_manifest_sha256": "1" * 64,
        "graph_contract_sha256": "2" * 64,
    }
    verified_source, verified_inventory = verifier._validate_launch_provenance(
        envelope,
        envelope_hash=envelope_sha,
        manifest=prepared,
        required_sources=verifier.REQUIRED_SOURCE_PATHS,
    )
    assert verified_source == source_manifest
    assert set(verifier.REQUIRED_SOURCE_PATHS).issubset(verified_inventory)

    omitted = json.loads(json.dumps(envelope))
    omitted["source_manifest"]["sources"].pop(verifier.REQUIRED_SOURCE_PATHS[-1])
    omitted["source_manifest_sha256"] = verifier._canonical_sha(
        omitted["source_manifest"]
    )
    with pytest.raises(ValueError, match="omits required sources"):
        verifier._validate_launch_provenance(
            omitted,
            envelope_hash=envelope_sha,
            manifest={
                **prepared,
                "final_source_manifest_sha256": omitted["source_manifest_sha256"],
            },
            required_sources=verifier.REQUIRED_SOURCE_PATHS,
        )

    for field, wrong in (
        ("launch_commit", "f" * 40),
        ("bundle_sha256", "e" * 64),
        ("joint_regression_evidence_sha256", "d" * 64),
    ):
        forged_prepared = {**prepared, field: wrong}
        with pytest.raises(ValueError, match="provenance mismatch"):
            verifier._validate_launch_provenance(
                envelope,
                envelope_hash=envelope_sha,
                manifest=forged_prepared,
                required_sources=verifier.REQUIRED_SOURCE_PATHS,
            )

    mapping = [{"chain_fingerprint": str(chain) * 64} for chain in range(1, 5)]
    prepared["preparation_identity"] = verifier._expected_preparation_identity(
        prepared, mapping
    )
    assert verifier._validate_preparation_identity(prepared, mapping) == prepared[
        "preparation_identity"
    ]
    with pytest.raises(ValueError, match="preparation_identity"):
        verifier._validate_preparation_identity(
            {**prepared, "preparation_identity": "f" * 64}, mapping
        )
    path_manifest = {
        "input_manifest": "input_manifest.json",
        "model_frame": "inputs/model_frame.parquet",
        "protected_tree_manifest": "provenance/protected_tree_manifest.json",
        "chain_mapping": [
            {
                "initial_allocation": (
                    f"initializations/initial_allocation_chain_{chain_id:02d}.parquet"
                ),
                "initial_checkpoint": (
                    f"initial_checkpoints/chain_{chain_id:02d}/"
                    "checkpoint_epoch_0_attempt_1_iter_000000000.json"
                ),
            }
            for chain_id in range(1, 5)
        ],
    }
    verifier._validate_prepared_artifact_paths(path_manifest)
    renamed_manifest = json.loads(json.dumps(path_manifest))
    renamed_manifest["chain_mapping"][0]["initial_checkpoint"] = (
        "initial_checkpoints/chain_01/renamed-but-resigned.json"
    )
    with pytest.raises(ValueError, match="generator-exact"):
        verifier._validate_prepared_artifact_paths(renamed_manifest)
    status = {
        "job_attempt": 2,
        "latest_checkpoint": (
            "checkpoints/checkpoint_epoch_1_attempt_2_iter_000270000.json"
        ),
    }
    assert verifier._validate_terminal_checkpoint_path(
        status, epoch=1, iteration=270_000
    ) == status["latest_checkpoint"]
    with pytest.raises(ValueError, match="generator-exact"):
        verifier._validate_terminal_checkpoint_path(
            {**status, "latest_checkpoint": "checkpoints/resigned.json"},
            epoch=1,
            iteration=270_000,
        )


def test_isolated_verifier_rejects_resigned_sparse_target_wrong_seed_and_checkpoint(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_frozen_target_checkpoint",
    )
    frame, design, identity, initial, _, _ = _tiny_spatial_runtime(
        tmp_path / "runtime"
    )
    seeds = {
        "chain_seed": 74291,
        "allocation_initialization_seed": 74251,
        "spatial_initialization_seed": 74261,
    }

    def resign(value: dict[str, object]) -> dict[str, object]:
        result = json.loads(json.dumps(value))
        result["target_fingerprint"] = verifier._canonical_sha(result["target"])
        result["chain"]["target_fingerprint"] = result["target_fingerprint"]
        result["chain_fingerprint"] = verifier._canonical_sha(result["chain"])
        return result

    verifier._validate_target_identity(
        identity,
        expected_target=identity["target"],
        chain_id=1,
        seeds=seeds,
    )
    for mutation in ("missing", "extra"):
        forged = json.loads(json.dumps(identity))
        if mutation == "missing":
            forged["target"].pop("prior")
        else:
            forged["target"]["unexpected"] = "coherently resigned"
        with pytest.raises(ValueError, match="target exact field/value"):
            verifier._validate_target_identity(
                resign(forged),
                expected_target=identity["target"],
                chain_id=1,
                seeds=seeds,
            )
    wrong_seed = json.loads(json.dumps(identity))
    wrong_seed["chain"]["chain_seed"] = 99999
    with pytest.raises(ValueError, match="seed/fingerprint"):
        verifier._validate_target_identity(
            resign(wrong_seed),
            expected_target=identity["target"],
            chain_id=1,
            seeds=seeds,
        )
    bool_target = json.loads(json.dumps(identity))
    bool_target["target"]["extension_epoch"] = False
    with pytest.raises(ValueError, match="target exact field/value"):
        verifier._validate_target_identity(
            resign(bool_target),
            expected_target=identity["target"],
            chain_id=1,
            seeds=seeds,
        )
    bool_chain = json.loads(json.dumps(identity))
    bool_chain["chain"]["chain_id"] = True
    with pytest.raises(ValueError, match="seed/fingerprint"):
        verifier._validate_target_identity(
            resign(bool_chain),
            expected_target=identity["target"],
            chain_id=1,
            seeds=seeds,
        )

    checkpoint = verifier._load_canonical_checkpoint(initial)
    verifier._validate_checkpoint_payload(
        checkpoint,
        identity=identity,
        seeds=seeds,
        expected_epoch=0,
        expected_attempt=1,
        expected_iteration=0,
        expected_draws=0,
        expected_chunks=0,
        row_count=len(frame),
        county_count=len(design.spatial_graph.counties),
        labels=design.spatial_graph.component_id,
        expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
        count_moves_per_iteration=1,
        blocked_refresh_frequency=25,
        blocked_refresh_attempts=12,
    )

    def publish_resigned_checkpoint(
        name: str, payload: dict[str, object]
    ) -> Path:
        path = tmp_path / f"{name}.json"
        raw = verifier._canonical_bytes(payload)
        path.write_bytes(raw)
        path.with_name(path.name + ".sha256").write_text(
            hashlib.sha256(raw).hexdigest() + "\n", encoding="ascii", newline="\n"
        )
        return path

    mutations: list[tuple[str, dict[str, object], str]] = []
    missing = json.loads(json.dumps(checkpoint))
    missing.pop("current_target")
    mutations.append(("missing", missing, "exact v2 schema"))
    extra = json.loads(json.dumps(checkpoint))
    extra["unexpected"] = True
    mutations.append(("extra", extra, "exact v2 schema"))
    wrong_checkpoint_seed = json.loads(json.dumps(checkpoint))
    wrong_checkpoint_seed["seeds"]["chain_seed"] = 99999
    mutations.append(("wrong-seed", wrong_checkpoint_seed, "identity/seed/progress"))
    for name, payload, message in mutations:
        path = publish_resigned_checkpoint(name, payload)
        loaded = verifier._load_canonical_checkpoint(path)
        with pytest.raises(ValueError, match=message):
            verifier._validate_checkpoint_payload(
                loaded,
                identity=identity,
                seeds=seeds,
                expected_epoch=0,
                expected_attempt=1,
                expected_iteration=0,
                expected_draws=0,
                expected_chunks=0,
                row_count=len(frame),
                county_count=len(design.spatial_graph.counties),
                labels=design.spatial_graph.component_id,
                expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
                count_moves_per_iteration=1,
                blocked_refresh_frequency=25,
                blocked_refresh_attempts=12,
            )

    corrupt_sidecar = tmp_path / "corrupt-sidecar.json"
    corrupt_sidecar.write_bytes(initial.read_bytes())
    corrupt_sidecar.with_name(corrupt_sidecar.name + ".sha256").write_text(
        "0" * 64 + "\n", encoding="ascii", newline="\n"
    )
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verifier._load_canonical_checkpoint(corrupt_sidecar)
    noncanonical_sidecar = tmp_path / "noncanonical-sidecar.json"
    noncanonical_sidecar.write_bytes(initial.read_bytes())
    digest = hashlib.sha256(noncanonical_sidecar.read_bytes()).hexdigest()
    noncanonical_sidecar.with_name(
        noncanonical_sidecar.name + ".sha256"
    ).write_bytes((digest + "\n\n").encode("ascii"))
    with pytest.raises(ValueError, match="Noncanonical SHA-256 sidecar"):
        verifier._load_canonical_checkpoint(noncanonical_sidecar)


def test_isolated_resume_from_custody_rejects_resigned_retry_extension_and_rng_splices(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_resume_from_adversarial",
    )

    def publish_checkpoint(path: Path, payload: dict[str, object]) -> str:
        raw = verifier._canonical_bytes(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.with_name(path.name + ".sha256").write_bytes(
            (hashlib.sha256(raw).hexdigest() + "\n").encode("ascii")
        )
        return hashlib.sha256(raw).hexdigest()

    def certificate(
        *,
        mode: str,
        chain_root: Path,
        status_path: Path,
        status: dict[str, object],
        rebound_path: Path | None = None,
    ) -> dict[str, object]:
        return {
            "schema_id": "sr_v2_spatial_resume_from/v1",
            "mode": mode,
            "source_immutable_status_path": status_path.relative_to(
                chain_root
            ).as_posix(),
            "source_immutable_status_sha256": hashlib.sha256(
                status_path.read_bytes()
            ).hexdigest(),
            "source_checkpoint_path": status["latest_checkpoint"],
            "source_checkpoint_sha256": status["latest_checkpoint_sha256"],
            "source_extension_epoch": status["extension_epoch"],
            "source_job_attempt": status["job_attempt"],
            "source_iteration": status["iterations"],
            "source_saved_draws": status["retained_draws"],
            "rebound_checkpoint_path": (
                None
                if rebound_path is None
                else rebound_path.relative_to(chain_root).as_posix()
            ),
            "rebound_checkpoint_sha256": (
                None
                if rebound_path is None
                else hashlib.sha256(rebound_path.read_bytes()).hexdigest()
            ),
        }

    # Retry custody is anchored to the exact prior immutable status and its
    # acknowledged checkpoint.  Re-signing both source files cannot alter the
    # already-published next-attempt certificate.
    _, _, _, retry_checkpoint, _, _ = _tiny_spatial_runtime(
        tmp_path / "retry-chain"
    )
    retry_root = retry_checkpoint.parents[1]
    retry_status_path = (
        retry_root / "attempts/epoch_0/attempt_1/status.json"
    )
    retry_status: dict[str, object] = {
        "status": "checkpointed",
        "failure_class": None,
        "failure_category": None,
        "retryable": True,
        "extension_epoch": 0,
        "job_attempt": 1,
        "iterations": 0,
        "retained_draws": 0,
        "latest_checkpoint": retry_checkpoint.relative_to(retry_root).as_posix(),
        "latest_checkpoint_sha256": hashlib.sha256(
            retry_checkpoint.read_bytes()
        ).hexdigest(),
    }
    _write_json_sidecar(retry_status_path, retry_status)
    retry_certificate = certificate(
        mode="retry",
        chain_root=retry_root,
        status_path=retry_status_path,
        status=retry_status,
    )
    checked = verifier._validate_resume_from_certificate(
        retry_certificate,
        evidence_certificate=retry_certificate,
        chain_root=retry_root,
        current_epoch=0,
        current_attempt=2,
        prior_status=retry_status,
        prior_status_path=retry_status_path,
    )
    assert checked["source_checkpoint"]["current_state"]
    bool_aliases = {
        "source_extension_epoch": False,
        "source_job_attempt": True,
        "source_iteration": False,
        "source_saved_draws": False,
    }
    for field, value in bool_aliases.items():
        aliased = dict(retry_certificate)
        aliased[field] = value
        with pytest.raises(ValueError, match="exact integer"):
            verifier._validate_resume_from_certificate(
                aliased,
                evidence_certificate=aliased,
                chain_root=retry_root,
                current_epoch=0,
                current_attempt=2,
                prior_status=retry_status,
                prior_status_path=retry_status_path,
            )
    evidence_alias = dict(retry_certificate)
    evidence_alias["source_iteration"] = False
    with pytest.raises(ValueError, match="schema/evidence mismatch"):
        verifier._validate_resume_from_certificate(
            retry_certificate,
            evidence_certificate=evidence_alias,
            chain_root=retry_root,
            current_epoch=0,
            current_attempt=2,
            prior_status=retry_status,
            prior_status_path=retry_status_path,
        )

    spliced_retry = verifier._load_canonical_checkpoint(retry_checkpoint)
    spliced_retry["current_state"]["log_sigma_county_hex"] = np.nextafter(
        float.fromhex(spliced_retry["current_state"]["log_sigma_county_hex"]),
        np.inf,
    ).hex()
    retry_status["latest_checkpoint_sha256"] = publish_checkpoint(
        retry_checkpoint, spliced_retry
    )
    _write_json_sidecar(retry_status_path, retry_status)
    verifier._set_hold(
        tmp_path,
        reason="independent_verification_not_passed",
        stage="independent_verification",
        extension_epoch=0,
        output_base_override=tmp_path,
    )
    with pytest.raises(ValueError, match="resume|source|status|SHA-256"):
        verifier._validate_resume_from_certificate(
            retry_certificate,
            evidence_certificate=retry_certificate,
            chain_root=retry_root,
            current_epoch=0,
            current_attempt=2,
            prior_status=retry_status,
            prior_status_path=retry_status_path,
        )

    # An extension rebound changes only reviewed identity/epoch/attempt fields.
    # Even when a forged rebound and both certificates are coherently rehashed,
    # state and RNG differences must fail semantic equality.
    _, _, _, prior_checkpoint, _, _ = _tiny_spatial_runtime(
        tmp_path / "extension-chain"
    )
    extension_root = prior_checkpoint.parents[1]
    prior_status_path = extension_root / "attempts/epoch_0/attempt_1/status.json"
    prior_status: dict[str, object] = {
        "status": "completed",
        "failure_class": None,
        "failure_category": None,
        "retryable": False,
        "extension_epoch": 0,
        "job_attempt": 1,
        "iterations": 0,
        "retained_draws": 0,
        "latest_checkpoint": prior_checkpoint.relative_to(
            extension_root
        ).as_posix(),
        "latest_checkpoint_sha256": hashlib.sha256(
            prior_checkpoint.read_bytes()
        ).hexdigest(),
    }
    _write_json_sidecar(prior_status_path, prior_status)
    prior_payload = verifier._load_canonical_checkpoint(prior_checkpoint)
    rebound_payload = json.loads(json.dumps(prior_payload))
    rebound_payload["target_fingerprint"] = "e" * 64
    rebound_payload["extension_epoch"] = 1
    rebound_payload["job_attempt"] = 1
    rebound_path = (
        extension_root
        / "checkpoints/checkpoint_epoch_1_attempt_1_iter_000000000.json"
    )
    publish_checkpoint(rebound_path, rebound_payload)
    extension_certificate = certificate(
        mode="extension",
        chain_root=extension_root,
        status_path=prior_status_path,
        status=prior_status,
        rebound_path=rebound_path,
    )
    checked = verifier._validate_resume_from_certificate(
        extension_certificate,
        evidence_certificate=extension_certificate,
        chain_root=extension_root,
        current_epoch=1,
        current_attempt=1,
        prior_status=prior_status,
        prior_status_path=prior_status_path,
    )
    assert checked["rebound_checkpoint"]["extension_epoch"] == 1

    state_splice = json.loads(json.dumps(rebound_payload))
    state_splice["current_state"]["log_sigma_county_hex"] = np.nextafter(
        float.fromhex(state_splice["current_state"]["log_sigma_county_hex"]),
        np.inf,
    ).hex()
    publish_checkpoint(rebound_path, state_splice)
    state_certificate = certificate(
        mode="extension",
        chain_root=extension_root,
        status_path=prior_status_path,
        status=prior_status,
        rebound_path=rebound_path,
    )
    with pytest.raises(ValueError, match="semantic"):
        verifier._validate_resume_from_certificate(
            state_certificate,
            evidence_certificate=state_certificate,
            chain_root=extension_root,
            current_epoch=1,
            current_attempt=1,
            prior_status=prior_status,
            prior_status_path=prior_status_path,
        )

    rng_splice = json.loads(json.dumps(rebound_payload))
    rng_splice["rng_state"]["state"]["state"] += 1
    publish_checkpoint(rebound_path, rng_splice)
    rng_certificate = certificate(
        mode="extension",
        chain_root=extension_root,
        status_path=prior_status_path,
        status=prior_status,
        rebound_path=rebound_path,
    )
    with pytest.raises(ValueError, match="semantic"):
        verifier._validate_resume_from_certificate(
            rng_certificate,
            evidence_certificate=rng_certificate,
            chain_root=extension_root,
            current_epoch=1,
            current_attempt=1,
            prior_status=prior_status,
            prior_status_path=prior_status_path,
        )
    gate = json.loads(
        (tmp_path / verifier.RUN_ID / "spatial_sensitivity_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False


def test_resume_certificate_preserves_immediate_failure_checkpoint_authority(
    tmp_path: Path,
) -> None:
    runner = _load_script(
        "107_run_sr_v2_spatial_sensitivity_chain.py",
        "spatial_runner_immediate_failure_resume",
    )
    _, _, _, checkpoint, _, _ = _tiny_spatial_runtime(
        tmp_path / "immediate-failure-chain"
    )
    chain_root = checkpoint.parents[1]
    status = {
        "extension_epoch": 0,
        "job_attempt": 2,
        "iterations": 0,
        "retained_draws": 0,
        "latest_checkpoint": checkpoint.relative_to(chain_root).as_posix(),
        "latest_checkpoint_sha256": hashlib.sha256(
            checkpoint.read_bytes()
        ).hexdigest(),
    }
    status_path = chain_root / "attempts/epoch_0/attempt_2/status.json"
    _write_json_sidecar(status_path, status)
    resume_from = runner._resume_from_certificate(
        chain_root,
        mode="retry",
        source_checkpoint=checkpoint,
        source_status=status,
        rebound_checkpoint=None,
    )
    assert resume_from["source_immutable_status_path"].endswith(
        "attempt_2/status.json"
    )
    assert resume_from["source_job_attempt"] == 1
    assert resume_from["source_iteration"] == status["iterations"]


def test_isolated_checkpoint_recomputes_latent_and_blocked_proposal_totals(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_counter_schedule_adversarial",
    )
    frame, design, identity, initial, _, _ = _tiny_spatial_runtime(
        tmp_path / "counter-runtime"
    )
    seeds = {
        "chain_seed": 74291,
        "allocation_initialization_seed": 74251,
        "spatial_initialization_seed": 74261,
    }
    checkpoint = verifier._load_canonical_checkpoint(initial)
    checkpoint["iteration"] = 25
    for name in (
        "beta",
        "state",
        "year",
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
        "spatial_hyperparameters",
    ):
        checkpoint["proposed"][name] = 25
    checkpoint["proposed"]["transfer"] = 25
    checkpoint["proposed"]["blocked_refresh"] = 12
    checkpoint["proposed"]["mala"] = 5
    checkpoint["adaptation_state"].update(
        {
            "attempted": 5,
            "accepted": 0,
            "window_attempted": 5,
            "window_accepted": 0,
            "windows_completed": 0,
            "adaptation_frozen": False,
        }
    )
    verifier._validate_checkpoint_payload(
        checkpoint,
        identity=identity,
        seeds=seeds,
        expected_epoch=0,
        expected_attempt=1,
        expected_iteration=25,
        expected_draws=0,
        expected_chunks=0,
        row_count=len(frame),
        county_count=len(design.spatial_graph.counties),
        labels=design.spatial_graph.component_id,
        expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
        count_moves_per_iteration=1,
        blocked_refresh_frequency=25,
        blocked_refresh_attempts=12,
    )

    checkpoint["proposed"]["transfer"] -= 1
    tampered_path = tmp_path / "counter-tamper.json"
    raw = verifier._canonical_bytes(checkpoint)
    tampered_path.write_bytes(raw)
    tampered_path.with_name(tampered_path.name + ".sha256").write_bytes(
        (hashlib.sha256(raw).hexdigest() + "\n").encode("ascii")
    )
    resigned = verifier._load_canonical_checkpoint(tampered_path)
    verifier._set_hold(
        tmp_path,
        reason="independent_verification_not_passed",
        stage="independent_verification",
        extension_epoch=0,
        output_base_override=tmp_path,
    )
    with pytest.raises(ValueError, match="latent proposal schedule"):
        verifier._validate_checkpoint_payload(
            resigned,
            identity=identity,
            seeds=seeds,
            expected_epoch=0,
            expected_attempt=1,
            expected_iteration=25,
            expected_draws=0,
            expected_chunks=0,
            row_count=len(frame),
            county_count=len(design.spatial_graph.counties),
            labels=design.spatial_graph.component_id,
            expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
            count_moves_per_iteration=1,
            blocked_refresh_frequency=25,
            blocked_refresh_attempts=12,
        )
    checkpoint["proposed"]["transfer"] += 1
    checkpoint["proposed"]["blocked_refresh"] = 11
    with pytest.raises(ValueError, match="blocked-refresh schedule"):
        verifier._validate_checkpoint_payload(
            checkpoint,
            identity=identity,
            seeds=seeds,
            expected_epoch=0,
            expected_attempt=1,
            expected_iteration=25,
            expected_draws=0,
            expected_chunks=0,
            row_count=len(frame),
            county_count=len(design.spatial_graph.counties),
            labels=design.spatial_graph.component_id,
            expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
            count_moves_per_iteration=1,
            blocked_refresh_frequency=25,
            blocked_refresh_attempts=12,
        )
    gate = json.loads(
        (tmp_path / verifier.RUN_ID / "spatial_sensitivity_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False


def test_isolated_status_rejects_retryable_terminal_noncompletion() -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_terminal_state_machine",
    )
    for status in (
        {
            "status": "checkpointed",
            "failure_class": None,
            "failure_category": None,
            "retryable": True,
        },
        {
            "status": "failed",
            "failure_class": "TimeoutError",
            "failure_category": "transient_runtime",
            "retryable": True,
        },
    ):
        with pytest.raises(ValueError, match="terminal.*completed"):
            verifier._validate_status_failure_contract(
                status,
                iterations=180_000,
                terminal_iteration=180_000,
            )


def test_isolated_status_rejects_bool_aliases_for_all_integer_fields() -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_status_bool_aliases",
    )
    status = {
        "chain_id": 1,
        "array_index": 1,
        "extension_epoch": 0,
        "job_attempt": 1,
        "iterations": 0,
        "retained_draws": 0,
        "chunks": 0,
        "seeds": {
            "chain_seed": 74291,
            "allocation_initialization_seed": 74251,
            "spatial_initialization_seed": 74261,
        },
    }
    aliases = {
        "chain_id": True,
        "array_index": True,
        "extension_epoch": False,
        "job_attempt": True,
        "iterations": False,
        "retained_draws": False,
        "chunks": False,
    }
    for field, value in aliases.items():
        tampered = json.loads(json.dumps(status))
        tampered[field] = value
        with pytest.raises(ValueError, match="exact integer"):
            verifier._validate_status_integer_fields(tampered)
    for seed in status["seeds"]:
        tampered = json.loads(json.dumps(status))
        tampered["seeds"][seed] = True
        with pytest.raises(ValueError, match="exact integer"):
            verifier._validate_status_integer_fields(tampered)


def test_isolated_retry_status_cannot_rollback_below_certified_source() -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_retry_rollback",
    )
    certificate = {
        "mode": "retry",
        "source_checkpoint_path": (
            "checkpoints/checkpoint_epoch_0_attempt_1_iter_000001000.json"
        ),
        "source_checkpoint_sha256": "a" * 64,
        "source_iteration": 1_000,
        "source_saved_draws": 0,
    }
    rewound = {
        "status": "failed",
        "job_attempt": 2,
        "iterations": 0,
        "retained_draws": 0,
        "latest_checkpoint": (
            "checkpoints/checkpoint_epoch_0_attempt_1_iter_000000000.json"
        ),
        "latest_checkpoint_sha256": "b" * 64,
    }
    with pytest.raises(ValueError, match="rollback"):
        verifier._validate_retry_progress_authority(
            rewound,
            certificate,
            checkpoint_creator_attempt=1,
        )
    unchanged = {
        **rewound,
        "iterations": 1_000,
        "latest_checkpoint": certificate["source_checkpoint_path"],
        "latest_checkpoint_sha256": certificate["source_checkpoint_sha256"],
    }
    verifier._validate_retry_progress_authority(
        unchanged,
        certificate,
        checkpoint_creator_attempt=1,
    )
    progressed_with_old_checkpoint = {
        **unchanged,
        "iterations": 1_001,
    }
    with pytest.raises(ValueError, match="current attempt"):
        verifier._validate_retry_progress_authority(
            progressed_with_old_checkpoint,
            certificate,
            checkpoint_creator_attempt=1,
        )


def test_isolated_retry_checkpoint_accepts_exact_nonempty_pending_buffers(
    tmp_path: Path,
) -> None:
    import base64

    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_nonempty_pending_resume",
    )
    frame, design, identity, initial, _, _ = _tiny_spatial_runtime(
        tmp_path / "pending-runtime"
    )
    seeds = {
        "chain_seed": 74291,
        "allocation_initialization_seed": 74251,
        "spatial_initialization_seed": 74261,
    }
    checkpoint = verifier._load_canonical_checkpoint(initial)
    iteration = 45_030
    parameters = list(identity["target"]["parameter_schema"])
    county_count = len(design.spatial_graph.counties)

    def encoded(values: np.ndarray, dtype: str) -> dict[str, object]:
        array = np.ascontiguousarray(values, dtype=np.dtype(dtype))
        return {
            "dtype": np.dtype(dtype).str,
            "shape": list(array.shape),
            "data_base64": base64.b64encode(array.tobytes(order="C")).decode(
                "ascii"
            ),
        }

    checkpoint["iteration"] = iteration
    checkpoint["saved_draws"] = 1
    checkpoint["next_draw_id"] = 2
    checkpoint["output_positions"] = {
        "scalar_rows": len(parameters),
        "spatial_draws": 1,
    }
    for name in (
        "beta",
        "state",
        "year",
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
        "spatial_hyperparameters",
    ):
        checkpoint["proposed"][name] = iteration
    checkpoint["proposed"].update(
        {
            "transfer": iteration,
            "blocked_refresh": (iteration // 25) * 12,
            "mala": iteration // 5,
        }
    )
    checkpoint["adaptation_state"].update(
        {
            "attempted": iteration // 5,
            "accepted": 0,
            "window_attempted": 0,
            "window_accepted": 0,
            "windows_completed": 90,
            "adaptation_frozen": True,
        }
    )
    checkpoint["pending_buffers"] = {
        "scalar": {
            "columns": [
                "chain_id",
                "draw_id",
                "extension_epoch",
                "parameter",
                "value",
            ],
            "row_count": len(parameters),
            "chain_id": encoded(np.ones(len(parameters)), "<i8"),
            "draw_id": encoded(np.ones(len(parameters)), "<i8"),
            "extension_epoch": encoded(np.zeros(len(parameters)), "<i8"),
            "parameter": parameters,
            "value": encoded(np.zeros(len(parameters)), "<f8"),
        },
        "structured": encoded(np.zeros((1, county_count)), "<f8"),
        "unstructured": encoded(np.zeros((1, county_count)), "<f8"),
    }
    verifier._validate_checkpoint_payload(
        checkpoint,
        identity=identity,
        seeds=seeds,
        expected_epoch=0,
        expected_attempt=1,
        expected_iteration=iteration,
        expected_draws=1,
        expected_chunks=0,
        row_count=len(frame),
        county_count=county_count,
        labels=design.spatial_graph.component_id,
        expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
        count_moves_per_iteration=1,
        blocked_refresh_frequency=25,
        blocked_refresh_attempts=12,
    )
    tampered = json.loads(json.dumps(checkpoint))
    tampered["pending_buffers"]["scalar"]["draw_id"] = encoded(
        np.full(len(parameters), 2), "<i8"
    )
    with pytest.raises(ValueError, match="pending scalar content"):
        verifier._validate_checkpoint_payload(
            tampered,
            identity=identity,
            seeds=seeds,
            expected_epoch=0,
            expected_attempt=1,
            expected_iteration=iteration,
            expected_draws=1,
            expected_chunks=0,
            row_count=len(frame),
            county_count=county_count,
            labels=design.spatial_graph.component_id,
            expected_y=frame["latent_count"].to_numpy(dtype=np.int64),
            count_moves_per_iteration=1,
            blocked_refresh_frequency=25,
            blocked_refresh_attempts=12,
        )


def test_production_shape_prepare_target_matches_isolated_verifier() -> None:
    from bayes_constrained.model import (
        active_prior_specification,
        crude_intercept_prior,
        make_design,
    )
    from bayes_constrained.spatial_bym2 import spatial_model_frame_sha256

    prepare = _load_script(
        "106_prepare_sr_v2_spatial_sensitivity.py",
        "spatial_prepare_production_shape_target",
    )
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_production_shape_target",
    )
    frame = pd.read_parquet(
        ROOT / "data/processed/bayes_constrained/model_frame.parquet"
    )
    normalized = frame["county_fips"].astype(str).str.strip().str.zfill(5)
    counties = tuple(sorted(normalized.unique()))
    assert len(counties) == 3_142
    county_index = {county: index for index, county in enumerate(counties)}
    graph_hash = "4" * 64
    graph = SimpleNamespace(
        counties=counties,
        row_county_index=normalized.map(county_index).to_numpy(dtype=np.int64),
        contract_sha256=graph_hash,
    )
    design = make_design(frame, spatial_graph=graph)
    config_hash = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    manifest = {
        "input_manifest_sha256": "2" * 64,
        "final_source_manifest_sha256": "3" * 64,
        "model_frame_semantic_sha256": spatial_model_frame_sha256(frame),
        "graph_contract_sha256": graph_hash,
    }
    prepare_target = prepare._epoch_zero_target(
        frame,
        design=design,
        config_sha256=config_hash,
        input_manifest_sha256=manifest["input_manifest_sha256"],
        final_source_manifest_sha256=manifest["final_source_manifest_sha256"],
        graph_contract_sha256=graph_hash,
        prior=active_prior_specification(),
        intercept_mean=crude_intercept_prior(frame),
    )
    isolated_target = verifier._expected_epoch_zero_target(
        frame, counties, manifest, CONFIG_PATH
    )
    assert isolated_target is not None
    assert prepare_target == isolated_target
    assert len(isolated_target["parameter_schema"]) == 71
    assert verifier._count_moves_per_iteration(frame) == 350
    assert isolated_target["design_schema"]["row_county_index"]["shape"] == [
        len(frame)
    ]


def test_comparison_bytes_apply_drawwise_transform_and_exact_boundaries() -> None:
    from bayes_constrained.spatial_pipeline import comparison_candidate_bytes

    primary = pd.DataFrame(
        {
            "parameter": COMPARISON_ROWS,
            "posterior_mean": [2.0] * 6 + [0.25, -0.5],
            "credible_interval_lower_95": [1.5] * 6 + [0.1, -0.8],
            "credible_interval_upper_95": [2.5] * 6 + [0.4, -0.2],
        }
    )
    values: list[dict[str, object]] = []
    for parameter in COMPARISON_ROWS:
        draw_values = [0.0, np.log(4.0)] if parameter in COMPARISON_ROWS[:6] else [0.0, 0.5]
        for chain_id in (1, 2, 3, 4):
            for draw_id, value in enumerate(draw_values, start=1):
                values.append(
                    {
                        "chain_id": chain_id,
                        "draw_id": draw_id,
                        "extension_epoch": 0,
                        "parameter": parameter,
                        "value": np.float64(value),
                    }
                )
    payload = comparison_candidate_bytes(primary, pd.DataFrame(values))
    assert payload.endswith(b"\n") and b"\r" not in payload
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8"), newline="")))
    assert [row["parameter"] for row in rows] == COMPARISON_ROWS
    assert rows[0]["scale"] == "incidence_rate_ratio"
    assert float(rows[0]["spatial_mean"]) == 2.5  # mean(exp([0, log(4)])), not exp(mean)
    assert float(rows[0]["absolute_change"]) == 0.5
    assert float(rows[0]["relative_change"]) == 0.25
    assert rows[0]["interval_overlap"] == "true"
    assert rows[6]["scale"] == "standardized_log_rate_coefficient"
    assert rows[6]["interval_overlap"] == "true"  # touching/overlapping closed intervals
    assert payload == comparison_candidate_bytes(primary, pd.DataFrame(values))
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_comparison_contract",
    )
    assert payload == verifier._comparison_bytes(primary, pd.DataFrame(values))


@pytest.mark.parametrize("primary_mean", [0.0, np.nan, np.inf, -np.inf])
def test_comparison_bytes_fail_closed_on_zero_or_nonfinite_primary_mean(
    primary_mean: float,
) -> None:
    from bayes_constrained.spatial_pipeline import comparison_candidate_bytes

    primary = pd.DataFrame(
        {
            "parameter": COMPARISON_ROWS,
            "posterior_mean": [primary_mean] + [1.0] * 7,
            "credible_interval_lower_95": [0.5] * 8,
            "credible_interval_upper_95": [1.5] * 8,
        }
    )
    draws = pd.DataFrame(
        [
            {
                "chain_id": chain,
                "draw_id": draw,
                "extension_epoch": 0,
                "parameter": parameter,
                "value": np.float64(0.1),
            }
            for parameter in COMPARISON_ROWS
            for chain in (1, 2, 3, 4)
            for draw in (1, 2)
        ]
    )
    with pytest.raises(ValueError, match="primary_mean"):
        comparison_candidate_bytes(primary, draws)
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        f"spatial_verifier_nonfinite_{str(primary_mean).replace('-', 'neg')}",
    )
    with pytest.raises(ValueError, match="finite/nonzero"):
        verifier._comparison_bytes(primary, draws)


def test_public_spatial_loop_and_pipeline_entrypoints_exist() -> None:
    from bayes_constrained import sampler

    assert callable(sampler.run_spatial_mcmc_chain)
    for filename, module_name in (
        ("106_prepare_sr_v2_spatial_sensitivity.py", "spatial_prepare"),
        ("107_run_sr_v2_spatial_sensitivity_chain.py", "spatial_runner"),
        ("108_merge_sr_v2_spatial_sensitivity.py", "spatial_merge"),
        ("109_gate_sr_v2_spatial_sensitivity.py", "spatial_gate"),
    ):
        _load_script(filename, module_name)


def test_public_spatial_loop_schedules_hyper_every_iteration_and_mala_every_fifth(
    tmp_path: Path,
) -> None:
    from bayes_constrained import sampler
    from bayes_constrained.spatial_bym2 import load_spatial_checkpoint

    frame, design, identity, initial, checkpoint_dir, chunk_dir = _tiny_spatial_runtime(
        tmp_path
    )
    result = sampler.run_spatial_mcmc_chain(
        frame,
        design=design,
        identity=identity,
        checkpoint_path=initial,
        checkpoint_dir=checkpoint_dir,
        chunk_dir=chunk_dir,
        job_attempt=1,
        settings={
            "max_count_proposals_per_iter": 1,
            "count_move_sweeps_per_iter": 0.1,
            "blocked_refresh_frequency": 0,
            "blocked_refresh_attempts": 0,
            "move_weights": {"state_year_transfer": 1.0},
        },
        checkpoint_every=1000,
        stop_requested=lambda iteration: iteration >= 5,
    )
    assert result["status"] == "checkpointed"
    assert result["iteration"] == 5
    latest = Path(result["latest_checkpoint"])
    assert latest.name == "checkpoint_epoch_0_attempt_1_iter_000000005.json"
    loaded = load_spatial_checkpoint(
        latest,
        expected_identity=identity,
        frame=frame,
        design=design,
        intercept_mean=float.fromhex(
            identity["target"]["intercept_mean_float_hex"]
        ),
        chunk_dir=chunk_dir,
    )
    assert loaded["proposed"]["spatial_hyperparameters"] == 5
    assert loaded["proposed"]["mala"] == 1
    assert loaded["adaptation_state"]["attempted"] == 1
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_authentic_nonzero_checkpoint",
    )
    checkpoint = verifier._load_canonical_checkpoint(latest)
    graph = design.spatial_graph
    assert verifier._validate_checkpoint_target(
        checkpoint,
        target=identity["target"],
        frame=frame,
        counties=graph.counties,
        adjacency=graph.adjacency,
        components=graph.components,
        scales=graph.component_scale,
        label="Authentic nonzero checkpoint",
    ) == float.fromhex(checkpoint["current_target"])
    one_ulp = json.loads(json.dumps(checkpoint))
    one_ulp["current_target"] = np.nextafter(
        float.fromhex(checkpoint["current_target"]), np.inf
    ).item().hex()
    with pytest.raises(ValueError, match="does not recompute exactly"):
        verifier._validate_checkpoint_target(
            one_ulp,
            target=identity["target"],
            frame=frame,
            counties=graph.counties,
            adjacency=graph.adjacency,
            components=graph.components,
            scales=graph.component_scale,
            label="Tampered checkpoint",
        )


def test_exact_assignment_epoch_draw_chunk_and_boundary_contracts() -> None:
    from bayes_constrained.sampler import spatial_iteration_schedule
    from bayes_constrained.spatial_pipeline import load_spatial_execution_spec

    spec = load_spatial_execution_spec(CONFIG_PATH)
    assert [
        (
            row.array_index,
            row.chain_id,
            row.chain_seed,
            row.allocation_initialization_seed,
            row.spatial_initialization_seed,
        )
        for row in spec.chain_map
    ] == [
        (1, 1, 74291, 74251, 74261),
        (2, 2, 74292, 74252, 74262),
        (3, 3, 74293, 74253, 74263),
        (4, 4, 74294, 74254, 74264),
    ]
    assert spec.epoch_contract == {
        0: {"iterations": 180000, "draws": 4500, "chunks": 18},
        1: {"iterations": 270000, "draws": 7500, "chunks": 30},
        2: {"iterations": 360000, "draws": 10500, "chunks": 42},
        3: {"iterations": 450000, "draws": 13500, "chunks": 54},
    }
    assert spatial_iteration_schedule(0) == {
        "iteration": 0,
        "saved_draws": 0,
        "next_draw_id": 1,
        "mala_attempts": 0,
        "base_theta_attempts": 0,
        "spatial_hyperparameter_attempts": 0,
        "adaptation_frozen": False,
        "retains_draw": False,
    }
    for iteration, draws, mala in (
        (44_999, 0, 8_999),
        (45_000, 0, 9_000),
        (180_000, 4_500, 36_000),
        (270_000, 7_500, 54_000),
        (360_000, 10_500, 72_000),
        (450_000, 13_500, 90_000),
    ):
        schedule = spatial_iteration_schedule(iteration)
        assert schedule["saved_draws"] == draws
        assert schedule["next_draw_id"] == draws + 1
        assert schedule["mala_attempts"] == mala
        assert schedule["base_theta_attempts"] == iteration
        assert schedule["spatial_hyperparameter_attempts"] == iteration
        assert schedule["adaptation_frozen"] is (iteration >= 45_000)


def test_prepare_sets_canonical_hold_before_config_or_envelope_failure(
    tmp_path: Path,
) -> None:
    prepare = _load_script(
        "106_prepare_sr_v2_spatial_sensitivity.py", "spatial_prepare_hold"
    )
    output = tmp_path / "spatial-output"
    run_root = output / "sr-v2-spatial-sensitivity-20260818-v1"
    run_root.mkdir(parents=True)
    (run_root / "spatial_sensitivity_gate.json").write_text(
        '{"passed":true,"status":"PASS"}\n', encoding="utf-8"
    )
    malformed = tmp_path / "bad.yaml"
    malformed.write_text("not: [valid", encoding="utf-8")
    with pytest.raises(Exception):
        prepare.prepare(
            root=tmp_path,
            config_path=malformed,
            launch_envelope_path=None,
            output_base_override=output,
        )
    gate = json.loads(
        (run_root / "spatial_sensitivity_gate.json").read_text(encoding="utf-8")
    )
    assert gate["passed"] is False
    assert gate["status"] == "HOLD"
    assert gate["submission_authorized"] is False
    assert not (run_root / "prepared").exists()


def test_scale_recomputation_has_no_large_component_shortcut() -> None:
    from scipy.sparse import csr_matrix

    from bayes_constrained.spatial_pipeline import recompute_component_scales

    path_three = csr_matrix(
        np.asarray([[0.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    )
    assert recompute_component_scales(
        path_three, (np.asarray([0, 1, 2], dtype=np.int64),)
    ) == pytest.approx((0.40933683318226494,), rel=0.0, abs=1e-15)

    sizes = (3_099, 17, 10, 2)
    offsets = np.cumsum((0,) + sizes)
    components = tuple(
        np.arange(offsets[index], offsets[index + 1], dtype=np.int64)
        for index in range(len(sizes))
    )
    called: list[int] = []

    def recording_solver(precision: np.ndarray) -> float:
        called.append(len(precision))
        return float(len(precision))

    result = recompute_component_scales(
        csr_matrix((sum(sizes), sum(sizes)), dtype=np.float64),
        components,
        scale_solver=recording_solver,
    )
    assert called == [3_099, 17, 10, 2]
    assert result == tuple(map(float, sizes))


def test_prepare_publishes_four_distinct_starts_idempotently_and_refuses_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bayes_constrained.spatial_pipeline import canonical_json_bytes

    prepare = _load_script(
        "106_prepare_sr_v2_spatial_sensitivity.py", "spatial_prepare_success"
    )
    frame, design, _, _, _, _ = _tiny_spatial_runtime(tmp_path / "runtime")
    root = tmp_path / "repo"
    (root / "outputs/scientific_reports_v2/production_8chain").mkdir(
        parents=True
    )
    (root / "outputs/scientific_reports_v2/production_8chain/production_gate.json").write_text(
        '{"passed":true}\n', encoding="utf-8", newline="\n"
    )
    (root / "outputs/scientific_reports_v2/spatial_residual_diagnostics").mkdir(
        parents=True
    )
    (root / "outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json").write_text(
        '{"recommended_action":"run_spatial_random_effect_sensitivity"}\n',
        encoding="utf-8",
        newline="\n",
    )
    envelope = tmp_path / "external-envelope.json"
    envelope.write_text("{}\n", encoding="utf-8", newline="\n")
    envelope.with_name(envelope.name + ".sha256").write_text(
        hashlib.sha256(envelope.read_bytes()).hexdigest() + "\n",
        encoding="ascii",
        newline="\n",
    )
    provenance = {
        "source_manifest": {"sources": {}},
        "launch_envelope_sha256": hashlib.sha256(envelope.read_bytes()).hexdigest(),
        "final_source_manifest_sha256": "1" * 64,
        "launch_commit": "2" * 40,
        "bundle_sha256": "3" * 64,
        "joint_regression_evidence_sha256": "4" * 64,
    }
    real_verify_hash_inventory = prepare.verify_hash_inventory
    monkeypatch.setattr(
        prepare,
        "verify_hash_inventory",
        lambda base, inventory, **kwargs: (
            {}
            if Path(base).resolve() == root.resolve()
            else real_verify_hash_inventory(base, inventory, **kwargs)
        ),
    )
    monkeypatch.setattr(
        prepare,
        "load_reviewed_launch_envelope",
        lambda *_args, **_kwargs: provenance,
    )

    graph = design.spatial_graph
    graph_payloads = {
        "graph/county_order.txt": "".join(
            f"{county}\n" for county in graph.counties
        ).encode("utf-8"),
        "graph/edge_list.txt": b"01001|01003\n01003|01005\n",
        "graph/components.csv": b"component_id,minimum_fips,size,singleton,scale_hex\n0,01001,3,false,0x1.a3281bf96580bp-2\n",
        "graph/scale_certificate.json": canonical_json_bytes(
            {"schema_id": "sr_v2_spatial_scale_certificate/v1", "scales": []}
        ),
        "graph/graph_contract.json": canonical_json_bytes(
            {
                "schema_id": "sr_v2_spatial_graph_contract/v1",
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "graph_contract_sha256": graph.contract_sha256,
            }
        ),
    }
    allocations = [
        np.asarray(values, dtype=np.int64)
        for values in (
            [1, 2, 2, 1, 1, 1],
            [2, 1, 1, 2, 1, 1],
            [1, 1, 1, 1, 2, 2],
            [2, 2, 1, 1, 1, 1],
        )
    ]
    calls = iter(allocations)

    def solver(*_args, **_kwargs):
        return next(calls).copy()

    output = tmp_path / "out"
    manifest = prepare.prepare(
        root=root,
        config_path=CONFIG_PATH,
        launch_envelope_path=envelope,
        output_base_override=output,
        frame_loader=lambda: frame.copy(deep=True),
        allocation_solver=solver,
        graph_preparer=lambda *_args, **_kwargs: (graph, graph_payloads),
    )
    run_root = output / "sr-v2-spatial-sensitivity-20260818-v1"
    assert (run_root / "prepared/prepared_run_manifest.json.sha256").is_file()
    assert len(manifest["chain_mapping"]) == 4
    assert manifest["production_eligible"] is False
    assert set(manifest["builder_provenance"].values()) == {"injected_test_only"}
    assert len({row["initial_allocation_sha256"] for row in manifest["chain_mapping"]}) == 4
    assert len({row["chain_fingerprint"] for row in manifest["chain_mapping"]}) == 4
    gate = json.loads(
        (run_root / "spatial_sensitivity_gate.json").read_text(encoding="utf-8")
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False

    reused = prepare.prepare(
        root=root,
        config_path=CONFIG_PATH,
        launch_envelope_path=envelope,
        output_base_override=output,
        frame_loader=lambda: (_ for _ in ()).throw(AssertionError("must not rerun")),
        allocation_solver=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not resolve")
        ),
        graph_preparer=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not rebuild")
        ),
    )
    assert reused["preparation_identity"] == manifest["preparation_identity"]
    tampered = run_root / "prepared/graph/county_order.txt"
    tampered.write_bytes(tampered.read_bytes() + b"99999\n")
    with pytest.raises(ValueError, match="SHA-256"):
        prepare.prepare(
            root=root,
            config_path=CONFIG_PATH,
            launch_envelope_path=envelope,
            output_base_override=output,
        )
    assert json.loads(
        (run_root / "spatial_sensitivity_gate.json").read_text(encoding="utf-8")
    )["status"] == "HOLD"


def test_runner_publishes_exact_status_schedule_and_completed_noop(
    tmp_path: Path,
) -> None:
    runner = _load_script(
        "107_run_sr_v2_spatial_sensitivity_chain.py", "spatial_runner_success"
    )
    frame, design, identity, initial, _, _ = _tiny_spatial_runtime(
        tmp_path / "runtime"
    )
    output = tmp_path / "out"
    run_root = output / "sr-v2-spatial-sensitivity-20260818-v1"
    prepared = run_root / "prepared"
    prepared_checkpoint = (
        prepared
        / "initial_checkpoints/chain_01/checkpoint_epoch_0_attempt_1_iter_000000000.json"
    )
    prepared_checkpoint.parent.mkdir(parents=True)
    prepared_checkpoint.write_bytes(initial.read_bytes())
    prepared_checkpoint.with_name(prepared_checkpoint.name + ".sha256").write_bytes(
        initial.with_name(initial.name + ".sha256").read_bytes()
    )
    manifest = {
        "preparation_identity": "a" * 64,
        "launch_envelope_sha256": "b" * 64,
        "final_source_manifest_sha256": "c" * 64,
        "chain_mapping": [
            {
                "array_index": 1,
                "chain_id": 1,
                "chain_seed": 74291,
                "allocation_initialization_seed": 74251,
                "spatial_initialization_seed": 74261,
                "target_identity": identity,
                "initial_checkpoint": prepared_checkpoint.relative_to(prepared).as_posix(),
            }
        ],
    }

    def prepared_validator(*_args, **_kwargs):
        return {"manifest": manifest, "prepared_root": str(prepared)}

    calls: list[dict[str, object]] = []

    def executor(_frame, **kwargs):
        calls.append(kwargs)
        records: list[dict[str, object]] = []
        for draw_id in range(1, 4_501):
            unsigned = {
                "schema_id": "sr_v2_spatial_retained_assertion/v1",
                "chain_id": 1,
                "draw_id": draw_id,
                "cumulative_iteration": 45_000 + 30 * draw_id,
                "extension_epoch": 0,
                "chunk_id": (draw_id - 1) // 250 + 1,
                "capture_order": "after_latent_target_base6_hyper_and_scheduled_mala",
                "count_constraints_asserted": True,
                "spatial_constraints_asserted": True,
                "latent_y_sha256": "1" * 64,
                "structured_effect_sha256": "2" * 64,
            }
            records.append(
                {
                    **unsigned,
                    "assertion_sha256": hashlib.sha256(
                        json.dumps(
                            unsigned,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=True,
                            allow_nan=False,
                        ).encode("utf-8")
                    ).hexdigest(),
                }
            )
        return {
            "status": "completed",
            "iteration": 180_000,
            "saved_draws": 4_500,
            "latest_checkpoint": str(kwargs["checkpoint_path"]),
            "committed_chunks": [{} for _ in range(18)],
            "start_saved_draws": 0,
            "retained_assertion_records": records,
            "evidence_builder": "injected_test_loop",
        }

    status = runner.run_chain(
        run_id="sr-v2-spatial-sensitivity-20260818-v1",
        array_index=1,
        extension_epoch=0,
        root=tmp_path,
        config_path=CONFIG_PATH,
        output_base_override=output,
        prepared_validator=prepared_validator,
        runtime_loader=lambda *_args: (frame, design, object()),
        chain_executor=executor,
        bounded_test_mode=True,
    )
    assert status["status"] == "completed"
    assert (status["iterations"], status["retained_draws"], status["chunks"]) == (
        180_000,
        4_500,
        18,
    )
    assert len(calls) == 1
    schedule = (
        run_root
        / "chains/chain_01/evidence/epoch_0/attempt_1/retained_assertions.jsonl"
    )
    lines = schedule.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4_500
    assert json.loads(lines[0])["cumulative_iteration"] == 45_030
    assert json.loads(lines[-1])["cumulative_iteration"] == 180_000
    evidence = json.loads(
        (schedule.parent / "attempt_evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["historical_latent_y_stored"] is False
    assert evidence["independent_historical_y_reconstruction_possible"] is False
    assert status["executor_builder"] == "injected_bounded_test_executor"
    resume_fields = {
        "schema_id",
        "mode",
        "source_immutable_status_path",
        "source_immutable_status_sha256",
        "source_checkpoint_path",
        "source_checkpoint_sha256",
        "source_extension_epoch",
        "source_job_attempt",
        "source_iteration",
        "source_saved_draws",
        "rebound_checkpoint_path",
        "rebound_checkpoint_sha256",
    }
    assert set(status["resume_from"]) == resume_fields
    assert status["resume_from"] == evidence["resume_from"]
    assert status["resume_from"] == {
        "schema_id": "sr_v2_spatial_resume_from/v1",
        "mode": "prepared_initial",
        "source_immutable_status_path": None,
        "source_immutable_status_sha256": None,
        "source_checkpoint_path": (
            "checkpoints/checkpoint_epoch_0_attempt_1_iter_000000000.json"
        ),
        "source_checkpoint_sha256": hashlib.sha256(
            prepared_checkpoint.read_bytes()
        ).hexdigest(),
        "source_extension_epoch": 0,
        "source_job_attempt": 1,
        "source_iteration": 0,
        "source_saved_draws": 0,
        "rebound_checkpoint_path": None,
        "rebound_checkpoint_sha256": None,
    }
    assert status["failure_class"] is None

    reused = runner.run_chain(
        run_id="sr-v2-spatial-sensitivity-20260818-v1",
        array_index=1,
        extension_epoch=0,
        root=tmp_path,
        config_path=CONFIG_PATH,
        output_base_override=output,
        prepared_validator=prepared_validator,
        runtime_loader=lambda *_args: (_ for _ in ()).throw(
            AssertionError("completed chain must not reload runtime")
        ),
        chain_executor=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("completed chain must not rerun")
        ),
    )
    assert reused["chain_fingerprint"] == status["chain_fingerprint"]
    checkpoint = run_root / "chains/chain_01" / status["latest_checkpoint"]
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="SHA-256"):
        runner.run_chain(
            run_id="sr-v2-spatial-sensitivity-20260818-v1",
            array_index=1,
            extension_epoch=0,
            root=tmp_path,
            config_path=CONFIG_PATH,
            output_base_override=output,
            prepared_validator=prepared_validator,
        )


def _write_json_sidecar(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    path.with_name(path.name + ".sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
        encoding="ascii",
        newline="\n",
    )


def _commit_tiny_spatial_chunk_history(
    root: Path, *, chunk_count: int
) -> tuple[Path, list[dict[str, object]], object, list[str]]:
    from bayes_constrained.spatial_bym2 import commit_spatial_draw_chunk

    _, design, identity, _, _, _ = _tiny_spatial_runtime(root / "runtime")
    graph = design.spatial_graph
    parameters = list(identity["target"]["parameter_schema"])
    chunk_root = root / "chunks"
    records: list[dict[str, object]] = []
    for chunk_id in range(1, chunk_count + 1):
        draw_start = (chunk_id - 1) * 250 + 1
        draw_ids = np.arange(draw_start, draw_start + 250, dtype=np.int64)
        epoch = 0 if draw_start <= 4_500 else 1
        values = np.zeros(250 * len(parameters), dtype=np.float64)
        for name, replacement in (("sigma_county", 1.0), ("phi_structured", 0.5)):
            values[np.tile(np.asarray(parameters) == name, 250)] = replacement
        scalar = pd.DataFrame(
            {
                "chain_id": np.ones(len(values), dtype=np.int64),
                "draw_id": np.repeat(draw_ids, len(parameters)),
                "extension_epoch": np.full(len(values), epoch, dtype=np.int64),
                "parameter": parameters * 250,
                "value": values,
            }
        )
        records.append(
            commit_spatial_draw_chunk(
                chunk_root,
                chain_id=1,
                extension_epoch=epoch,
                graph=graph,
                parameter_schema=parameters,
                chunk_id=chunk_id,
                draw_ids=draw_ids,
                scalar_draws=scalar,
                structured=np.zeros(
                    (250, len(graph.counties)), dtype=np.float64
                ),
                unstructured=np.zeros(
                    (250, len(graph.counties)), dtype=np.float64
                ),
            )
        )
    return chunk_root, records, graph, parameters


def test_retry_and_reviewed_extension_selectors_are_bounded_and_distinct(
    tmp_path: Path,
) -> None:
    from bayes_constrained.spatial_pipeline import (
        canonical_sha256,
        select_retry_indexes,
        validate_extension_authorization,
    )

    def write_status(chain_id: int, payload: dict[str, object]) -> None:
        chain_root = tmp_path / f"chains/chain_{chain_id:02d}"
        artifact = chain_root / "evidence.txt"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(f"chain {chain_id}\n", encoding="utf-8")
        payload.setdefault("target_fingerprint", "a" * 64)
        payload.setdefault("chain_fingerprint", f"{chain_id:064x}")
        payload.setdefault("preparation_identity", "b" * 64)
        payload.setdefault("launch_envelope_sha256", "c" * 64)
        payload.setdefault(
            "seeds",
            {
                "chain_seed": 74290 + chain_id,
                "allocation_initialization_seed": 74250 + chain_id,
                "spatial_initialization_seed": 74260 + chain_id,
            },
        )
        if payload.get("status") == "completed":
            payload.setdefault("iterations", 180_000)
            payload.setdefault("retained_draws", 4_500)
            payload.setdefault("chunks", 18)
            payload.setdefault("failure_category", None)
            payload.setdefault("retryable", False)
        elif payload.get("status") == "checkpointed":
            payload.setdefault("failure_category", None)
            payload.setdefault("retryable", True)
        elif payload.get("status") == "failed":
            payload.setdefault("failure_category", "transient_runtime")
            payload.setdefault("retryable", True)
        checkpoint = chain_root / (
            f"checkpoints/checkpoint_epoch_{payload['extension_epoch']}_"
            f"attempt_{payload['job_attempt']}_iter_000000000.json"
        )
        _write_json_sidecar(
            checkpoint,
            {
                "schema_version": 2,
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "chain_id": chain_id,
                "extension_epoch": payload["extension_epoch"],
                "target_fingerprint": payload["target_fingerprint"],
                "chain_fingerprint": payload["chain_fingerprint"],
            },
        )
        payload["latest_checkpoint"] = checkpoint.relative_to(chain_root).as_posix()
        payload["latest_checkpoint_sha256"] = hashlib.sha256(
            checkpoint.read_bytes()
        ).hexdigest()
        payload["artifact_sha256"] = {
            "evidence.txt": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            checkpoint.relative_to(chain_root).as_posix(): hashlib.sha256(
                checkpoint.read_bytes()
            ).hexdigest(),
            checkpoint.with_name(checkpoint.name + ".sha256")
            .relative_to(chain_root)
            .as_posix(): hashlib.sha256(
                checkpoint.with_name(checkpoint.name + ".sha256").read_bytes()
            ).hexdigest(),
        }
        immutable = chain_root / (
            f"attempts/epoch_{payload['extension_epoch']}/"
            f"attempt_{payload['job_attempt']}/status.json"
        )
        _write_json_sidecar(immutable, payload)
        _write_json_sidecar(chain_root / "chain_status.json", payload)

    for chain_id, (state, attempt) in enumerate(
        (("completed", 1), ("checkpointed", 1), ("failed", 2), ("completed", 2)),
        start=1,
    ):
        write_status(
            chain_id,
            {
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "chain_id": chain_id,
                "extension_epoch": 0,
                "job_attempt": attempt,
                "status": state,
            },
        )
    selection = select_retry_indexes(tmp_path, extension_epoch=0)
    assert selection["selected_array_indexes"] == [2, 3]
    assert selection["next_job_attempt_by_array_index"] == {"2": 2, "3": 3}
    assert selection["verified_completed_indexes"] == [1, 4]
    # A crash between atomic pointer and sidecar replacement cannot advance or
    # brick selection: immutable attempt history is authoritative.
    pointer_sidecar = tmp_path / "chains/chain_02/chain_status.json.sha256"
    pointer_sidecar.write_text("0" * 64 + "\n", encoding="ascii")
    recovered = select_retry_indexes(tmp_path, extension_epoch=0)
    assert recovered["selected_array_indexes"] == [2, 3]
    orphan = tmp_path / "chains/chain_02/attempts/orphan.bin"
    orphan.write_bytes(b"undeclared")
    with pytest.raises(ValueError, match="inventory"):
        select_retry_indexes(tmp_path, extension_epoch=0)
    orphan.unlink()

    import shutil

    nonretryable_categories = (
        "source",
        "graph",
        "constraint",
        "fingerprint",
        "nonfinite_value",
        "evidence_integrity",
    )
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["execution"]["extension_forbidden_failure_classes"] == list(
        nonretryable_categories
    )
    runner = _load_script(
        "107_run_sr_v2_spatial_sensitivity_chain.py",
        "spatial_runner_retry_authority",
    )
    runner._require_retry_authority(
        {"status": "checkpointed", "retryable": True, "failure_category": None}
    )
    runner._require_retry_authority(
        {
            "status": "failed",
            "retryable": True,
            "failure_category": "transient_runtime",
        }
    )
    for category in nonretryable_categories:
        with pytest.raises(ValueError, match="explicitly transient"):
            runner._require_retry_authority(
                {"status": "failed", "retryable": False, "failure_category": category}
            )
        shutil.rmtree(tmp_path / "chains")
        write_status(
            1,
            {
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "chain_id": 1,
                "extension_epoch": 0,
                "job_attempt": 1,
                "status": "failed",
                "failure_category": category,
                "retryable": False,
            },
        )
        for chain_id in (2, 3, 4):
            write_status(
                chain_id,
                {
                    "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                    "chain_id": chain_id,
                    "extension_epoch": 0,
                    "job_attempt": 1,
                    "status": "completed",
                },
            )
        with pytest.raises(ValueError, match="explicitly transient retry"):
            select_retry_indexes(tmp_path, extension_epoch=0)

    shutil.rmtree(tmp_path / "chains")
    write_status(
        1,
        {
            "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
            "chain_id": 1,
            "extension_epoch": 0,
            "job_attempt": 3,
            "status": "failed",
            "failure_category": "transient_runtime",
            "retryable": True,
        },
    )
    for chain_id in (2, 3, 4):
        write_status(
            chain_id,
            {
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "chain_id": chain_id,
                "extension_epoch": 0,
                "job_attempt": 1,
                "status": "completed",
            },
        )
    with pytest.raises(ValueError, match="attempt four is forbidden"):
        select_retry_indexes(tmp_path, extension_epoch=0)

    shutil.rmtree(tmp_path / "chains")
    for chain_id in range(1, 5):
        write_status(
            chain_id,
            {
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "chain_id": chain_id,
                "extension_epoch": 0,
                "job_attempt": 1,
                "status": "completed",
                "iterations": 180_000,
                "retained_draws": 4_500,
            },
        )
    prior_paths = {
        "prior_pre_gate_manifest_sha256": tmp_path / "epochs/epoch_0/merge/pre_gate_manifest.json",
        "prior_independent_verification_sha256": tmp_path / "epochs/epoch_0/verification/independent_spatial_sensitivity_verification.json",
        "prior_release_manifest_sha256": tmp_path / "epochs/epoch_0/release/spatial_sensitivity_release_manifest.json",
    }
    for path in prior_paths.values():
        _write_json_sidecar(path, {"fixture": path.name})
    prior_hashes = {
        field: hashlib.sha256(path.read_bytes()).hexdigest()
        for field, path in prior_paths.items()
    }
    gate_path = tmp_path / "epochs/epoch_0/gate/gate_decision.json"
    _write_json_sidecar(
        gate_path,
        {
            "status": "HOLD",
            "passed": False,
            "reason": "convergence_only",
            "extension_eligible": True,
            "extension_epoch": 0,
            "preparation_identity": "b" * 64,
            "pre_gate_manifest_sha256": prior_hashes["prior_pre_gate_manifest_sha256"],
            "independent_verification_sha256": prior_hashes["prior_independent_verification_sha256"],
            "release_manifest_sha256": prior_hashes["prior_release_manifest_sha256"],
        },
    )
    unsigned = {
        "schema_id": "sr_v2_spatial_extension_authorization/v1",
        "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
        "from_extension_epoch": 0,
        "to_extension_epoch": 1,
        "reason_convergence_only": True,
        "reviewer": "independent-reviewer",
        "reviewed_utc": "2026-08-19T00:00:00Z",
        "prior_preparation_identity": "b" * 64,
        **prior_hashes,
        "prior_gate_decision_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest(),
    }
    authorization = {**unsigned, "authorization_sha256": canonical_sha256(unsigned)}
    _write_json_sidecar(
        tmp_path / "extension_authorization_epoch_1.json", authorization
    )
    extension = validate_extension_authorization(
        tmp_path, to_extension_epoch=1
    )
    assert extension["selected_array_indexes"] == [1, 2, 3, 4]
    assert extension["job_attempt"] == 1

    status_path = tmp_path / "chains/chain_04/chain_status.json"
    bad = json.loads(status_path.read_text(encoding="utf-8"))
    bad["retained_draws"] = 4_499
    write_status(4, bad)
    with pytest.raises(ValueError, match="Every prior-epoch chain"):
        validate_extension_authorization(tmp_path, to_extension_epoch=1)


def test_benchmark_thresholds_are_inclusive_and_one_ulp_fail_closed(
    tmp_path: Path,
) -> None:
    from bayes_constrained.spatial_pipeline import validate_benchmark_evidence

    report_path = tmp_path / "benchmark/benchmark_report.json"
    elapsed_at_limit = 65.0 * 3_600 * 2_000 / (180_000 * 1.2)
    report = {
        "schema_id": "sr_v2_spatial_benchmark/v1",
        "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
        "preparation_identity": "a" * 64,
        "target_fingerprint": "b" * 64,
        "launch_envelope_sha256": "c" * 64,
        "final_source_manifest_sha256": "d" * 64,
        "builder": "exact_prepared_public_chain",
        "array_index": 1,
        "iterations": 2_000,
        "elapsed_seconds": elapsed_at_limit,
        "iterations_per_second": 2_000 / elapsed_at_limit,
        "projection_overhead_factor": 1.2,
        "projected_hours": 65.0,
        "projected_hours_limit_inclusive": 65.0,
        "peak_rss_gib": 56.0,
        "peak_rss_gib_limit_inclusive": 56.0,
        "paired_chunk_draws": 250,
        "paired_chunk_scalar_rows": 17_750,
        "paired_chunk_bytes": 1_048_576,
        "paired_chunk_elapsed_seconds": 1.0,
        "paired_chunk_mib_per_second": 1.0,
        "paired_chunk_record_sha256": "e" * 64,
        "paired_chunk_builder": "actual_commit_spatial_draw_chunk",
        "paired_chunk_scientific_data": False,
        "passed": True,
        "scientific_draws_published": False,
        "submission_authorized": False,
    }
    _write_json_sidecar(report_path, report)
    validated = validate_benchmark_evidence(
        tmp_path,
        preparation_identity="a" * 64,
        target_fingerprints=["b" * 64],
        launch_envelope_sha256="c" * 64,
        final_source_manifest_sha256="d" * 64,
    )
    assert validated["report"]["projected_hours"] == 65.0

    report["projected_hours"] = float(np.nextafter(65.0, np.inf))
    _write_json_sidecar(report_path, report)
    with pytest.raises(ValueError, match="exceeds"):
        validate_benchmark_evidence(
            tmp_path,
            preparation_identity="a" * 64,
            target_fingerprints=["b" * 64],
            launch_envelope_sha256="c" * 64,
            final_source_manifest_sha256="d" * 64,
        )


def test_benchmark_entrypoint_executes_paired_chunk_without_science_publication(
    tmp_path: Path,
) -> None:
    runner = _load_script(
        "107_run_sr_v2_spatial_sensitivity_chain.py",
        "spatial_runner_benchmark_entrypoint",
    )
    runtime_root = tmp_path / "runtime"
    frame, design, identity, initial, _, _ = _tiny_spatial_runtime(runtime_root)
    output_base = tmp_path / "out"
    run_root = output_base / "sr-v2-spatial-sensitivity-20260818-v1"
    report_path = run_root / "benchmark/benchmark_report.json"
    validation = {
        "prepared_root": str(runtime_root),
        "manifest": {
            "preparation_identity": "a" * 64,
            "production_eligible": False,
            "chain_mapping": [
                {
                    "chain_id": chain_id,
                    "target_fingerprint": identity["target_fingerprint"],
                    "target_identity": identity,
                    "initial_checkpoint": initial.relative_to(runtime_root).as_posix(),
                }
                for chain_id in (1, 2, 3, 4)
            ],
        },
        "launch_envelope_sha256": "b" * 64,
        "final_source_manifest_sha256": "c" * 64,
    }

    def fake_executor(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "status": "checkpointed",
            "iteration": 2_000,
            "saved_draws": 0,
            "committed_chunks": [],
        }

    payload = runner.benchmark_prepared_target(
        root=tmp_path,
        output_path=report_path,
        output_base_override=output_base,
        prepared_validator=lambda *_args, **_kwargs: validation,
        runtime_loader=lambda *_args, **_kwargs: (frame, design, object()),
        chain_executor=fake_executor,
        elapsed_seconds_override=1.0,
        peak_rss_gib_override=1.0,
        bounded_test_mode=True,
    )
    assert payload["builder"] == "injected_bounded_test_benchmark"
    assert payload["paired_chunk_builder"] == "actual_commit_spatial_draw_chunk"
    assert payload["paired_chunk_draws"] == 250
    assert payload["paired_chunk_scientific_data"] is False
    assert payload["scientific_draws_published"] is False
    assert report_path.is_file() and report_path.with_name(
        report_path.name + ".sha256"
    ).is_file()
    assert not (run_root / "chains").exists()
    assert not list((run_root / "benchmark").glob(".benchmark-work-*"))


def test_isolated_verifier_ast_rejects_runtime_helpers_and_dynamic_execution() -> None:
    source = (ROOT / "scripts/109_gate_sr_v2_spatial_sensitivity.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    banned_modules = {
        "bayes_constrained.model",
        "bayes_constrained.sampler",
        "bayes_constrained.spatial_bym2",
        "bayes_constrained.diagnostics",
        "bayes_constrained.spatial_pipeline",
        "scripts.108_merge_sr_v2_spatial_sensitivity",
        "importlib",
        "runpy",
    }
    imported: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.add(node.func.id)
    assert not any(
        module in banned_modules or module.startswith("scripts.108_merge")
        for module in imported
    )
    assert calls.isdisjoint({"__import__", "eval", "exec"})

    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    first_call = main.body[0].value
    assert isinstance(first_call, ast.Call)
    assert isinstance(first_call.func, ast.Name)
    assert first_call.func.id == "_set_hold"


def test_bounded_merge_entrypoint_publishes_immutable_pre_gate_but_never_passes(
    tmp_path: Path,
) -> None:
    merge = _load_script(
        "108_merge_sr_v2_spatial_sensitivity.py", "spatial_merge_bounded"
    )
    frame, design, identity, _, _, _ = _tiny_spatial_runtime(tmp_path / "runtime")
    parameter_schema = identity["target"]["parameter_schema"]
    output = tmp_path / "out"
    run_root = output / "sr-v2-spatial-sensitivity-20260818-v1"
    statuses: list[dict[str, object]] = []
    for chain_id in range(1, 5):
        chain_root = run_root / f"chains/chain_{chain_id:02d}"
        artifact = chain_root / "evidence/dummy.txt"
        artifact.parent.mkdir(parents=True)
        artifact.write_text(f"chain {chain_id}\n", encoding="utf-8")
        status = {
            "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
            "status": "completed",
            "chain_id": chain_id,
            "array_index": chain_id,
            "extension_epoch": 0,
            "job_attempt": 1,
            "iterations": 180_000,
            "retained_draws": 4_500,
            "chunks": 18,
            "preparation_identity": "a" * 64,
            "chain_fingerprint": f"{chain_id:064x}",
            "target_fingerprint": "f" * 64,
            "failure_category": None,
            "retryable": False,
            "seeds": {
                "chain_seed": 74290 + chain_id,
                "allocation_initialization_seed": 74250 + chain_id,
                "spatial_initialization_seed": 74260 + chain_id,
            },
        }
        checkpoint = chain_root / "checkpoints/checkpoint_epoch_0_attempt_1_iter_180000000.json"
        _write_json_sidecar(
            checkpoint,
            {
                "schema_version": 2,
                "run_id": "sr-v2-spatial-sensitivity-20260818-v1",
                "chain_id": chain_id,
                "extension_epoch": 0,
                "target_fingerprint": status["target_fingerprint"],
                "chain_fingerprint": status["chain_fingerprint"],
            },
        )
        status["latest_checkpoint"] = checkpoint.relative_to(chain_root).as_posix()
        status["latest_checkpoint_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        status["artifact_sha256"] = {
            "evidence/dummy.txt": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            checkpoint.relative_to(chain_root).as_posix(): hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            checkpoint.with_name(checkpoint.name + ".sha256").relative_to(chain_root).as_posix(): hashlib.sha256(checkpoint.with_name(checkpoint.name + ".sha256").read_bytes()).hexdigest(),
        }
        _write_json_sidecar(
            chain_root / "attempts/epoch_0/attempt_1/status.json", status
        )
        _write_json_sidecar(chain_root / "chain_status.json", status)
        statuses.append(status)
    manifest = {
        "preparation_identity": "a" * 64,
        "launch_envelope_sha256": "b" * 64,
        "final_source_manifest_sha256": "c" * 64,
        "parameter_schema": parameter_schema,
        "chain_mapping": [
            {"target_fingerprint": f"{chain_id:064x}"}
            for chain_id in range(1, 5)
        ],
    }
    primary_dir = tmp_path / "outputs/scientific_reports_v2/production_8chain"
    primary_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "parameter": COMPARISON_ROWS,
            "posterior_mean": [1.1] * 6 + [0.1, -0.1],
            "credible_interval_lower_95": [0.8] * 6 + [-0.1, -0.3],
            "credible_interval_upper_95": [1.4] * 6 + [0.3, 0.1],
        }
    ).to_csv(primary_dir / "posterior_primary_summary.csv", index=False)

    draw_rows: list[dict[str, object]] = []
    spatial_chain: list[int] = []
    spatial_draw: list[int] = []
    for chain_id in range(1, 5):
        for draw_id in range(1, 3):
            spatial_chain.append(chain_id)
            spatial_draw.append(draw_id)
            for parameter in parameter_schema:
                value = 0.05
                if parameter == "sigma_county":
                    value = 0.2
                elif parameter == "phi_structured":
                    value = 0.5
                draw_rows.append(
                    {
                        "chain_id": chain_id,
                        "draw_id": draw_id,
                        "extension_epoch": 0,
                        "parameter": parameter,
                        "value": np.float64(value),
                    }
                )
    scalar = pd.DataFrame(draw_rows)
    spatial = {
        "chain_id": np.asarray(spatial_chain, dtype=np.int64),
        "extension_epoch": np.zeros(8, dtype=np.int64),
        "draw_id": np.asarray(spatial_draw, dtype=np.int64),
        "structured": np.zeros((8, 3), dtype=np.float64),
        "unstructured": np.full((8, 3), 0.1, dtype=np.float64),
    }
    diagnostics_rows = [
        {
            "parameter": parameter,
            "r_hat": 1.0,
            "ess_bulk": 500.0,
            "ess_tail": 500.0,
            "arviz_version": "1.2.0",
            "constraint_failures": 0,
        }
        for parameter in parameter_schema
    ]
    for county in design.spatial_graph.counties:
        diagnostics_rows.extend(
            {
                "parameter": f"{prefix}[{county}]",
                "r_hat": 1.0,
                "ess_bulk": 500.0,
                "ess_tail": 500.0,
                "arviz_version": "1.2.0",
                "constraint_failures": 0,
            }
            for prefix in (
                "spatial_structured",
                "spatial_unstructured",
                "county_combined",
            )
        )
    diagnostics = pd.DataFrame(diagnostics_rows)
    checkpoints = [
        {"proposed": {"mala": 36_000}, "accepted": {"mala": 20_000}}
        for _ in range(4)
    ]

    result = merge.merge_epoch(
        extension_epoch=0,
        root=tmp_path,
        config_path=CONFIG_PATH,
        output_base_override=output,
        prepared_validator=lambda *_args, **_kwargs: {"manifest": manifest},
        runtime_loader=lambda *_args: (frame, design, object()),
        merged_input_loader=lambda **_kwargs: (scalar, spatial, checkpoints),
        diagnostics_builder=lambda *_args, **_kwargs: diagnostics,
        benchmark_validator=lambda *_args, **_kwargs: {
            "report_sha256": "d" * 64
        },
        evidence_validator=lambda *_args, **_kwargs: {
            "count_constraint_failures": 0,
            "spatial_constraint_failures": 0,
            "ledger_sha256": "e" * 64,
        },
        bounded_test_mode=True,
    )
    assert result["builder"] == "injected_bounded_test_builder"
    assert result["bounded_test_mode"] is True
    assert result["production_shape"] is False
    assert not (run_root / "primary_vs_spatial.csv").exists()
    gate = json.loads(
        (run_root / "spatial_sensitivity_gate.json").read_text(encoding="utf-8")
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False

    candidate = run_root / "epochs/epoch_0/merge/primary_vs_spatial.candidate.csv"
    candidate.write_bytes(candidate.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="SHA-256"):
        merge.merge_epoch(
            extension_epoch=0,
            root=tmp_path,
            config_path=CONFIG_PATH,
            output_base_override=output,
            prepared_validator=lambda *_args, **_kwargs: {"manifest": manifest},
        )


def test_isolated_verifier_sets_hold_before_malformed_config(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py", "spatial_verifier_hold_first"
    )
    output = tmp_path / "out"
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("not: [valid", encoding="utf-8")
    with pytest.raises(Exception):
        verifier.independent_verify(
            extension_epoch=0,
            root=tmp_path,
            config_path=malformed,
            output_base_override=output,
        )
    gate = json.loads(
        (
            output
            / "sr-v2-spatial-sensitivity-20260818-v1/spatial_sensitivity_gate.json"
        ).read_text(encoding="utf-8")
    )
    assert gate["status"] == "HOLD"
    assert gate["passed"] is False
    failure = json.loads(
        (
            output
            / "sr-v2-spatial-sensitivity-20260818-v1/epochs/epoch_0/"
            "verification/independent_spatial_sensitivity_verification.json"
        ).read_text(encoding="utf-8")
    )
    assert failure["passed"] is False


def test_isolated_raw_chunk_and_terminal_count_checks_reject_semantic_tamper(
    tmp_path: Path,
) -> None:
    from bayes_constrained.spatial_bym2 import commit_spatial_draw_chunk

    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py", "spatial_verifier_raw_adversarial"
    )
    frame, design, identity, _, _, _ = _tiny_spatial_runtime(tmp_path / "runtime")
    graph = design.spatial_graph
    parameter_schema = identity["target"]["parameter_schema"]
    draw_ids = np.arange(1, 251, dtype=np.int64)
    values = np.zeros(250 * len(parameter_schema), dtype=np.float64)
    for name, replacement in (("sigma_county", 1.0), ("phi_structured", 0.5)):
        values[np.tile(np.asarray(parameter_schema) == name, 250)] = replacement
    scalar = pd.DataFrame(
        {
            "chain_id": np.ones(len(values), dtype=np.int64),
            "draw_id": np.repeat(draw_ids, len(parameter_schema)),
            "extension_epoch": np.zeros(len(values), dtype=np.int64),
            "parameter": parameter_schema * 250,
            "value": values,
        }
    )
    chunk_root = tmp_path / "chunk"
    record = commit_spatial_draw_chunk(
        chunk_root,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=parameter_schema,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=np.zeros((250, len(graph.counties)), dtype=np.float64),
        unstructured=np.zeros((250, len(graph.counties)), dtype=np.float64),
    )
    checked, arrays = verifier._validate_raw_chunk(
        chunk_root=chunk_root,
        record=record,
        chain_id=1,
        chunk_id=1,
        parameter_schema=parameter_schema,
        counties=graph.counties,
        labels=graph.component_id,
        graph_contract_sha256=graph.contract_sha256,
    )
    assert len(checked) == 250 * len(parameter_schema)
    assert arrays["structured"].shape == (250, 3)
    verifier._validate_terminal_counts(
        frame["latent_count"].to_numpy(dtype=np.int64), frame
    )
    bad_y = frame["latent_count"].to_numpy(dtype=np.int64).copy()
    bad_y[0] += 1
    with pytest.raises(ValueError, match="totals|bounds|status"):
        verifier._validate_terminal_counts(bad_y, frame)

    scalar_path = chunk_root / record["scalar_path"]
    corrupted = pd.read_parquet(scalar_path)
    corrupted = pd.concat([corrupted, corrupted.iloc[[0]]], ignore_index=True)
    corrupted.to_parquet(scalar_path, index=False)
    tampered_record = {**record, "scalar_sha256": hashlib.sha256(scalar_path.read_bytes()).hexdigest()}
    with pytest.raises(ValueError, match="scalar chunk"):
        verifier._validate_raw_chunk(
            chunk_root=chunk_root,
            record=tampered_record,
            chain_id=1,
            chunk_id=1,
            parameter_schema=parameter_schema,
            counties=graph.counties,
            labels=graph.component_id,
            graph_contract_sha256=graph.contract_sha256,
        )

    npz_root = tmp_path / "chunk-npz"
    npz_record = commit_spatial_draw_chunk(
        npz_root,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=parameter_schema,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=np.zeros((250, len(graph.counties)), dtype=np.float64),
        unstructured=np.zeros((250, len(graph.counties)), dtype=np.float64),
    )
    npz_path = npz_root / npz_record["spatial_path"]
    with np.load(npz_path, allow_pickle=False) as archive:
        npz_arrays = {name: archive[name].copy() for name in archive.files}
    npz_arrays["structured"] = npz_arrays["structured"].astype(np.float32)
    np.savez(npz_path, **npz_arrays)
    npz_tampered = {
        **npz_record,
        "spatial_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest(),
    }
    with pytest.raises(ValueError, match="spatial chunk exact"):
        verifier._validate_raw_chunk(
            chunk_root=npz_root,
            record=npz_tampered,
            chain_id=1,
            chunk_id=1,
            parameter_schema=parameter_schema,
            counties=graph.counties,
            labels=graph.component_id,
            graph_contract_sha256=graph.contract_sha256,
        )


def test_isolated_semantic_summary_validators_reject_single_cell_corruption(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_summary_adversarial",
    )
    diagnostics = pd.DataFrame(
        {
            "parameter": [*COMPARISON_ROWS, "sigma_county", "phi_structured"],
            "r_hat": [1.0] * 10,
            "ess_bulk": [500.0] * 10,
            "ess_tail": [500.0] * 10,
            "arviz_version": ["1.2.0"] * 10,
            "constraint_failures": [0] * 10,
        }
    )
    diagnostics_path = tmp_path / "spatial_diagnostics.csv"
    diagnostics.to_csv(diagnostics_path, index=False, lineterminator="\n")
    verifier._validate_recorded_csv(
        diagnostics_path, diagnostics, "Recorded diagnostics"
    )
    corrupted_diagnostics = diagnostics.copy()
    corrupted_diagnostics.loc[0, "ess_bulk"] = 499.0
    corrupted_diagnostics.to_csv(diagnostics_path, index=False, lineterminator="\n")
    with pytest.raises(ValueError, match="Recorded diagnostics"):
        verifier._validate_recorded_csv(
            diagnostics_path, diagnostics, "Recorded diagnostics"
        )

    scalar = pd.DataFrame(
        [
            {
                "chain_id": chain,
                "draw_id": draw,
                "parameter": parameter,
                "value": value,
            }
            for chain in (1, 2)
            for draw in (1, 2)
            for parameter, value in (("sigma_county", 1.0), ("phi_structured", 0.5))
        ]
    )
    keys = [(chain, draw) for chain in (1, 2) for draw in (1, 2)]
    spatial = {
        "chain_id": np.asarray([chain for chain, _ in keys], dtype=np.int64),
        "draw_id": np.asarray([draw for _, draw in keys], dtype=np.int64),
        "structured": np.zeros((4, 1), dtype=np.float64),
        "unstructured": np.asarray([[0.0], [1.0], [2.0], [3.0]], dtype=np.float64),
    }
    county_diagnostics = pd.DataFrame(
        {
            "parameter": ["county_combined[00001]"],
            "r_hat": [1.0],
            "ess_bulk": [500.0],
            "ess_tail": [500.0],
        }
    )
    county = verifier._county_summary(
        scalar,
        spatial,
        county_diagnostics,
        ["00001"],
        np.asarray([0], dtype=np.int64),
    )
    county_path = tmp_path / "county_effect_summary.csv"
    county.to_csv(county_path, index=False, lineterminator="\n")
    verifier._validate_recorded_csv(
        county_path,
        county,
        "County-effect summary",
        dtype={"county_fips": str},
    )
    corrupted_county = county.copy()
    corrupted_county.loc[0, "combined_mean"] += 0.125
    corrupted_county.to_csv(county_path, index=False, lineterminator="\n")
    with pytest.raises(ValueError, match="County-effect summary"):
        verifier._validate_recorded_csv(
            county_path,
            county,
            "County-effect summary",
            dtype={"county_fips": str},
        )

    acceptance = verifier._acceptance_summary(
        [{"chain_id": 1}],
        [{"proposed": {"mala": 2}, "accepted": {"mala": 1}}],
    )
    acceptance_path = tmp_path / "acceptance_summary.csv"
    acceptance.to_csv(acceptance_path, index=False, lineterminator="\n")
    verifier._validate_recorded_csv(
        acceptance_path, acceptance, "Acceptance summary"
    )
    corrupted_acceptance = acceptance.copy()
    corrupted_acceptance.loc[0, "accepted"] = 2
    corrupted_acceptance.to_csv(acceptance_path, index=False, lineterminator="\n")
    with pytest.raises(ValueError, match="Acceptance summary"):
        verifier._validate_recorded_csv(
            acceptance_path, acceptance, "Acceptance summary"
        )

    constraint = verifier._constraint_summary(0)
    constraint_path = tmp_path / "constraint_summary.json"
    constraint_path.write_text(json.dumps(constraint), encoding="utf-8")
    verifier._validate_recorded_json(
        constraint_path, constraint, "Constraint summary"
    )
    constraint_path.write_text(
        json.dumps({**constraint, "count_constraint_failures": 1}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Constraint summary"):
        verifier._validate_recorded_json(
            constraint_path, constraint, "Constraint summary"
        )

    diagnostics_summary = verifier._diagnostics_summary(diagnostics, 0)
    diagnostics_summary_path = tmp_path / "spatial_diagnostics_summary.json"
    diagnostics_summary_path.write_text(
        json.dumps(diagnostics_summary), encoding="utf-8"
    )
    verifier._validate_recorded_json(
        diagnostics_summary_path, diagnostics_summary, "Diagnostics summary"
    )
    diagnostics_summary_path.write_text(
        json.dumps({**diagnostics_summary, "rows": 9}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Diagnostics summary"):
        verifier._validate_recorded_json(
            diagnostics_summary_path, diagnostics_summary, "Diagnostics summary"
        )


def test_isolated_publications_and_pass_manifests_are_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py", "spatial_verifier_publication_adversarial"
    )
    destination = tmp_path / "immutable"
    first = {"schema_id": "fixture/v1", "value": 1}
    verifier._publish_immutable_json(destination, "record.json", first)
    original = (destination / "record.json").read_bytes()
    with pytest.raises(FileExistsError):
        verifier._publish_immutable_json(destination, "record.json", {**first, "value": 2})
    assert (destination / "record.json").read_bytes() == original

    crash_destination = tmp_path / "crash"
    monkeypatch.setattr(
        verifier.os,
        "rename",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected crash")),
    )
    with pytest.raises(OSError, match="injected crash"):
        verifier._publish_immutable_json(crash_destination, "record.json", first)
    assert not crash_destination.exists()
    assert not list(tmp_path.glob(".crash-*"))

    forged = {
        field: False if field == "passed" else None
        for field in verifier.VERIFICATION_EXACT_FIELDS
    }
    forged.update(
        {
            "schema_id": "sr_v2_independent_spatial_sensitivity_verification/v1",
            "run_id": verifier.RUN_ID,
            "model_id": verifier.MODEL_ID,
            "extension_epoch": 0,
            "preparation_identity": "a" * 64,
            "launch_envelope_sha256": "b" * 64,
            "final_source_manifest_sha256": "c" * 64,
            "benchmark_report_sha256": "d" * 64,
            "pre_gate_manifest_sha256": "e" * 64,
            "passed": True,
            "submission_authorized": False,
        }
    )
    with pytest.raises(ValueError, match="group"):
        verifier._validate_passed_verification(
            forged,
            extension_epoch=0,
            prepared={
                "preparation_identity": "a" * 64,
                "launch_envelope_sha256": "b" * 64,
                "final_source_manifest_sha256": "c" * 64,
                "input_manifest_sha256": "f" * 64,
                "protected_tree_manifest_sha256": "1" * 64,
            },
            benchmark_hash="d" * 64,
            pre_gate_hash="e" * 64,
        )
    release_root = tmp_path / "release-root"
    candidate = release_root / "epochs/epoch_0/merge/primary_vs_spatial.candidate.csv"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"candidate\n")
    snapshot = verifier._verification_artifact_snapshot(release_root, 0)
    snapshot_hash = verifier._canonical_sha(snapshot)
    inventory = verifier._release_artifact_inventory(release_root, 0)
    release = {
        "schema_id": "sr_v2_spatial_sensitivity_release_manifest/v1",
        "run_id": verifier.RUN_ID,
        "model_id": verifier.MODEL_ID,
        "extension_epoch": 0,
        "preparation_identity": "a" * 64,
        "launch_envelope_sha256": "b" * 64,
        "final_source_manifest_sha256": "c" * 64,
        "benchmark_report_sha256": "d" * 64,
        "pre_gate_manifest_sha256": "e" * 64,
        "independent_verification_sha256": "f" * 64,
        "verification_convergence_passed": True,
        "verification_artifact_snapshot": snapshot,
        "verification_artifact_snapshot_sha256": snapshot_hash,
        "artifacts": inventory,
        "artifact_inventory_sha256": verifier._canonical_sha(inventory),
        "planned_outputs": {
            "primary_vs_spatial.csv": {
                "source": candidate.relative_to(release_root).as_posix(),
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            }
        },
        "excludes": ["primary_vs_spatial.csv", "spatial_sensitivity_gate.json"],
        "submission_authorized": False,
    }
    prepared = {
        "preparation_identity": "a" * 64,
        "launch_envelope_sha256": "b" * 64,
        "final_source_manifest_sha256": "c" * 64,
    }
    verifier._validate_release(
        release,
        run_root=release_root,
        extension_epoch=0,
        prepared=prepared,
        benchmark_hash="d" * 64,
        pre_gate_hash="e" * 64,
        verification_hash="f" * 64,
        verification_snapshot=snapshot,
        verification_snapshot_hash=snapshot_hash,
        candidate_relative=candidate.relative_to(release_root).as_posix(),
        candidate_hash=hashlib.sha256(candidate.read_bytes()).hexdigest(),
    )
    (release_root / "orphan.bin").write_bytes(b"extra")
    with pytest.raises(ValueError, match="coverage"):
        verifier._validate_release(
            release,
            run_root=release_root,
            extension_epoch=0,
            prepared=prepared,
            benchmark_hash="d" * 64,
            pre_gate_hash="e" * 64,
            verification_hash="f" * 64,
            verification_snapshot=snapshot,
            verification_snapshot_hash=snapshot_hash,
            candidate_relative=candidate.relative_to(release_root).as_posix(),
            candidate_hash=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        )


def test_runner_recovers_highest_fully_valid_checkpoint(
    tmp_path: Path,
) -> None:
    from bayes_constrained.model import active_prior_specification
    from bayes_constrained.sampler import run_spatial_mcmc_chain

    runner = _load_script(
        "107_run_sr_v2_spatial_sensitivity_chain.py", "spatial_runner_recovery"
    )
    frame, design, identity, initial, checkpoint_dir, chunk_dir = _tiny_spatial_runtime(
        tmp_path / "runtime"
    )
    result = run_spatial_mcmc_chain(
        frame,
        design=design,
        identity=identity,
        checkpoint_path=initial,
        checkpoint_dir=checkpoint_dir,
        chunk_dir=chunk_dir,
        job_attempt=1,
        settings={
            **runner.FROZEN_CHAIN_SETTINGS,
            "count_move_sweeps_per_iter": 0.0,
            "max_count_proposals_per_iter": 1,
            "blocked_refresh_frequency": 0,
        },
        checkpoint_every=5,
        max_runtime_minutes=None,
        stop_requested=lambda iteration: iteration >= 5,
    )
    recovered_path, recovered = runner._recover_latest_valid_checkpoint(
        checkpoint_dir=checkpoint_dir,
        fallback=initial,
        identity=identity,
        extension_epoch=0,
        frame=frame,
        design=design,
        prior=active_prior_specification(),
        chunk_dir=chunk_dir,
    )
    assert recovered_path == Path(result["latest_checkpoint"]).resolve()
    assert recovered["iteration"] == 5


@pytest.mark.parametrize("status,passed", [("PASS", True), ("HOLD", False)])
def test_gate_decision_crash_after_immutable_publish_resumes_identically(
    tmp_path: Path,
    status: str,
    passed: bool,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        f"spatial_gate_crash_{status.lower()}",
    )
    run_root = tmp_path / "run"
    initial_hold = {
        "schema_id": "sr_v2_spatial_sensitivity_gate/v1",
        "run_id": verifier.RUN_ID,
        "status": "HOLD",
        "passed": False,
        "stage": "gate",
        "reason": "gate_checks_running",
        "submission_authorized": False,
    }
    verifier._atomic_json(run_root / "spatial_sensitivity_gate.json", initial_hold)
    decision = {
        "schema_id": "sr_v2_spatial_sensitivity_gate/v1",
        "run_id": verifier.RUN_ID,
        "model_id": verifier.MODEL_ID,
        "extension_epoch": 0,
        "preparation_identity": "a" * 64,
        "benchmark_report_sha256": "b" * 64,
        "pre_gate_manifest_sha256": "c" * 64,
        "release_manifest_sha256": "d" * 64,
        "independent_verification_sha256": "e" * 64,
        "submission_authorized": False,
        "interpretation_boundary": "fixture",
        "status": status,
        "passed": passed,
        "action": "freeze_spatial_sensitivity" if passed else "reviewed_extension_required",
        "reason": "all_fail_closed_criteria_passed" if passed else "convergence_only",
        "extension_eligible": not passed,
        "final_comparison_sha256": "f" * 64 if passed else None,
    }

    def crash_pointer(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected crash after immutable decision")

    with pytest.raises(OSError, match="injected crash"):
        verifier._commit_gate_decision(
            run_root, 0, decision, pointer_writer=crash_pointer
        )
    immutable = run_root / "epochs/epoch_0/gate/gate_decision.json"
    assert immutable.is_file()
    assert json.loads(
        (run_root / "spatial_sensitivity_gate.json").read_text(encoding="utf-8")
    ) == initial_hold

    verifier._commit_gate_decision(run_root, 0, decision)
    assert json.loads(
        (run_root / "spatial_sensitivity_gate.json").read_text(encoding="utf-8")
    ) == decision
    with pytest.raises(FileExistsError, match="Conflicting immutable"):
        verifier._commit_gate_decision(
            run_root, 0, {**decision, "reason": "conflicting-decision"}
        )
    assert json.loads(immutable.read_text(encoding="utf-8")) == decision


def test_verifier_snapshot_rejects_coherent_post_verifier_spatial_rewrite(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_gate_snapshot_toctou",
    )
    run_root = tmp_path / "run"
    (run_root / "prepared").mkdir(parents=True)
    (run_root / "prepared/prepared.bin").write_bytes(b"prepared")
    spatial_path = run_root / "chains/chain_01/chunks/spatial_chunk_000001.npz"
    spatial_path.parent.mkdir(parents=True)
    np.savez(
        spatial_path,
        chain_id=np.asarray(1, dtype=np.int64),
        extension_epoch=np.asarray(0, dtype=np.int64),
        draw_id=np.arange(1, 251, dtype=np.int64),
        structured=np.zeros((250, 3), dtype=np.float64),
        unstructured=np.zeros((250, 3), dtype=np.float64),
    )
    status_paths = (
        run_root / "chains/chain_01/chain_status.json",
        run_root / "chains/chain_01/attempts/epoch_0/attempt_1/status.json",
    )
    status = {
        "schema_id": "fixture/v1",
        "artifact_sha256": {
            spatial_path.relative_to(run_root / "chains/chain_01").as_posix(): hashlib.sha256(
                spatial_path.read_bytes()
            ).hexdigest()
        },
    }
    for path in status_paths:
        _write_json_sidecar(path, status)
    merge = run_root / "epochs/epoch_0/merge/pre_gate_manifest.json"
    _write_json_sidecar(merge, {"schema_id": "fixture/v1"})
    snapshot = verifier._verification_artifact_snapshot(run_root, 0)
    verification = {
        "artifact_snapshot": snapshot,
        "artifact_snapshot_sha256": verifier._canonical_sha(snapshot),
    }
    assert verifier._validate_verification_snapshot(
        run_root, 0, verification
    ) == snapshot

    with np.load(spatial_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays["unstructured"][0, 0] = 0.125
    np.savez(spatial_path, **arrays)
    new_hash = hashlib.sha256(spatial_path.read_bytes()).hexdigest()
    coherent = {
        **status,
        "artifact_sha256": {
            spatial_path.relative_to(run_root / "chains/chain_01").as_posix(): new_hash
        },
    }
    for path in status_paths:
        _write_json_sidecar(path, coherent)
    verifier._set_hold(
        tmp_path,
        reason="gate_checks_running",
        stage="gate",
        extension_epoch=0,
        output_base_override=tmp_path,
    )
    with pytest.raises(ValueError, match="changed after independent verification"):
        verifier._validate_verification_snapshot(run_root, 0, verification)
    gate = json.loads(
        (tmp_path / verifier.RUN_ID / "spatial_sensitivity_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False
    source = (ROOT / "scripts/109_gate_sr_v2_spatial_sensitivity.py").read_text(
        encoding="utf-8"
    )
    assert source.count("_verify_merged_semantics(") >= 3


def test_isolated_chunk_custody_accepts_retry_extension_and_immediate_failure_growth(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_chunk_history_growth",
    )
    transition = getattr(verifier, "_validate_chunk_custody_transition", None)
    validate_current = getattr(verifier, "_validate_current_chunk_manifest", None)
    assert callable(transition), "missing independent historical chunk transition validator"
    assert callable(validate_current), "missing exact current chunk-manifest validator"
    chunk_root, records, graph, parameters = _commit_tiny_spatial_chunk_history(
        tmp_path, chunk_count=30
    )

    def inventory(prefix: list[dict[str, object]]) -> dict[str, str]:
        result: dict[str, str] = {}
        for record in prefix:
            result[f"chunks/{record['scalar_path']}"] = str(record["scalar_sha256"])
            result[f"chunks/{record['spatial_path']}"] = str(record["spatial_sha256"])
        if prefix:
            result["chunks/spatial_chunk_manifest.json"] = hashlib.sha256(
                verifier._canonical_bytes(
                    {
                        "schema_id": "sr_v2_spatial_chunk_manifest/v1",
                        "records": prefix,
                    }
                )
            ).hexdigest()
        return result

    context = {
        "chunk_root": chunk_root,
        "chain_id": 1,
        "parameter_schema": parameters,
        "counties": graph.counties,
        "labels": graph.component_id,
        "graph_contract_sha256": graph.contract_sha256,
    }
    cache: set[tuple[object, ...]] = set()
    # Ordinary retry: A1 acknowledges one committed pair and A2 appends one.
    transition(
        previous_records=[],
        current_records=records[:1],
        previous_inventory={},
        current_inventory=inventory(records[:1]),
        validated_records=cache,
        **context,
    )
    transition(
        previous_records=records[:1],
        current_records=records[:2],
        previous_inventory=inventory(records[:1]),
        current_inventory=inventory(records[:2]),
        validated_records=cache,
        **context,
    )
    # Extension transition: epoch 0's 18 chunks are an immutable prefix of 30.
    transition(
        previous_records=records[:18],
        current_records=records[:30],
        previous_inventory=inventory(records[:18]),
        current_inventory=inventory(records[:30]),
        validated_records=cache,
        **context,
    )
    # Immediate A2 failure makes no progress; A3 may then append from that prefix.
    transition(
        previous_records=records[:1],
        current_records=records[:1],
        previous_inventory=inventory(records[:1]),
        current_inventory=inventory(records[:1]),
        validated_records=cache,
        **context,
    )
    transition(
        previous_records=records[:1],
        current_records=records[:2],
        previous_inventory=inventory(records[:1]),
        current_inventory=inventory(records[:2]),
        validated_records=cache,
        **context,
    )
    validate_current(chunk_root=chunk_root, records=records)


def test_isolated_chunk_custody_rejects_manifest_prefix_hash_and_raw_splices(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_chunk_history_adversarial",
    )
    transition = getattr(verifier, "_validate_chunk_custody_transition", None)
    validate_current = getattr(verifier, "_validate_current_chunk_manifest", None)
    assert callable(transition), "missing independent historical chunk transition validator"
    assert callable(validate_current), "missing exact current chunk-manifest validator"
    chunk_root, records, graph, parameters = _commit_tiny_spatial_chunk_history(
        tmp_path / "history", chunk_count=2
    )

    def inventory(prefix: list[dict[str, object]]) -> dict[str, str]:
        result = {
            f"chunks/{record['scalar_path']}": str(record["scalar_sha256"])
            for record in prefix
        }
        result.update(
            {
                f"chunks/{record['spatial_path']}": str(record["spatial_sha256"])
                for record in prefix
            }
        )
        if prefix:
            result["chunks/spatial_chunk_manifest.json"] = hashlib.sha256(
                verifier._canonical_bytes(
                    {
                        "schema_id": "sr_v2_spatial_chunk_manifest/v1",
                        "records": prefix,
                    }
                )
            ).hexdigest()
        return result

    context = {
        "chunk_root": chunk_root,
        "chain_id": 1,
        "parameter_schema": parameters,
        "counties": graph.counties,
        "labels": graph.component_id,
        "graph_contract_sha256": graph.contract_sha256,
        "validated_records": set(),
    }
    bad_historical = json.loads(json.dumps(records[:1]))
    bad_historical[0]["scalar_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="Raw chunk bytes changed"):
        transition(
            previous_records=[],
            current_records=bad_historical,
            previous_inventory={},
            current_inventory=inventory(bad_historical),
            **context,
        )
    later_splice = json.loads(json.dumps(records[:2]))
    later_splice[0]["spatial_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="prefix"):
        transition(
            previous_records=records[:1],
            current_records=later_splice,
            previous_inventory=inventory(records[:1]),
            current_inventory=inventory(later_splice),
            **context,
        )
    wrong_manifest = inventory(records[:1])
    wrong_manifest["chunks/spatial_chunk_manifest.json"] = "0" * 64
    with pytest.raises(ValueError, match="manifest"):
        transition(
            previous_records=[],
            current_records=records[:1],
            previous_inventory={},
            current_inventory=wrong_manifest,
            **context,
        )
    previous_inventory = {**inventory(records[:1]), "authority.bin": "a" * 64}
    current_inventory = {**inventory(records[:2]), "authority.bin": "b" * 64}
    with pytest.raises(ValueError, match="prior artifact"):
        transition(
            previous_records=records[:1],
            current_records=records[:2],
            previous_inventory=previous_inventory,
            current_inventory=current_inventory,
            **context,
        )

    manifest = chunk_root / "spatial_chunk_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_id": "sr_v2_spatial_chunk_manifest/v1",
                "records": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="canonical|manifest"):
        validate_current(chunk_root=chunk_root, records=records)

    raw_root, raw_records, raw_graph, raw_parameters = (
        _commit_tiny_spatial_chunk_history(tmp_path / "raw", chunk_count=1)
    )
    scalar_path = raw_root / str(raw_records[0]["scalar_path"])
    scalar = pd.read_parquet(scalar_path)
    pd.concat([scalar, scalar.iloc[[0]]], ignore_index=True).to_parquet(
        scalar_path, index=False
    )
    coherent = json.loads(json.dumps(raw_records))
    coherent[0]["scalar_sha256"] = hashlib.sha256(
        scalar_path.read_bytes()
    ).hexdigest()
    (raw_root / "spatial_chunk_manifest.json").write_bytes(
        verifier._canonical_bytes(
            {
                "schema_id": "sr_v2_spatial_chunk_manifest/v1",
                "records": coherent,
            }
        )
    )
    with pytest.raises(ValueError, match="scalar chunk"):
        transition(
            chunk_root=raw_root,
            previous_records=[],
            current_records=coherent,
            previous_inventory={},
            current_inventory=inventory(coherent),
            chain_id=1,
            parameter_schema=raw_parameters,
            counties=raw_graph.counties,
            labels=raw_graph.component_id,
            graph_contract_sha256=raw_graph.contract_sha256,
            validated_records=set(),
        )
    verifier._set_hold(
        tmp_path,
        reason="independent_verification_not_passed",
        stage="independent_verification",
        extension_epoch=0,
        output_base_override=tmp_path,
    )
    gate = json.loads(
        (tmp_path / verifier.RUN_ID / "spatial_sensitivity_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False


@pytest.mark.parametrize(
    ("field", "alias"),
    (
        ("chain_id", True),
        ("extension_epoch", False),
        ("chunk_id", True),
        ("draw_start", True),
        ("draw_end", True),
        ("draw_count", True),
        ("county_count", True),
    ),
)
def test_isolated_raw_chunk_rejects_bool_alias_for_every_integer_field(
    tmp_path: Path, field: str, alias: bool
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        f"spatial_verifier_chunk_bool_{field}",
    )
    chunk_root, records, graph, parameters = _commit_tiny_spatial_chunk_history(
        tmp_path, chunk_count=1
    )
    tampered = dict(records[0])
    tampered[field] = alias
    with pytest.raises(ValueError, match="exact integer"):
        verifier._validate_raw_chunk(
            chunk_root=chunk_root,
            record=tampered,
            chain_id=1,
            chunk_id=1,
            parameter_schema=parameters,
            counties=graph.counties,
            labels=graph.component_id,
            graph_contract_sha256=graph.contract_sha256,
        )


def test_isolated_checkpoint_chunk_rejects_bool_alias_for_every_integer_field(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_checkpoint_chunk_bool_aliases",
    )
    frame, design, identity, initial, _, _ = _tiny_spatial_runtime(
        tmp_path / "checkpoint"
    )
    _, records, _, _ = _commit_tiny_spatial_chunk_history(
        tmp_path / "raw", chunk_count=1
    )
    checkpoint = verifier._load_canonical_checkpoint(initial)
    iteration = 52_500
    checkpoint.update(
        {
            "iteration": iteration,
            "saved_draws": 250,
            "next_draw_id": 251,
            "committed_chunks": records,
            "output_positions": {
                "scalar_rows": 250 * len(identity["target"]["parameter_schema"]),
                "spatial_draws": 250,
            },
        }
    )
    for name in (
        "beta",
        "state",
        "year",
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
        "spatial_hyperparameters",
    ):
        checkpoint["proposed"][name] = iteration
    checkpoint["proposed"].update(
        {
            "transfer": iteration,
            "blocked_refresh": (iteration // 25) * 12,
            "mala": iteration // 5,
        }
    )
    checkpoint["adaptation_state"].update(
        {
            "attempted": iteration // 5,
            "accepted": 0,
            "window_attempted": 0,
            "window_accepted": 0,
            "windows_completed": 90,
            "adaptation_frozen": True,
        }
    )
    seeds = {
        "chain_seed": 74291,
        "allocation_initialization_seed": 74251,
        "spatial_initialization_seed": 74261,
    }
    validation = {
        "identity": identity,
        "seeds": seeds,
        "expected_epoch": 0,
        "expected_attempt": 1,
        "expected_iteration": iteration,
        "expected_draws": 250,
        "expected_chunks": 1,
        "row_count": len(frame),
        "county_count": len(design.spatial_graph.counties),
        "labels": design.spatial_graph.component_id,
        "expected_y": frame["latent_count"].to_numpy(dtype=np.int64),
        "count_moves_per_iteration": 1,
        "blocked_refresh_frequency": 25,
        "blocked_refresh_attempts": 12,
    }
    verifier._validate_checkpoint_payload(checkpoint, **validation)
    aliases = {
        "chain_id": True,
        "extension_epoch": False,
        "chunk_id": True,
        "draw_start": True,
        "draw_end": True,
        "draw_count": True,
        "county_count": True,
    }
    for field, alias in aliases.items():
        tampered = json.loads(json.dumps(checkpoint))
        tampered["committed_chunks"][0][field] = alias
        with pytest.raises(ValueError, match="exact integer"):
            verifier._validate_checkpoint_payload(tampered, **validation)


def test_isolated_schedule_rejects_rehashed_bool_aliases_in_all_nested_integers(
    tmp_path: Path,
) -> None:
    verifier = _load_script(
        "109_gate_sr_v2_spatial_sensitivity.py",
        "spatial_verifier_nested_schedule_bool_aliases",
    )
    assertion_template: dict[str, object] = {
        "schema_id": "sr_v2_spatial_retained_assertion/v1",
        "chain_id": 1,
        "draw_id": 1,
        "cumulative_iteration": 45_030,
        "extension_epoch": 0,
        "chunk_id": 1,
        "capture_order": "after_latent_target_base6_hyper_and_scheduled_mala",
        "count_constraints_asserted": True,
        "spatial_constraints_asserted": True,
        "latent_y_sha256": "1" * 64,
        "structured_effect_sha256": "2" * 64,
    }
    evidence_template: dict[str, object] = {
        "schema_id": "sr_v2_spatial_attempt_evidence/v1",
        "run_id": verifier.RUN_ID,
        "chain_id": 1,
        "extension_epoch": 0,
        "job_attempt": 1,
        "start_saved_draws": 0,
        "end_saved_draws": 1,
        "record_count": 1,
        "ledger_path": "retained_assertions.jsonl",
        "ledger_sha256": "",
        "evidence_builder": "actual_public_chain_loop",
        "production_executor": True,
        "capture_order": "after_latent_target_base6_hyper_and_scheduled_mala",
        "count_constraint_failures": 0,
        "spatial_constraint_failures": 0,
        "historical_latent_y_stored": False,
        "independent_historical_y_reconstruction_possible": False,
        "verification_boundary": (
            "The verifier checks the exact retained schedule and in-loop assertion "
            "evidence but cannot independently reconstruct historical latent y."
        ),
        "resume_from": {},
    }

    def publish(
        case_root: Path,
        *,
        evidence_changes: dict[str, object] | None = None,
        assertion_changes: dict[str, object] | None = None,
        status_records: object = 1,
    ) -> tuple[Path, dict[str, object], list[tuple[int, int, Path, dict[str, object]]]]:
        chain_root = case_root / "chain"
        evidence_root = chain_root / "evidence/epoch_0/attempt_1"
        assertion = {**assertion_template, **(assertion_changes or {})}
        assertion["assertion_sha256"] = verifier._canonical_sha(
            {
                key: value
                for key, value in assertion.items()
                if key != "assertion_sha256"
            }
        )
        ledger_payload = verifier._canonical_bytes(assertion) + b"\n"
        evidence_root.mkdir(parents=True, exist_ok=True)
        ledger = evidence_root / "retained_assertions.jsonl"
        ledger.write_bytes(ledger_payload)
        evidence = {**evidence_template, **(evidence_changes or {})}
        evidence["ledger_sha256"] = hashlib.sha256(ledger_payload).hexdigest()
        evidence_path = evidence_root / "attempt_evidence.json"
        _write_json_sidecar(evidence_path, evidence)
        status = {
            "executor_builder": "exact_public_chain_loop",
            "resume_from": {},
            "retained_draws": 1,
            "retained_assertion_evidence": {
                "records": status_records,
                "ledger_sha256": hashlib.sha256(ledger_payload).hexdigest(),
                "manifest_sha256": {
                    evidence_path.relative_to(chain_root).as_posix(): hashlib.sha256(
                        evidence_path.read_bytes()
                    ).hexdigest()
                },
                "historical_latent_y_stored": False,
                "independent_historical_y_reconstruction_possible": False,
            },
        }
        status_path = chain_root / "attempts/epoch_0/attempt_1/status.json"
        _write_json_sidecar(status_path, status)
        return chain_root, status, [(0, 1, status_path, status)]

    baseline_root, baseline_status, baseline_history = publish(
        tmp_path / "baseline"
    )
    assert verifier._verify_schedule(
        baseline_root, 1, 0, 1, baseline_status, baseline_history
    )["records"] == 1

    evidence_aliases = {
        "chain_id": True,
        "extension_epoch": False,
        "job_attempt": True,
        "start_saved_draws": False,
        "end_saved_draws": True,
        "record_count": True,
        "count_constraint_failures": False,
        "spatial_constraint_failures": False,
    }
    for field, alias in evidence_aliases.items():
        chain_root, status, history = publish(
            tmp_path / f"evidence-{field}", evidence_changes={field: alias}
        )
        with pytest.raises(ValueError, match="exact integer"):
            verifier._verify_schedule(chain_root, 1, 0, 1, status, history)

    assertion_aliases = {
        "chain_id": True,
        "draw_id": True,
        "cumulative_iteration": True,
        "extension_epoch": False,
        "chunk_id": True,
    }
    for field, alias in assertion_aliases.items():
        chain_root, status, history = publish(
            tmp_path / f"assertion-{field}", assertion_changes={field: alias}
        )
        with pytest.raises(ValueError, match="exact integer"):
            verifier._verify_schedule(chain_root, 1, 0, 1, status, history)

    chain_root, status, history = publish(
        tmp_path / "status-records", status_records=True
    )
    with pytest.raises(ValueError, match="exact integer"):
        verifier._verify_schedule(chain_root, 1, 0, 1, status, history)
    verifier._set_hold(
        tmp_path,
        reason="independent_verification_not_passed",
        stage="independent_verification",
        extension_epoch=0,
        output_base_override=tmp_path,
    )
    gate = json.loads(
        (tmp_path / verifier.RUN_ID / "spatial_sensitivity_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate["status"] == "HOLD" and gate["passed"] is False
