from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.spatial_bym2 import (  # noqa: E402
    BYM2Prior,
    build_bym2_graph,
    bym2_log_prior,
    combined_county_effect,
    componentwise_center,
    validate_structured_effect,
)


ADJACENCY_PATH = (
    ROOT
    / "outputs"
    / "scientific_reports_v2"
    / "spatial_residual_diagnostics"
    / "county_adjacency2024.txt"
)
MODEL_FRAME_PATH = ROOT / "data" / "processed" / "bayes_constrained" / "model_frame.parquet"
CONFIG_PATH = ROOT / "config" / "sr_v2_spatial_sensitivity_execution.yaml"

COUNTY_ORDER_SHA256 = "250417302ddfc261014e7182e065ff0ebaef3a15437c8672fc05b9ab4a9c066b"
EDGE_LIST_SHA256 = "59412bc9722a119487977065892db16d6bb6931725821a0adb21886ec891df39"
ADJACENCY_SHA256 = "912ca408163016864fe64aaf667b53ad03a19ce4acbc586d3ac508395bdac980"
SINGLETONS = (
    "02261",
    "02270",
    "09001",
    "09003",
    "09005",
    "09007",
    "09009",
    "09011",
    "09013",
    "09015",
    "15001",
    "15003",
    "15007",
    "46113",
)
NON_SINGLETONS = (
    ("01001", 3099, "0x1.23688b75b9ac1p-1"),
    ("02013", 17, "0x1.fdba0c05e631ep-2"),
    ("02100", 10, "0x1.00888ae534b68p-1"),
    ("15005", 2, "0x1.ffffffffffffep-3"),
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _adjacency_payload(edges: list[tuple[str, str]], counties: list[str]) -> bytes:
    rows = ["County Name|County GEOID|Neighbor Name|Neighbor GEOID"]
    for county in counties:
        rows.append(f"{county}|{county}|{county}|{county}")
    for left, right in edges:
        rows.append(f"{left}|{left}|{right}|{right}")
        rows.append(f"{right}|{right}|{left}|{left}")
    return ("\n".join(rows) + "\n").encode("utf-8")


@pytest.fixture
def synthetic_graph(tmp_path: Path):
    counties = ["01001", "01003", "01005", "02001", "02003", "03001"]
    edges = [
        ("01001", "01003"),
        ("01003", "01005"),
        ("02001", "02003"),
    ]
    payload = _adjacency_payload(edges, counties)
    path = tmp_path / "adjacency.txt"
    path.write_bytes(payload)
    frame = pd.DataFrame({"county_fips": counties})
    return build_bym2_graph(frame, path, expected_sha256=_sha256(payload))


def test_synthetic_graph_locks_component_order_scales_and_unit_marginal_variance(
    synthetic_graph,
) -> None:
    graph = synthetic_graph
    assert [graph.counties[part[0]] for part in graph.components] == [
        "01001",
        "02001",
        "03001",
    ]
    assert [len(part) for part in graph.components] == [3, 2, 1]
    np.testing.assert_allclose(
        graph.component_scale,
        [0.40933683318226494, 0.25, 0.0],
        rtol=0.0,
        atol=1e-15,
    )
    for component in graph.components[:-1]:
        precision = graph.scaled_precision[np.ix_(component, component)].toarray()
        marginal_variance = np.diag(np.linalg.pinv(precision, hermitian=True))
        assert np.exp(np.mean(np.log(marginal_variance))) == pytest.approx(
            1.0, rel=1e-13, abs=1e-13
        )


def test_component_centering_is_not_global_and_singletons_are_exact_zero(
    synthetic_graph,
) -> None:
    centered = componentwise_center(
        np.asarray([1.0, 2.0, 6.0, 10.0, 14.0, 99.0]), synthetic_graph
    )
    np.testing.assert_allclose(centered, [-2.0, -1.0, 3.0, -2.0, 2.0, 0.0])
    for component in synthetic_graph.components[:-1]:
        assert centered[component].sum() == pytest.approx(0.0, abs=1e-15)
    assert centered[-1] == 0.0
    validate_structured_effect(centered, synthetic_graph)

    globally_centered = np.asarray([-1.0, -1.0, -1.0, 1.5, 1.5, 0.0])
    with pytest.raises(ValueError, match="component-wise centered"):
        validate_structured_effect(globally_centered, synthetic_graph)
    nonzero_singleton = centered.copy()
    nonzero_singleton[-1] = np.nextafter(0.0, 1.0)
    with pytest.raises(ValueError, match="singleton"):
        validate_structured_effect(nonzero_singleton, synthetic_graph)


def test_combined_effect_matches_bym2_identity_and_singleton_rule(synthetic_graph) -> None:
    structured = componentwise_center(
        np.asarray([1.0, 2.0, 6.0, 10.0, 14.0, 99.0]), synthetic_graph
    )
    unstructured = np.asarray([0.5, -1.0, 0.25, 2.0, -0.5, 3.0])
    log_sigma = np.log(2.5)
    phi = 0.36
    actual = combined_county_effect(
        structured,
        unstructured,
        log_sigma,
        np.log(phi / (1.0 - phi)),
        synthetic_graph,
    )
    expected = 2.5 * (0.6 * structured + 0.8 * unstructured)
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=1e-14)
    assert actual[-1] == pytest.approx(2.5 * 0.8 * unstructured[-1])


