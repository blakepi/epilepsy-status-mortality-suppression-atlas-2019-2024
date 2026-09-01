from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.model import PRIMARY_TERMS, Theta, active_prior_specification  # noqa: E402
from bayes_constrained.sampler import load_chain_checkpoint, save_chain_checkpoint  # noqa: E402
from bayes_constrained.sensitivity import (  # noqa: E402
    EXPECTED_INTERACTION_TERMS,
    FINAL_SOURCE_FILES,
    SensitivityProfile,
    acquire_prepare_lock,
    artifact_inventory,
    assert_manifest_matches,
    build_sensitivity_frame,
    canonical_sha256,
    completed_chain_is_reusable,
    derive_period_irrs,
    evaluate_profile_gate,
    expected_parameter_schema,
    load_declared_checkpoint,
    load_execution_spec,
    load_final_source_manifest,
    preparation_identity,
    publish_directory_no_clobber,
    profile_fingerprint,
    safe_relative_path,
    validate_chain_draws,
    validate_comparison_table,
    validate_diagnostics_table,
)


CONFIG_PATH = ROOT / "config" / "sr_v2_heavy_sensitivity_execution.yaml"
SVI_PATH = ROOT / "data" / "raw" / "covariates" / "SVI_2022_US_county.csv"

EXPECTED_MAP = [
    (1, "prior_broader", 1, 68291, 67291),
    (2, "prior_broader", 2, 68292, 67292),
    (3, "prior_broader", 3, 68293, 67293),
    (4, "prior_broader", 4, 68294, 67294),
    (5, "prior_regularizing", 1, 69291, 67391),
    (6, "prior_regularizing", 2, 69292, 67392),
    (7, "prior_regularizing", 3, 69293, 67393),
    (8, "prior_regularizing", 4, 69294, 67394),
    (9, "model_family_poisson", 1, 70291, 70251),
    (10, "model_family_poisson", 2, 70292, 70252),
    (11, "model_family_poisson", 3, 70293, 70253),
    (12, "model_family_poisson", 4, 70294, 70254),
    (13, "pandemic_interaction", 1, 71291, 71251),
    (14, "pandemic_interaction", 2, 71292, 71252),
    (15, "pandemic_interaction", 3, 71293, 71253),
    (16, "pandemic_interaction", 4, 71294, 71254),
    (17, "pandemic_exclusion", 1, 72291, 72251),
    (18, "pandemic_exclusion", 2, 72292, 72252),
    (19, "pandemic_exclusion", 3, 72293, 72253),
    (20, "pandemic_exclusion", 4, 72294, 72254),
    (21, "age_structure_age17", 1, 73291, 73251),
    (22, "age_structure_age17", 2, 73292, 73252),
    (23, "age_structure_age17", 3, 73293, 73253),
    (24, "age_structure_age17", 4, 73294, 73254),
]

