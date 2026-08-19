from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.sensitivity import (  # noqa: E402
    EXPECTED_INTERACTION_TERMS,
    SensitivityProfile,
    assert_manifest_matches,
    build_sensitivity_frame,
    completed_chain_is_reusable,
    derive_period_irrs,
    evaluate_profile_gate,
    expected_parameter_schema,
    load_execution_spec,
    profile_fingerprint,
    sha256_canonical_text,
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
    for relative, expected in spec.reviewed_sources.items():
        assert sha256_canonical_text(ROOT / relative) == expected


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
    schema = ["Intercept", "primary_rurality_metro_other", "kappa"]
    diagnostics = pd.DataFrame(
        {
            "parameter": schema,
            "r_hat": [1.0, 1.0, 1.0],
            "ess_bulk": [500.0, 500.0, 500.0],
            "ess_tail": [500.0, 500.0, 500.0],
        }
    )
    comparisons = pd.DataFrame(
        {"parameter": ["primary_rurality_metro_other"], "primary_median": [1.1]}
    )
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
    import importlib.util

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