def test_transformed_halfnormal_and_beta_priors_include_jacobians(synthetic_graph) -> None:
    structured = np.zeros(6)
    unstructured = np.zeros(6)
    prior = BYM2Prior(sigma_county_halfnormal_sd=1.0)

    at_zero = bym2_log_prior(structured, unstructured, 0.0, 0.0, synthetic_graph, prior)
    at_log_two = bym2_log_prior(
        structured, unstructured, np.log(2.0), 0.0, synthetic_graph, prior
    )
    assert at_log_two - at_zero == pytest.approx(-1.5 + np.log(2.0))

    logit_quarter = np.log(0.25 / 0.75)
    at_quarter = bym2_log_prior(
        structured, unstructured, 0.0, logit_quarter, synthetic_graph, prior
    )
    assert at_quarter - at_zero == pytest.approx(np.log((0.25 * 0.75) / 0.25))
    assert np.isfinite(at_zero)


@pytest.mark.parametrize(
    ("structured", "unstructured", "log_sigma", "logit_phi"),
    [
        (np.asarray([np.nan, 0, 0, 0, 0, 0]), np.zeros(6), 0.0, 0.0),
        (np.zeros(6), np.asarray([0, 0, 0, 0, 0, np.inf]), 0.0, 0.0),
        (np.zeros(6), np.zeros(6), np.inf, 0.0),
        (np.zeros(6), np.zeros(6), 0.0, np.inf),
    ],
)
def test_nonfinite_states_are_rejected(
    synthetic_graph, structured, unstructured, log_sigma, logit_phi
) -> None:
    prior = BYM2Prior(sigma_county_halfnormal_sd=1.0)
    assert (
        bym2_log_prior(
            structured, unstructured, log_sigma, logit_phi, synthetic_graph, prior
        )
        == -np.inf
    )
    with pytest.raises(ValueError, match="finite|phi"):
        combined_county_effect(
            structured, unstructured, log_sigma, logit_phi, synthetic_graph
        )


def test_finite_extreme_log_sigma_is_rejected_without_overflow(synthetic_graph) -> None:
    assert bym2_log_prior(
        np.zeros(6),
        np.zeros(6),
        700.0,
        0.0,
        synthetic_graph,
        BYM2Prior(1.0),
    ) == -np.inf