EXPECTED_TARGETS = {
    "prior_broader": ("negative_binomial_2", "primary", "full", "broader"),
    "prior_regularizing": (
        "negative_binomial_2",
        "primary",
        "full",
        "regularizing",
    ),
    "model_family_poisson": ("poisson", "primary", "full", "default"),
    "pandemic_interaction": (
        "negative_binomial_2",
        "pandemic_interaction",
        "full",
        "default",
    ),
    "pandemic_exclusion": (
        "negative_binomial_2",
        "primary",
        "pandemic_exclusion",
        "default",
    ),
    "age_structure_age17": (
        "negative_binomial_2",
        "age_structure_age17",
        "age17_augmented",
        "default",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_execution_spec_is_the_exact_immutable_24_chain_contract() -> None:
    spec = load_execution_spec(CONFIG_PATH)
    assert spec.run_id == "sr-v2-heavy-sensitivity-20260818-v1"
    assert spec.repository_base_commit == "123904015805758119d8cc9d88c6bb94efbc36e1"
    assert (
        spec.iterations_per_chain,
        spec.burn_in,
        spec.thin,
        spec.retained_draws_per_chain,
    ) == (180000, 45000, 30, 4500)
    assert [
        (row.array_index, row.profile_id, row.chain_id, row.chain_seed, row.initialization_seed)
        for row in spec.chain_map
    ] == EXPECTED_MAP
    assert len({row.chain_seed for row in spec.chain_map}) == 24
    assert len({row.initialization_seed for row in spec.chain_map}) == 24
    assert all(
        len([row for row in spec.chain_map if row.profile_id == profile_id]) == 4
        for profile_id in EXPECTED_TARGETS
    )
    assert {
        profile.profile_id: (
            profile.likelihood,
            profile.model,
            profile.frame,
            profile.prior,
        )
        for profile in spec.profiles
    } == EXPECTED_TARGETS
    assert spec.thresholds == {
        "rhat_max_all": 1.05,
        "ess_bulk_min_all": 100,
        "ess_tail_min_all": 100,
        "rhat_max_primary": 1.03,
        "ess_bulk_min_primary": 400,
        "ess_tail_min_primary": 400,
        "constraint_failures_allowed": 0,
    }
    for relative, expected in spec.source_authorities.items():
        assert _sha256(ROOT / relative) == expected
    assert tuple(spec.final_source_files) == FINAL_SOURCE_FILES
    assert spec.launch_envelope_schema == "sr_v2_robustness_launch_envelope/v1"


def test_profile_fingerprint_binds_target_chain_schema_and_all_hash_families() -> None:
    spec = load_execution_spec(CONFIG_PATH)
    broader = spec.profile("prior_broader")
    poisson = spec.profile("model_family_poisson")
    first, second = spec.chain_map[:2]
    keywords = {
        "run_id": spec.run_id,
        "included_years": ["2019", "2020", "2021", "2022", "2023", "2024"],
        "execution": {"n_iter": 180000, "burn_in": 45000, "thin": 30},
        "config_sha256": "a" * 64,
        "input_hashes": {"frame": "b" * 64},
        "source_hashes": {"sampler": "c" * 64},
        "parameter_schema": ["Intercept", "kappa"],
    }
    baseline = profile_fingerprint(broader, first, **keywords)
    assert baseline == profile_fingerprint(broader, first, **keywords)
    assert baseline != profile_fingerprint(broader, second, **keywords)
    assert baseline != profile_fingerprint(poisson, first, **keywords)
    assert baseline != profile_fingerprint(
        broader, first, **{**keywords, "parameter_schema": ["Intercept"]}
    )
    assert baseline != profile_fingerprint(
        broader,
        first,
        **{**keywords, "source_hashes": {"sampler": "d" * 64}},
    )


def test_reviewed_frames_and_parameter_schemas_are_exact() -> None:
    spec = load_execution_spec(CONFIG_PATH)
    source = load_model_frame()
    source_copy = source.copy(deep=True)

    exclusion_profile = spec.profile("pandemic_exclusion")
    excluded = build_sensitivity_frame(source, exclusion_profile, svi_path=SVI_PATH)
    assert sorted(excluded["year"].astype(str).unique()) == [
        "2019",
        "2022",
        "2023",
        "2024",
    ]
    assert excluded.attrs["constraint_contract"] == "selected_years_no_period_total"
    assert "source_full_period_q001_lower" in excluded
    assert "source_full_period_q001_upper" in excluded

    age_profile = spec.profile("age_structure_age17")
    age = build_sensitivity_frame(source, age_profile, svi_path=SVI_PATH)
    assert len(age) == len(source)
    assert set(age["county_fips"]) == set(source["county_fips"])
    assert {"z_pct_age65", "z_pct_age17", "age17_imputed_flag"} <= set(age.columns)
    pd.testing.assert_frame_equal(source, source_copy)

    poisson_schema = expected_parameter_schema(
        source, spec.profile("model_family_poisson")
    )
    assert "kappa" not in poisson_schema
    interaction_schema = expected_parameter_schema(
        source, spec.profile("pandemic_interaction")
    )
    assert [term for term in interaction_schema if "__x__" in term] == list(
        EXPECTED_INTERACTION_TERMS
    )
    exclusion_schema = expected_parameter_schema(excluded, exclusion_profile)
    assert [term for term in exclusion_schema if term.startswith("year_effect[")] == [
        "year_effect[2019]",
        "year_effect[2022]",
        "year_effect[2023]",
        "year_effect[2024]",
    ]
    assert "z_pct_age17" in expected_parameter_schema(age, age_profile)


def test_interaction_irrs_are_derived_draw_by_draw_before_quantiles() -> None:
    draws = pd.DataFrame(
        [
            {"chain": 1, "draw": 1, "parameter": "primary_rurality_metro_other", "value": np.log(2.0)},
            {"chain": 1, "draw": 1, "parameter": "primary_rurality_metro_other__x__acute_pandemic", "value": np.log(3.0)},
            {"chain": 1, "draw": 1, "parameter": "primary_rurality_metro_other__x__later_period", "value": np.log(5.0)},
            {"chain": 1, "draw": 2, "parameter": "primary_rurality_metro_other", "value": np.log(7.0)},
            {"chain": 1, "draw": 2, "parameter": "primary_rurality_metro_other__x__acute_pandemic", "value": np.log(11.0)},
            {"chain": 1, "draw": 2, "parameter": "primary_rurality_metro_other__x__later_period", "value": np.log(13.0)},
        ]
    )
    actual = derive_period_irrs(draws)
    assert actual[["chain", "draw", "parameter", "period"]].to_records(index=False).tolist() == [
        (1, 1, "primary_rurality_metro_other", "pre_pandemic_2019"),
        (1, 1, "primary_rurality_metro_other", "acute_pandemic_2020_2021"),
        (1, 1, "primary_rurality_metro_other", "later_period_2022_2024"),
        (1, 2, "primary_rurality_metro_other", "pre_pandemic_2019"),
        (1, 2, "primary_rurality_metro_other", "acute_pandemic_2020_2021"),
        (1, 2, "primary_rurality_metro_other", "later_period_2022_2024"),
    ]
    np.testing.assert_allclose(actual["irr"], [2.0, 6.0, 10.0, 7.0, 77.0, 91.0])


def test_changed_preparation_manifest_is_never_treated_as_idempotent() -> None:
    expected = {
        "run_id": "sr-v2-heavy-sensitivity-20260818-v1",
        "preparation_identity": "a" * 64,
        "operational_config_sha256": "b" * 64,
    }
    assert_manifest_matches(expected, dict(expected))
    for key, value in (
        ("run_id", "different"),
        ("preparation_identity", "c" * 64),
        ("operational_config_sha256", "d" * 64),
    ):
        changed = {**expected, key: value}
        with pytest.raises(ValueError, match="immutable preparation manifest"):
            assert_manifest_matches(expected, changed)


def test_completed_chain_is_reused_only_after_every_hash_verifies(tmp_path: Path) -> None:
    chain_dir = tmp_path / "chain_01"
    chain_dir.mkdir()
    (chain_dir / "draws_params.parquet").write_bytes(b"draws")
    (chain_dir / "latent_validation.csv").write_bytes(b"passed\nTrue\n")
    (chain_dir / "checkpoint.npz").write_bytes(b"checkpoint")
    hashes = {
        name: _sha256(chain_dir / name)
        for name in (
            "draws_params.parquet",
            "latent_validation.csv",
            "checkpoint.npz",
        )
    }
    status = {
        "status": "completed",
        "run_id": "sr-v2-heavy-sensitivity-20260818-v1",
        "array_index": 1,
        "profile_fingerprint": "f" * 64,
        "saved_draws": 4500,
        "artifact_sha256": hashes,
    }
    assert completed_chain_is_reusable(
        chain_dir,
        status,
        run_id=status["run_id"],
        array_index=1,
        fingerprint=status["profile_fingerprint"],
        expected_draws=4500,
    )
    (chain_dir / "draws_params.parquet").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256"):
        completed_chain_is_reusable(
            chain_dir,
            status,
            run_id=status["run_id"],
            array_index=1,
            fingerprint=status["profile_fingerprint"],
            expected_draws=4500,
        )


def _valid_chain_records(schema: list[str]) -> list[dict[str, object]]:
    return [
        {
            "chain_id": chain_id,
            "status": "completed",
            "saved_draws": 4500,
            "hashes_verified": True,
            "constraint_failures": 0,
            "parameter_schema": schema,
            "included_years": ["2019", "2020", "2021", "2022", "2023", "2024"],
        }
        for chain_id in range(1, 5)
    ]


def test_profile_gate_holds_for_missing_tampered_or_nonconverged_evidence() -> None:
    profile = SensitivityProfile(
        profile_id="prior_broader",
        likelihood="negative_binomial_2",
        model="primary",
        frame="full",
        prior="broader",
    )
    schema = ["Intercept", *PRIMARY_TERMS, "kappa"]
    diagnostics = pd.DataFrame(
        {
            "parameter": schema,
            "r_hat": [1.0] * len(schema),
            "ess_bulk": [500.0] * len(schema),
            "ess_tail": [500.0] * len(schema),
            "chains": [4] * len(schema),
            "draws_per_chain": [4500] * len(schema),
            "draws": [18000] * len(schema),
        }
    )
    comparisons = pd.DataFrame([
        {
            "profile": "prior_broader", "parameter": parameter, "period": "modeled_period",
            "sensitivity_median": 1.1, "sensitivity_lower_95": 1.0, "sensitivity_upper_95": 1.2,
            "primary_median": 1.1, "primary_lower_95": 1.0, "primary_upper_95": 1.2,
        }
        for parameter in PRIMARY_TERMS
    ])
    kwargs = {
        "profile": profile,
        "diagnostics": diagnostics,
        "comparisons": comparisons,
        "expected_schema": schema,
        "expected_years": ["2019", "2020", "2021", "2022", "2023", "2024"],
        "expected_comparison_parameters": ["primary_rurality_metro_other"],
        "thresholds": {
            "rhat_max_all": 1.05,
            "ess_bulk_min_all": 100,
            "ess_tail_min_all": 100,
            "rhat_max_primary": 1.03,
            "ess_bulk_min_primary": 400,
            "ess_tail_min_primary": 400,
            "constraint_failures_allowed": 0,
        },
        "primary_parameters": ["primary_rurality_metro_other"],
    }
    valid = _valid_chain_records(schema)
    assert evaluate_profile_gate(chain_records=valid, **kwargs)["passed"] is True
    assert evaluate_profile_gate(chain_records=valid[:3], **kwargs)["passed"] is False
    tampered = [dict(row) for row in valid]
    tampered[0]["hashes_verified"] = False
    assert evaluate_profile_gate(chain_records=tampered, **kwargs)["passed"] is False
    bad_diagnostics = diagnostics.copy()
    bad_diagnostics.loc[1, "r_hat"] = 1.031
    assert evaluate_profile_gate(
        chain_records=valid, **{**kwargs, "diagnostics": bad_diagnostics}
    )["passed"] is False
    missing_comparison = comparisons.iloc[0:0]
    assert evaluate_profile_gate(
        chain_records=valid, **{**kwargs, "comparisons": missing_comparison}
    )["passed"] is False


def test_runner_cli_exposes_no_force_or_cross_target_resume_path() -> None:
    path = ROOT / "scripts" / "101_run_sr_v2_heavy_sensitivity_chain.py"
    module_spec = importlib.util.spec_from_file_location("heavy_chain_runner", path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    parser = module.build_parser()
    assert {action.dest for action in parser._actions} == {
        "help",
        "run_id",
        "array_index",
    }


def _write_final_source_manifest(root: Path, spec, *, launch_commit: str = "1" * 40) -> Path:
    sources = {}
    for index, relative in enumerate(FINAL_SOURCE_FILES):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source-{index}\n", encoding="utf-8")
        sources[relative] = _sha256(path)
    union_source = root / "src" / "bayes_constrained" / "spatial_future.py"
    union_source.write_text("# future spatial executable\n", encoding="utf-8")
    sources["src/bayes_constrained/spatial_future.py"] = _sha256(union_source)
    joint = root / "evidence" / "joint_regression.json"
    joint.parent.mkdir(parents=True, exist_ok=True)
    joint.write_text('{"passed":true}\n', encoding="utf-8")
    source_manifest = {
        "schema_id": "sr_v2_robustness_final_source_manifest/v1",
        "status": "reviewed_final",
        "joint_regression_passed": True,
        "joint_regression_evidence": "evidence/joint_regression.json",
        "joint_regression_evidence_sha256": _sha256(joint),
        "source_hash_mode": "raw_bytes",
        "sources": sources,
    }
    payload = {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "status": "reviewed_final",
        "clean_worktree": True,
        "launch_commit": launch_commit,
        "bundle_sha256": "2" * 64,
        "source_manifest": source_manifest,
        "source_manifest_sha256": canonical_sha256(source_manifest),
    }
    path = root / "external" / "reviewed_launch_envelope.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    path.with_name(path.name + ".sha256").write_text(_sha256(path) + "\n", encoding="ascii")
    return path


def test_final_source_manifest_is_required_complete_and_tamper_evident(tmp_path: Path) -> None:
    spec = load_execution_spec(CONFIG_PATH)
    assert tuple(spec.final_source_files) == FINAL_SOURCE_FILES
    missing = tmp_path / "external" / "missing.json"
    with pytest.raises(FileNotFoundError, match="launch envelope"):
        load_final_source_manifest(tmp_path, spec, missing)
    manifest_path = _write_final_source_manifest(tmp_path, spec)
    loaded = load_final_source_manifest(tmp_path, spec, manifest_path)
    assert loaded["launch_commit"] == "1" * 40
    assert set(FINAL_SOURCE_FILES) < set(loaded["sources"])
    (tmp_path / FINAL_SOURCE_FILES[0]).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source SHA-256"):
        load_final_source_manifest(tmp_path, spec, manifest_path)
    assert manifest_path.exists()


def test_actual_prepare_entrypoint_holds_without_external_launch_envelope() -> None:
    path = ROOT / "scripts" / "100_prepare_sr_v2_heavy_sensitivity.py"
    module_spec = importlib.util.spec_from_file_location("heavy_prepare_integration", path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    with pytest.raises(FileNotFoundError, match="external launch envelope"):
        module.prepare(root=ROOT, config_path=CONFIG_PATH, launch_envelope_path=None)


def test_actual_merge_entrypoint_rejects_missing_preparation_identity(tmp_path: Path) -> None:
    spec = load_execution_spec(CONFIG_PATH)
    for relative in spec.source_authorities:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    external = _write_final_source_manifest(tmp_path, spec)
    run_root = tmp_path / spec.output_root / spec.run_id
    run_root.mkdir(parents=True)
    shutil.copyfile(external, run_root / "launch_envelope.json")
    shutil.copyfile(external.with_name(external.name + ".sha256"), run_root / "launch_envelope.json.sha256")
    path = ROOT / "scripts" / "102_merge_sr_v2_heavy_sensitivity.py"
    module_spec = importlib.util.spec_from_file_location("heavy_merge_integration", path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="Manifest or SHA-256 sidecar is missing"):
        module.merge(spec.run_id, root=tmp_path, config_path=CONFIG_PATH)


def _synthetic_preparation_frame() -> pd.DataFrame:
    county_fips = ["01001", "01003", "01005", "01007"]
    ruralities = ["metro_large", "metro_other", "nonmetro_adjacent", "nonmetro_nonadjacent"]
    svi = ["Q1_lowest", "Q2", "Q3", "Q4_highest"]
    rows = []
    for year in ("2019", "2020", "2021", "2022", "2023", "2024"):
        for county, rurality, quartile in zip(county_fips, ruralities, svi, strict=True):
            rows.append({
                "county_fips": county, "state_fips": "01", "year": year,
                "q002_count_status": "exact", "q002_lower": 1, "q002_upper": 1,
                "q001_period_status": "exact", "q001_period_lower": 6, "q001_period_upper": 6,
                "q004_state_year_total": 4, "q003_national_year_total": 4,
                "population": 1000.0, "primary_rurality": rurality, "svi_quartile": quartile,
                "z_pct_age65": 0.0, "z_pct_male": 0.0,
            })
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = 24
    frame.attrs["constraint_contract"] = "full_period"
    return frame


def _complete_all_prepared_chains(run_root: Path, spec) -> None:
    prepared = json.loads((run_root / "prepared_run_manifest.json").read_text(encoding="utf-8"))
    for profile_record in prepared["profiles"]:
        schema = list(profile_record["parameter_schema"])
        profile = profile_record["profile"]
        for assignment in profile_record["chains"]:
            chain_id = int(assignment["chain"])
            chain_dir = run_root / "profiles" / profile["id"] / "chains" / f"chain_{chain_id:02d}"
            draw_ids = np.tile(np.arange(1, 4501, dtype=np.int64), len(schema))
            draws = pd.DataFrame({
                "chain": np.full(len(schema) * 4500, chain_id, dtype=np.int64),
                "draw": draw_ids,
                "iteration": 45000 + draw_ids * 30,
                "parameter": np.repeat(np.asarray(schema, dtype=object), 4500),
                "value": 0.01 * chain_id + draw_ids.astype(float) / 1_000_000.0,
            })
            draws.to_parquet(chain_dir / "draws_params.parquet", index=False)
            np.savez_compressed(chain_dir / "draws_latent.npz", draws=np.asarray([[1]], dtype=np.int16))
            pd.DataFrame({"passed": [True]}).to_csv(chain_dir / "latent_validation.csv", index=False)
            pd.DataFrame({"move": ["stub"], "rate": [1.0]}).to_csv(chain_dir / "acceptance_rates.csv", index=False)
            pd.DataFrame({"iteration": [180000]}).to_csv(chain_dir / "runtime_log.csv", index=False)
            (chain_dir / "chain_config_resolved.yaml").write_text("synthetic: true\n", encoding="utf-8")
            terminal = chain_dir / "checkpoints" / "checkpoint_iter_000180000.npz"
            _checkpoint_payload(
                terminal,
                assignment["checkpoint_target_identity"],
                likelihood_family=profile["likelihood"],
                iteration=180000,
                saved_draws=4500,
            )
            artifacts = [
                "draws_params.parquet", "draws_latent.npz", "latent_validation.csv",
                "acceptance_rates.csv", "runtime_log.csv", "chain_config_resolved.yaml",
            ] + sorted(path.relative_to(chain_dir).as_posix() for path in (chain_dir / "checkpoints").iterdir())
            inventory = artifact_inventory(chain_dir, artifacts)
            latest = terminal.relative_to(chain_dir).as_posix()
            status = {
                "schema_id": "sr_v2_heavy_sensitivity_chain_status/v1",
                "status": "completed", "run_id": spec.run_id,
                "array_index": int(assignment["array_index"]), "profile": profile["id"],
                "chain_id": chain_id, "chain_seed": int(assignment["chain_seed"]),
                "initialization_seed": int(assignment["initialization_seed"]),
                "profile_fingerprint": assignment["profile_fingerprint"],
                "checkpoint_target_identity": assignment["checkpoint_target_identity"],
                "saved_draws": 4500, "constraint_failures": 0,
                "parameter_schema": schema, "included_years": profile_record["included_years"],
                "artifact_sha256": inventory, "latest_checkpoint": latest,
                "latest_checkpoint_sha256": inventory[latest],
            }
            (chain_dir / "chain_status.json").write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


@pytest.mark.filterwarnings("ignore:Perfect separation.*:statsmodels.tools.sm_exceptions.PerfectSeparationWarning")
def test_actual_successful_prepare_merge_gate_then_single_fault_holds(tmp_path: Path) -> None:
    spec = load_execution_spec(CONFIG_PATH)
    for relative in spec.source_authorities:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    envelope = _write_final_source_manifest(tmp_path, spec)
    prepare_path = ROOT / "scripts" / "100_prepare_sr_v2_heavy_sensitivity.py"
    prepare_spec = importlib.util.spec_from_file_location("heavy_prepare_success", prepare_path)
    assert prepare_spec is not None and prepare_spec.loader is not None
    prepare_module = importlib.util.module_from_spec(prepare_spec)
    prepare_spec.loader.exec_module(prepare_module)
    frame = _synthetic_preparation_frame()
    prepared = prepare_module.prepare(
        root=tmp_path,
        config_path=CONFIG_PATH,
        launch_envelope_path=envelope,
        frame_loader=lambda: frame.copy(deep=True),
        allocation_solver=lambda selected, **_: selected["q002_lower"].to_numpy(dtype=int),
    )
    assert prepared["status"] == "prepared_not_run"
    reused = prepare_module.prepare(
        root=tmp_path,
        config_path=CONFIG_PATH,
        launch_envelope_path=envelope,
        frame_loader=lambda: (_ for _ in ()).throw(AssertionError("idempotent prepare rebuilt frames")),
        allocation_solver=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("idempotent prepare reran solver")),
    )
    assert reused["preparation_identity"] == prepared["preparation_identity"]
    run_root = tmp_path / spec.output_root / spec.run_id
    _complete_all_prepared_chains(run_root, spec)

    merge_path = ROOT / "scripts" / "102_merge_sr_v2_heavy_sensitivity.py"
    merge_spec = importlib.util.spec_from_file_location("heavy_merge_success", merge_path)
    assert merge_spec is not None and merge_spec.loader is not None
    merge_module = importlib.util.module_from_spec(merge_spec)
    merge_spec.loader.exec_module(merge_module)

    def perfect_diagnostics(draws: pd.DataFrame, output_dir=None) -> pd.DataFrame:
        parameters = draws["parameter"].drop_duplicates().astype(str).tolist()
        return pd.DataFrame({
            "parameter": parameters, "r_hat": 1.0, "ess_bulk": 1000.0, "ess_tail": 1000.0,
            "chains": 4, "draws_per_chain": 4500, "draws": 18000,
        })

    merged = merge_module.merge(spec.run_id, root=tmp_path, config_path=CONFIG_PATH, diagnostics_builder=perfect_diagnostics)
    assert len(merged["profiles"]) == 6
    assert merge_module.merge(spec.run_id, root=tmp_path, config_path=CONFIG_PATH, diagnostics_builder=perfect_diagnostics)["artifact_sha256"] == merged["artifact_sha256"]

    gate_path = ROOT / "scripts" / "103_gate_sr_v2_heavy_sensitivity.py"
    gate_spec = importlib.util.spec_from_file_location("heavy_gate_success", gate_path)
    assert gate_spec is not None and gate_spec.loader is not None
    gate_module = importlib.util.module_from_spec(gate_spec)
    gate_spec.loader.exec_module(gate_module)
    passed = gate_module.gate(spec.run_id, root=tmp_path, config_path=CONFIG_PATH)
    assert passed["passed"] is True and passed["status"] == "PASS"
    fault = run_root / "profiles" / "prior_broader" / "chains" / "chain_01" / "draws_params.parquet"
    fault.write_bytes(fault.read_bytes() + b"tamper")
    held = gate_module.gate(spec.run_id, root=tmp_path, config_path=CONFIG_PATH)
    assert held["passed"] is False and held["status"] == "HOLD"


@pytest.mark.parametrize(
    ("array_index", "profile_id", "parameter_schema"),
    [
        (1, "prior_broader", ["Intercept", "kappa"]),
        (9, "model_family_poisson", ["Intercept"]),
    ],
)
def test_actual_runner_stub_enforces_manifest_checkpoint_and_orphan_trust_chain(
    tmp_path: Path,
    array_index: int,
    profile_id: str,
    parameter_schema: list[str],
) -> None:
    import yaml

    spec = load_execution_spec(CONFIG_PATH)
    for relative in spec.source_authorities:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    external = _write_final_source_manifest(tmp_path, spec)
    run_root = tmp_path / spec.output_root / spec.run_id
    run_root.mkdir(parents=True)
    envelope = run_root / "launch_envelope.json"
    shutil.copyfile(external, envelope)
    shutil.copyfile(external.with_name(external.name + ".sha256"), envelope.with_name(envelope.name + ".sha256"))
    final_source = load_final_source_manifest(tmp_path, spec, envelope)
    config_hash = _sha256(CONFIG_PATH)
    prep_identity = preparation_identity(spec, config_sha256=config_hash, final_source_manifest=final_source)
    profile = spec.profile(profile_id)
    assignment = spec.assignment(array_index)
    profile_root = run_root / "profiles" / profile.profile_id
    frame_path = profile_root / "inputs" / "model_frame.parquet"
    frame_path.parent.mkdir(parents=True)
    pd.DataFrame({"year": ["2019"], "dummy": [1]}).to_parquet(frame_path, index=False)
    config_path = profile_root / "config" / "resolved_profile.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        yaml.safe_dump({
            "run": {"n_iter": 180000, "likelihood_family": profile.likelihood},
            "model": {"prior_profile": profile.prior, "likelihood_family": profile.likelihood},
        }),
        encoding="utf-8",
    )
    fingerprint = "a" * 64
    identity = {
        "schema_id": "sr_v2_heavy_checkpoint_target/v1",
        "run_id": spec.run_id,
        "profile": profile.profile_id,
        "profile_fingerprint": fingerprint,
        "model": profile.model,
        "likelihood": profile.likelihood,
        "frame": profile.frame,
        "prior": profile.prior,
        "operational_config_sha256": config_hash,
        "profile_config_sha256": _sha256(config_path),
        "frame_sha256": _sha256(frame_path),
        "final_source_manifest_sha256": final_source["manifest_sha256"],
        "parameter_schema_sha256": "b" * 64,
        "array_index": array_index,
        "chain_id": assignment.chain_id,
        "chain_seed": assignment.chain_seed,
        "initialization_seed": assignment.initialization_seed,
    }
    chain_dir = profile_root / "chains" / "chain_01"
    initial = chain_dir / "checkpoints" / "checkpoint_iter_000000000.npz"
    _checkpoint_payload(initial, identity, likelihood_family=profile.likelihood, iteration=0, saved_draws=0)
    artifacts = [
        "launch_envelope.json", "launch_envelope.json.sha256",
        frame_path.relative_to(run_root).as_posix(), config_path.relative_to(run_root).as_posix(),
        initial.relative_to(run_root).as_posix(), initial.with_name(initial.name + ".sha256").relative_to(run_root).as_posix(),
    ]
    prepared = {
        "schema_id": "sr_v2_heavy_sensitivity_prepared_run/v1",
        "run_id": spec.run_id,
        "preparation_identity": prep_identity,
        "operational_config_sha256": config_hash,
        "final_source_manifest_sha256": final_source["manifest_sha256"],
        "launch_envelope_sha256": final_source["envelope_sha256"],
        "launch_commit": final_source["launch_commit"],
        "bundle_sha256": final_source["bundle_sha256"],
        "profiles": [{
            "profile": profile.to_dict(), "included_years": ["2019"], "required_columns": ["dummy", "year"],
            "parameter_schema": parameter_schema,
            "frame": frame_path.relative_to(run_root).as_posix(), "frame_sha256": _sha256(frame_path),
            "config": config_path.relative_to(run_root).as_posix(), "config_sha256": _sha256(config_path),
            "chains": [{**assignment.to_dict(), "profile_fingerprint": fingerprint, "checkpoint_target_identity": identity,
                        "initial_checkpoint": initial.relative_to(run_root).as_posix(), "initial_checkpoint_sha256": _sha256(initial)}],
        }],
        "prepared_artifact_sha256": artifact_inventory(run_root, artifacts),
    }
    prepared_path = run_root / "prepared_run_manifest.json"
    prepared_path.write_text(json.dumps(prepared, sort_keys=True) + "\n", encoding="utf-8")
    prepared_path.with_name(prepared_path.name + ".sha256").write_text(_sha256(prepared_path) + "\n", encoding="ascii")

    sampler_called = False

    def stub_sampler(frame, **kwargs):
        nonlocal sampler_called
        sampler_called = True
        resolved = yaml.safe_load(Path(kwargs["config_path"]).read_text(encoding="utf-8"))
        assert resolved["run"]["likelihood_family"] == profile.likelihood
        assert resolved["model"]["prior_profile"] == profile.prior
        assert active_prior_specification().name == profile.prior
        assert kwargs["mode"] == "production"
        assert kwargs["chain_id"] == assignment.chain_id
        assert kwargs["array_task_id"] == array_index
        assert kwargs["seed"] == assignment.chain_seed
        assert Path(kwargs["out_dir"]) == profile_root
        assert Path(kwargs["checkpoint_dir"]) == chain_dir / "checkpoints"
        assert kwargs["checkpoint_every"] == spec.checkpoint_every
        assert kwargs["resume"] is True
        assert kwargs["model_name"] == profile.model
        assert kwargs["target_identity"] == identity
        assert Path(kwargs["resume_checkpoint_path"]) == initial
        assert frame["year"].astype(str).tolist() == ["2019"]
        output = Path(kwargs["out_dir"]) / "chains" / "chain_01"
        pd.DataFrame([
            {"chain": 1, "draw": draw, "iteration": 45000 + draw * 30, "parameter": parameter, "value": float(draw) / 1000}
            for parameter in parameter_schema for draw in range(1, 4501)
        ]).to_parquet(output / "draws_params.parquet", index=False)
        np.savez_compressed(output / "draws_latent.npz", draws=np.asarray([[1]]))
        pd.DataFrame({"passed": [True]}).to_csv(output / "latent_validation.csv", index=False)
        pd.DataFrame({"move": ["x"], "rate": [1.0]}).to_csv(output / "acceptance_rates.csv", index=False)
        pd.DataFrame({"iteration": [180000]}).to_csv(output / "runtime_log.csv", index=False)
        (output / "chain_config_resolved.yaml").write_text("stub: true\n", encoding="utf-8")
        terminal = output / "checkpoints" / "checkpoint_iter_000180000.npz"
        theta = Theta(beta=np.asarray([0.0]), state_effect=np.asarray([0.0]), year_effect=np.asarray([0.0]), log_sigma_state=0.0, log_sigma_year=0.0, log_kappa=0.0)
        save_chain_checkpoint(
            terminal, y=np.asarray([1]), theta=theta, rng=np.random.default_rng(8), iteration=180000,
            saved_draws=4500, current_lp=-1.0, accepted={}, proposed={}, param_accept={}, param_prop={},
            likelihood_family=profile.likelihood, target_identity=identity,
        )
        return {"status": "completed", "saved_draws": 4500, "iteration": 180000}

    runner_path = ROOT / "scripts" / "101_run_sr_v2_heavy_sensitivity_chain.py"
    module_spec = importlib.util.spec_from_file_location("heavy_runner_integration", runner_path)
    assert module_spec is not None and module_spec.loader is not None
    runner = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(runner)
    status = runner.run_chain(spec.run_id, array_index, root=tmp_path, config_path=CONFIG_PATH, sampler_runner=stub_sampler)
    assert status["status"] == "completed"
    assert sampler_called is True
    sampler_called = False
    reused_status = runner.run_chain(spec.run_id, array_index, root=tmp_path, config_path=CONFIG_PATH, sampler_runner=stub_sampler)
    assert reused_status["status"] == "completed" and sampler_called is False
    (chain_dir / "orphan.partial").write_text("partial", encoding="utf-8")
    with pytest.raises(ValueError, match="orphan|undeclared"):
        runner.run_chain(spec.run_id, array_index, root=tmp_path, config_path=CONFIG_PATH, sampler_runner=stub_sampler)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (("output_root", "../escape"), "output root"),
        (("thresholds.rhat_max_all", 1.5), "threshold"),
        (("profiles.0.prior", "default"), "target contract"),
        (("chain_map.0.chain_seed", 999), "chain map"),
        (("protected_trees.0", "outputs/other"), "protected trees"),
    ],
)
def test_execution_spec_rejects_any_frozen_contract_drift(
    tmp_path: Path, mutation: tuple[str, object], match: str
) -> None:
    import yaml

    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    dotted, value = mutation
    cursor = payload
    parts = dotted.split(".")
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    last = parts[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = value
    else:
        cursor[last] = value
    path = tmp_path / "changed.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_execution_spec(path)


def test_safe_paths_and_no_clobber_publication_reject_escape_and_conflict(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ValueError, match="relative"):
        safe_relative_path(root, Path("..") / "escape")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError:
        pass
    else:
        with pytest.raises(ValueError, match="escapes"):
            safe_relative_path(root, "link/file.json")

    lock = root / ".prepare.lock"
    with acquire_prepare_lock(lock):
        with pytest.raises(FileExistsError, match="preparation lock"):
            with acquire_prepare_lock(lock):
                pass
    staging = root / ".staging"
    staging.mkdir()
    (staging / "new.txt").write_text("new", encoding="utf-8")
    destination = root / "run"
    destination.mkdir()
    (destination / "existing.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to replace"):
        publish_directory_no_clobber(staging, destination)
    assert (destination / "existing.txt").read_text(encoding="utf-8") == "preserve"


def test_no_clobber_publication_rejects_raced_empty_destination_and_dangling_symlink(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "payload").write_text("new", encoding="utf-8")
    destination = tmp_path / "run"

    def race() -> None:
        destination.mkdir()

    with pytest.raises(FileExistsError, match="refusing to replace"):
        publish_directory_no_clobber(staging, destination, before_commit=race)
    assert staging.is_dir() and destination.is_dir()
    assert not (destination / "payload").exists()

    dangling = tmp_path / "dangling"
    try:
        os.symlink(tmp_path / "missing-target", dangling, target_is_directory=True)
    except OSError:
        return
    other = tmp_path / "other-staging"
    other.mkdir()
    with pytest.raises(FileExistsError, match="refusing to replace"):
        publish_directory_no_clobber(other, dangling)
    assert os.path.lexists(dangling)


def test_no_clobber_publication_moves_commit_marker_last(tmp_path: Path, monkeypatch) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "payload").write_text("data", encoding="utf-8")
    (staging / "prepared_run_manifest.json").write_text("{}\n", encoding="utf-8")
    marker = staging / "prepared_run_manifest.json.sha256"
    marker.write_text("0" * 64 + "\n", encoding="ascii")
    destination = tmp_path / "run"
    real_rename = os.rename
    moved: list[str] = []

    def recording_rename(source, target) -> None:
        moved.append(Path(source).name)
        real_rename(source, target)

    monkeypatch.setattr(os, "rename", recording_rename)
    publish_directory_no_clobber(
        staging,
        destination,
        commit_marker="prepared_run_manifest.json.sha256",
    )
    assert moved[-1] == "prepared_run_manifest.json.sha256"
    assert not staging.exists() and marker.name in {path.name for path in destination.iterdir()}


def _checkpoint_payload(
    path: Path,
    identity: dict[str, object] | None,
    *,
    likelihood_family: str = "negative_binomial_2",
    iteration: int = 10,
    saved_draws: int = 2,
) -> None:
    theta = Theta(
        beta=np.asarray([0.0]),
        state_effect=np.asarray([0.0]),
        year_effect=np.asarray([0.0]),
        log_sigma_state=0.0,
        log_sigma_year=0.0,
        log_kappa=0.0,
    )
    save_chain_checkpoint(
        path,
        y=np.asarray([1]),
        theta=theta,
        rng=np.random.default_rng(7),
        iteration=iteration,
        saved_draws=saved_draws,
        current_lp=-1.0,
        accepted={},
        proposed={},
        param_accept={},
        param_prop={},
        likelihood_family=likelihood_family,
        target_identity=identity,
    )


def test_checkpoint_embeds_full_target_identity_and_declared_resume_never_falls_back(
    tmp_path: Path,
) -> None:
    identity = {
        "schema_id": "sr_v2_heavy_checkpoint_target/v1",
        "run_id": "sr-v2-heavy-sensitivity-20260818-v1",
        "profile": "prior_broader",
        "profile_fingerprint": "a" * 64,
        "model": "primary",
        "likelihood": "negative_binomial_2",
        "frame": "full",
        "prior": "broader",
        "operational_config_sha256": "b" * 64,
        "profile_config_sha256": "c" * 64,
        "frame_sha256": "d" * 64,
        "final_source_manifest_sha256": "e" * 64,
        "parameter_schema_sha256": "f" * 64,
        "array_index": 1,
        "chain_id": 1,
        "chain_seed": 68291,
        "initialization_seed": 67291,
    }
    directory = tmp_path / "checkpoints"
    first = directory / "checkpoint_iter_000000010.npz"
    _checkpoint_payload(first, identity)
    loaded = load_chain_checkpoint(first, expected_target_identity=identity)
    assert loaded["target_identity"] == identity
    substituted = {**identity, "profile": "prior_regularizing", "prior": "regularizing"}
    with pytest.raises(ValueError, match="target identity mismatch"):
        load_chain_checkpoint(first, expected_target_identity=substituted)
    newer = directory / "checkpoint_iter_000000020.npz"
    _checkpoint_payload(newer, identity)
    newer.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="newer|declared"):
        load_declared_checkpoint(
            directory, first.name, expected_target_identity=identity,
            expected_likelihood_family="negative_binomial_2",
        )
    newer.unlink()
    first.with_name(first.name + ".sha256").write_text("0" * 64 + "\n", encoding="ascii")
    with pytest.raises(ValueError, match="sidecar"):
        load_chain_checkpoint(first, expected_target_identity=identity)