def test_graph_contract_rejects_wrong_source_hash_and_frame_counties(tmp_path: Path) -> None:
    counties = ["01001", "01003", "01005"]
    payload = _adjacency_payload([("01001", "01003"), ("01003", "01005")], counties)
    path = tmp_path / "adjacency.txt"
    path.write_bytes(payload)
    frame = pd.DataFrame({"county_fips": counties})
    with pytest.raises(ValueError, match="adjacency SHA-256"):
        build_bym2_graph(frame, path, expected_sha256="0" * 64)

    reference = build_bym2_graph(frame, path, expected_sha256=_sha256(payload))
    frozen = {
        "node_count": 3,
        "edge_count": 2,
        "component_count": 1,
        "nonisolated_count": 3,
        "county_order_sha256": _sha256(b"01001\n01003\n01005\n"),
        "edge_list_sha256": _sha256(b"01001|01003\n01003|01005\n"),
        "singletons": [],
        "components": [
            {
                "minimum_fips": "01001",
                "size": 3,
                "scale_hex": float(reference.component_scale[0]).hex(),
            }
        ],
    }
    for bad_frame in (
        pd.DataFrame({"county_fips": counties[:-1]}),
        pd.DataFrame({"county_fips": counties + ["01007"]}),
        pd.DataFrame({"county_fips": counties + ["01005"]}),
    ):
        with pytest.raises(ValueError, match="county|duplicate"):
            build_bym2_graph(
                bad_frame,
                path,
                expected_sha256=_sha256(payload),
                frozen_contract=frozen,
            )


def test_frozen_contract_rejects_edge_and_scale_mismatch(tmp_path: Path) -> None:
    counties = ["01001", "01003", "01005"]
    payload = _adjacency_payload([("01001", "01003"), ("01003", "01005")], counties)
    path = tmp_path / "adjacency.txt"
    path.write_bytes(payload)
    frame = pd.DataFrame({"county_fips": counties})
    graph = build_bym2_graph(frame, path, expected_sha256=_sha256(payload))
    base = {
        "node_count": 3,
        "edge_count": 2,
        "component_count": 1,
        "nonisolated_count": 3,
        "county_order_sha256": _sha256(b"01001\n01003\n01005\n"),
        "edge_list_sha256": _sha256(b"01001|01003\n01003|01005\n"),
        "singletons": [],
        "components": [
            {
                "minimum_fips": "01001",
                "size": 3,
                "scale_hex": float(graph.component_scale[0]).hex(),
            }
        ],
    }
    for field, bad_value, match in (
        ("edge_list_sha256", "f" * 64, "edge-list"),
        (
            "components",
            [{"minimum_fips": "01001", "size": 3, "scale_hex": float(0.5).hex()}],
            "component",
        ),
    ):
        frozen = {**base, field: bad_value}
        with pytest.raises(ValueError, match=match):
            build_bym2_graph(
                frame,
                path,
                expected_sha256=_sha256(payload),
                frozen_contract=frozen,
            )


def test_joint_row_permutation_preserves_canonical_graph_and_target(synthetic_graph, tmp_path: Path) -> None:
    counties = list(synthetic_graph.counties)
    edges = [("01001", "01003"), ("01003", "01005"), ("02001", "02003")]
    payload = _adjacency_payload(edges, counties)
    path = tmp_path / "adjacency.txt"
    path.write_bytes(payload)
    permutation = np.asarray([5, 2, 0, 4, 1, 3])
    permuted_frame = pd.DataFrame({"county_fips": np.asarray(counties)[permutation]})
    permuted = build_bym2_graph(permuted_frame, path, expected_sha256=_sha256(payload))

    structured = componentwise_center(np.asarray([1, 2, 6, 10, 14, 99.0]), synthetic_graph)
    unstructured = np.asarray([0.5, -1.0, 0.25, 2.0, -0.5, 3.0])
    baseline = combined_county_effect(structured, unstructured, 0.4, -0.3, synthetic_graph)
    row_effect = combined_county_effect(structured, unstructured, 0.4, -0.3, permuted)[
        permuted.row_county_index
    ]
    inverse = np.argsort(permutation)
    np.testing.assert_array_equal(row_effect[inverse], baseline)
    assert permuted.counties == synthetic_graph.counties
    assert permuted.contract_sha256 == synthetic_graph.contract_sha256
    assert bym2_log_prior(
        structured,
        unstructured,
        0.4,
        -0.3,
        permuted,
        BYM2Prior(1.0),
    ) == pytest.approx(
        bym2_log_prior(
            structured,
            unstructured,
            0.4,
            -0.3,
            synthetic_graph,
            BYM2Prior(1.0),
        ),
        rel=0.0,
        abs=1e-12,
    )