def test_declared_poisson_checkpoint_uses_and_cross_checks_target_family(tmp_path: Path) -> None:
    identity = {
        "schema_id": "sr_v2_heavy_checkpoint_target/v1", "run_id": "run", "profile": "model_family_poisson",
        "profile_fingerprint": "a" * 64, "model": "primary", "likelihood": "poisson", "frame": "full",
        "prior": "default", "operational_config_sha256": "b" * 64, "profile_config_sha256": "c" * 64,
        "frame_sha256": "d" * 64, "final_source_manifest_sha256": "e" * 64,
        "parameter_schema_sha256": "f" * 64, "array_index": 9, "chain_id": 1,
        "chain_seed": 70291, "initialization_seed": 70251,
    }
    checkpoint = tmp_path / "checkpoints" / "checkpoint_iter_000000000.npz"
    theta = Theta(beta=np.asarray([0.0]), state_effect=np.asarray([0.0]), year_effect=np.asarray([0.0]), log_sigma_state=0.0, log_sigma_year=0.0, log_kappa=0.0)
    save_chain_checkpoint(
        checkpoint, y=np.asarray([1]), theta=theta, rng=np.random.default_rng(9), iteration=0,
        saved_draws=0, current_lp=-1.0, accepted={}, proposed={}, param_accept={}, param_prop={},
        likelihood_family="poisson", target_identity=identity,
    )
    loaded = load_declared_checkpoint(
        checkpoint.parent, checkpoint.name,
        expected_target_identity=identity, expected_likelihood_family="poisson",
    )
    assert loaded["likelihood_family"] == "poisson"
    with pytest.raises(ValueError, match="target identity likelihood|family"):
        load_declared_checkpoint(
            checkpoint.parent, checkpoint.name,
            expected_target_identity=identity, expected_likelihood_family="negative_binomial_2",
        )