def test_archived_graph_exact_certificate() -> None:
    frame = pd.read_parquet(MODEL_FRAME_PATH, columns=["county_fips"]).drop_duplicates()
    frozen = {
        "node_count": 3142,
        "edge_count": 9233,
        "component_count": 18,
        "nonisolated_count": 3128,
        "county_order_sha256": COUNTY_ORDER_SHA256,
        "edge_list_sha256": EDGE_LIST_SHA256,
        "singletons": list(SINGLETONS),
        "components": [
            {"minimum_fips": fips, "size": size, "scale_hex": scale}
            for fips, size, scale in NON_SINGLETONS
        ],
    }
    graph = build_bym2_graph(
        frame,
        ADJACENCY_PATH,
        expected_sha256=ADJACENCY_SHA256,
        frozen_contract=frozen,
    )
    assert len(graph.counties) == 3142
    assert graph.adjacency.nnz == 2 * 9233
    assert len(graph.components) == 18
    assert int(graph.singleton_mask.sum()) == 14
    assert tuple(np.asarray(graph.counties)[graph.singleton_mask]) == SINGLETONS
    actual_non_singletons = [
        (
            graph.counties[component[0]],
            len(component),
            float(graph.component_scale[index]).hex(),
        )
        for index, component in enumerate(graph.components)
        if len(component) > 1
    ]
    assert actual_non_singletons == list(NON_SINGLETONS)


def test_operational_yaml_freezes_execution_and_output_contracts() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["schema_id"] == "sr_v2_spatial_sensitivity_execution/v1"
    assert config["run_id"] == "sr-v2-spatial-sensitivity-20260818-v1"
    assert config["model_id"] == "sr-v2-primary-nb2-bym2-v1"
    assert config["source_authorities"] == {
        "outputs/scientific_reports_v2/production_8chain/production_gate.json": "38be94b401138864cf6e4cb030f2bd53e9b8ad6ea24e080e0353824124784437",
        "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv": "2842efa4c95b018aed3626b58b33e42792c0348655225c3a89ec58b4109452e6",
        "outputs/scientific_reports_v2/production_8chain/posterior_parameter_draws.parquet": "0f3adc1a90bd411f3065e798867423d5bd2ae1cf0c61d99d7f5f53493b362064",
        "outputs/scientific_reports_v2/production_8chain/county_posterior_summary.csv": "f9eb36d8748da9a3c8f95c952a95de6d4845ecb963f329a2a61b9adb47ee056e",
        "data/processed/bayes_constrained/model_frame.parquet": "2f20555f4b690e1a495e2409dbb2f9bb128a6d3f7b0bb39f4017034aaf2a9e44",
        "config/scientific_reports_v2_robustness_registry.yaml": "072e039b78af11a0bb4d6532bb8fb09f70b81d825a38faa3cf89670ca7843814",
        "outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json": "5d3209d248add49cfd2a5a5379af3e831ec7f6136ed45654ca882cc399a190d1",
        "outputs/scientific_reports_v2/spatial_residual_diagnostics/global_morans_i.csv": "a44ee5945c308f1455e799c0f22bed356ff118ff6a0de5da1d1f9315c3a836c8",
        "outputs/scientific_reports_v2/spatial_residual_diagnostics/within_state_morans_i.csv": "6296899e8a789e219d245d109b55759dead7817f5ba93c75f0694f669231c995",
        "outputs/scientific_reports_v2/spatial_residual_diagnostics/county_adjacency2024.txt": ADJACENCY_SHA256,
    }
    graph = config["graph_certificate"]
    assert graph["nodes"] == 3142
    assert graph["undirected_edges"] == 9233
    assert graph["components"] == 18
    assert graph["singletons"] == list(SINGLETONS)
    assert graph["nonisolated_nodes"] == 3128
    assert graph["county_order_sha256"] == COUNTY_ORDER_SHA256
    assert graph["edge_list_sha256"] == EDGE_LIST_SHA256
    assert [
        (row["minimum_fips"], row["size"], row["scale_hex"])
        for row in graph["non_singleton_components"]
    ] == list(NON_SINGLETONS)

    assert config["seeds"] == {
        "chain": [74291, 74292, 74293, 74294],
        "allocation_initialization": [74251, 74252, 74253, 74254],
        "spatial_initialization": [74261, 74262, 74263, 74264],
    }
    assert config["execution"]["initial_epoch"] == {
        "extension_epoch": 0,
        "iterations_per_chain": 180000,
        "burn_in": 45000,
        "thin": 30,
        "retained_draws_per_chain": 4500,
    }
    assert config["execution"]["valid_total_iterations_and_draws"] == [
        [180000, 4500],
        [270000, 7500],
        [360000, 10500],
        [450000, 13500],
    ]
    assert config["execution"]["extension_epoch_range"] == [0, 3]
    assert config["execution"]["job_attempt_range_per_epoch"] == [1, 3]
    assert config["mala"] == {
        "frequency_iterations": 5,
        "initial_epsilon_structured": 0.02,
        "initial_epsilon_unstructured": 0.04,
        "adaptation_epoch": 0,
        "adaptation_burn_in_end_iteration": 45000,
        "window_attempts": 100,
        "target_acceptance": 0.574,
        "gain_cap": 0.05,
        "gain_power": -0.6,
        "multiplier_bounds": [0.1, 5.0],
        "extension_adaptation": False,
        "adaptation_formula": "log(m_next)=clip(log(m)+min(0.05,j^-0.6)*(window_acceptance-0.574),log(0.1),log(5.0))",
    }
    assert config["comparison"]["rows"] == [
        "primary_rurality_metro_other",
        "primary_rurality_nonmetro_adjacent",
        "primary_rurality_nonmetro_nonadjacent",
        "svi_quartile_Q2",
        "svi_quartile_Q3",
        "svi_quartile_Q4_highest",
        "z_pct_age65",
        "z_pct_male",
    ]
    assert config["thresholds"]["all_stochastic_and_combined_county"] == {
        "rhat_max_inclusive": 1.05,
        "bulk_ess_min_inclusive": 100,
        "tail_ess_min_inclusive": 100,
    }
    assert config["thresholds"]["primary_plus_spatial_hyperparameters"] == {
        "parameters": config["comparison"]["rows"] + ["sigma_county", "phi_structured"],
        "rhat_max_inclusive": 1.03,
        "bulk_ess_min_inclusive": 400,
        "tail_ess_min_inclusive": 400,
    }
    assert config["thresholds"]["count_constraint_failures_allowed"] == 0
    assert config["thresholds"]["spatial_constraint_failures_allowed"] == 0
    assert config["resources"] == {
        "benchmark": {"partition": "main", "hours": 2, "cpus": 4, "memory_gib": 64},
        "chain": {"partition": "main", "hours": 72, "cpus": 4, "memory_gib": 64, "array": "1-4%2", "usr1_seconds_before_deadline": 300},
        "finalizer": {"partition": "timed-main", "hours": 2, "cpus": 8, "memory_gib": 64},
        "benchmark_iterations": 2000,
        "benchmark_runtime_limit_hours": 65,
        "benchmark_peak_rss_limit_gib": 56,
        "benchmark_projection_overhead_factor": 1.2,
    }
    required_schemas = {
        "graph_contract",
        "prepared_run_manifest",
        "chain_checkpoint_v2",
        "scalar_draw_chunk",
        "spatial_draw_chunk",
        "chain_status",
        "merged_scalar_draws",
        "merged_spatial_draws",
        "diagnostics",
        "county_effect_summary",
        "comparison_candidate",
        "independent_verification",
        "release_manifest",
        "gate",
    }
    assert set(config["output_schemas"]) == required_schemas
    assert all(config["output_schemas"][name] for name in required_schemas)


def test_contract_hash_uses_canonical_json_and_hex_scales(synthetic_graph) -> None:
    payload = {
        "components": [
            {
                "members": [synthetic_graph.counties[index] for index in component],
                "scale_hex": float(synthetic_graph.component_scale[position]).hex(),
            }
            for position, component in enumerate(synthetic_graph.components)
        ],
        "counties_sha256": _sha256(
            "".join(f"{county}\n" for county in synthetic_graph.counties).encode("utf-8")
        ),
        "edges_sha256": _sha256(b"01001|01003\n01003|01005\n02001|02003\n"),
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    assert synthetic_graph.contract_sha256 == _sha256(canonical)