def test_default_checkpoint_writer_preserves_exact_legacy_schema_and_artifacts(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint_iter_000000005.npz"
    _checkpoint_payload(checkpoint, identity=None)
    with np.load(checkpoint, allow_pickle=True) as stored:
        assert set(stored.files) == {
            "y", "beta", "state_effect", "year_effect", "log_sigma_state", "log_sigma_year", "log_kappa",
            "rng_state", "iteration", "saved_draws", "current_lp", "accepted_json", "proposed_json",
            "param_accept_json", "param_prop_json", "likelihood_family",
        }
    assert {path.name for path in tmp_path.iterdir()} == {checkpoint.name}


def test_exact_draw_diagnostic_and_comparison_cardinality_contracts() -> None:
    schema = ["Intercept", "primary_rurality_metro_other"]
    draws = pd.DataFrame(
        [
            {"chain": 1, "draw": draw, "iteration": 1 + 2 * draw, "parameter": parameter, "value": float(draw)}
            for parameter in schema
            for draw in (1, 2)
        ]
    )
    validate_chain_draws(draws, chain_id=1, parameter_schema=schema, retained_draws=2, burn_in=1, thin=2)
    duplicate = pd.concat([draws, draws.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="row count|duplicate"):
        validate_chain_draws(duplicate, chain_id=1, parameter_schema=schema, retained_draws=2, burn_in=1, thin=2)
    wrong_chain = draws.copy(); wrong_chain.loc[0, "chain"] = 2
    with pytest.raises(ValueError, match="chain label"):
        validate_chain_draws(wrong_chain, chain_id=1, parameter_schema=schema, retained_draws=2, burn_in=1, thin=2)
    wrong_iteration = draws.copy(); wrong_iteration.loc[0, "iteration"] = 99
    with pytest.raises(ValueError, match="iteration schedule"):
        validate_chain_draws(wrong_iteration, chain_id=1, parameter_schema=schema, retained_draws=2, burn_in=1, thin=2)
    for column in ("chain", "draw", "iteration"):
        fractional = draws.copy(); fractional[column] = fractional[column].astype(float); fractional.loc[0, column] += 0.9
        with pytest.raises(ValueError, match="integral"):
            validate_chain_draws(fractional, chain_id=1, parameter_schema=schema, retained_draws=2, burn_in=1, thin=2)
        nonfinite = draws.copy(); nonfinite.loc[0, column] = np.nan
        with pytest.raises(ValueError, match="finite integral"):
            validate_chain_draws(nonfinite, chain_id=1, parameter_schema=schema, retained_draws=2, burn_in=1, thin=2)

    diagnostics = pd.DataFrame(
        {
            "parameter": schema,
            "r_hat": [1.0, 1.0],
            "ess_bulk": [10.0, 10.0],
            "ess_tail": [10.0, 10.0],
            "chains": [4, 4],
            "draws_per_chain": [4500, 4500],
            "draws": [18000, 18000],
        }
    )
    validate_diagnostics_table(diagnostics, parameter_schema=schema)
    diagnostics.loc[0, "chains"] = 3
    with pytest.raises(ValueError, match="metadata"):
        validate_diagnostics_table(diagnostics, parameter_schema=schema)

    primary = list(EXPECTED_TARGETS)  # deliberately wrong keys below
    comparison = pd.DataFrame({"parameter": primary, "period": ["modeled_period"] * len(primary), "sensitivity_median": np.ones(len(primary)), "primary_median": np.ones(len(primary))})
    with pytest.raises(ValueError, match="Comparison key|columns"):
        validate_comparison_table(comparison, profile_id="prior_broader")


def test_gate_replaces_stale_pass_before_malformed_config_parsing(tmp_path: Path) -> None:
    script_path = ROOT / "scripts" / "103_gate_sr_v2_heavy_sensitivity.py"
    module_spec = importlib.util.spec_from_file_location("heavy_gate_fix_test", script_path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    gate_path = tmp_path / "outputs" / "scientific_reports_v2" / "heavy_sensitivity" / "sr-v2-heavy-sensitivity-20260818-v1" / "heavy_sensitivity_gate.json"
    gate_path.parent.mkdir(parents=True)
    gate_path.write_text('{"passed":true,"status":"PASS"}\n', encoding="utf-8")
    malformed = tmp_path / "bad.yaml"
    malformed.write_text("not: [valid", encoding="utf-8")
    result = module.gate("wrong-run", root=tmp_path, config_path=malformed)
    persisted = json.loads(gate_path.read_text(encoding="utf-8"))
    assert result["passed"] is False
    assert persisted["status"] == "HOLD"
    assert persisted["passed"] is False
