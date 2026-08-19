from __future__ import annotations

import copy
import hashlib
import json
import os
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
    commit_spatial_draw_chunk,
    combined_county_effect,
    componentwise_center,
    frozen_graph_contract_from_execution,
    load_spatial_checkpoint,
    merge_spatial_draw_chunks,
    save_spatial_checkpoint,
    spatial_design_schema,
    spatial_checkpoint_identity,
    spatial_model_frame_sha256,
    spatial_parameter_schema,
    spatial_prior_schema,
    validate_spatial_chunk_inventory,
    validate_structured_effect,
)
from bayes_constrained.exact_validation import enumerate_feasible_states  # noqa: E402
from bayes_constrained.diagnostics import spatial_diagnostics_table  # noqa: E402
from bayes_constrained.model import (  # noqa: E402
    DEFAULT_PRIOR_SPECIFICATION,
    Design,
    PriorSpecification,
    Theta,
    count_logpmf,
    crude_intercept_prior,
    linear_predictor,
    log_likelihood,
    log_posterior_theta,
    make_design,
    mu,
)
from bayes_constrained import sampler as sampler_module  # noqa: E402
from bayes_constrained import spatial_bym2 as spatial_module  # noqa: E402
from bayes_constrained.sampler import (  # noqa: E402
    SpatialMALAState,
    _local_loglik,
    advance_spatial_mala_adaptation,
    run_mcmc_chain_hpc,
    spatial_county_score,
    spatial_mala_log_q,
    update_spatial_fields_mala,
    update_spatial_hyperparameters,
)
from bayes_constrained.validation_cases import structural_six_cycle_frame  # noqa: E402


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
TEST_SCALAR_PARAMETER_SCHEMA = ("sigma_county", "phi_structured")
SPATIAL_COUNTER_SCHEMA = (
    "transfer",
    "interval_transfer",
    "interval_path",
    "swap_2x2",
    "cycle_swap",
    "blocked_refresh",
    "beta",
    "state",
    "year",
    "log_sigma_state",
    "log_sigma_year",
    "log_kappa",
    "spatial_hyperparameters",
    "mala",
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value) -> str:
    return _sha256(_canonical_bytes(value))


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _theta_semantic(theta: Theta) -> dict[str, object]:
    return {
        "beta": [float(value).hex() for value in theta.beta],
        "state_effect": [float(value).hex() for value in theta.state_effect],
        "year_effect": [float(value).hex() for value in theta.year_effect],
        "log_sigma_state": float(theta.log_sigma_state).hex(),
        "log_sigma_year": float(theta.log_sigma_year).hex(),
        "log_kappa": float(theta.log_kappa).hex(),
    }


def _adjacency_payload(edges: list[tuple[str, str]], counties: list[str]) -> bytes:
    rows = ["County Name|County GEOID|Neighbor Name|Neighbor GEOID"]
    for county in counties:
        rows.append(f"{county}|{county}|{county}|{county}")
    for left, right in edges:
        rows.append(f"{left}|{left}|{right}|{right}")
        rows.append(f"{right}|{right}|{left}|{left}")
    return ("\n".join(rows) + "\n").encode("utf-8")


def _spatial_model_case(tmp_path: Path):
    counties = ["01001", "01003", "01005"]
    edges = [("01001", "01003"), ("01003", "01005")]
    payload = _adjacency_payload(edges, counties)
    adjacency = tmp_path / "model-adjacency.txt"
    adjacency.write_bytes(payload)
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
    rows = []
    for county in counties:
        period = sum(counts[(county, year)] for year in ("2019", "2020"))
        for year in ("2019", "2020"):
            value = counts[(county, year)]
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
                    "latent_count": value,
                    "period_total": period,
                }
            )
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = int(frame["latent_count"].sum())
    graph = build_bym2_graph(
        frame,
        adjacency,
        expected_sha256=_sha256(payload),
    )
    design = make_design(frame, spatial_graph=graph)
    beta = np.linspace(-0.1, 0.1, design.x.shape[1])
    beta[0] = -6.8
    theta = Theta(
        beta=beta,
        state_effect=np.zeros(1),
        year_effect=np.asarray([-0.1, 0.1]),
        log_sigma_state=np.log(0.2),
        log_sigma_year=np.log(0.2),
        log_kappa=np.log(4.0),
        spatial_structured=componentwise_center(
            np.asarray([-0.3, 0.1, 0.2]), graph
        ),
        spatial_unstructured=np.asarray([0.2, -0.1, 0.3]),
        log_sigma_county=np.log(0.7),
        logit_phi_structured=np.log(0.4 / 0.6),
    )
    assert len(theta.beta) == design.x.shape[1]
    return frame, frame["latent_count"].to_numpy(dtype=int), design, theta


def _spatial_identity(
    graph,
    *,
    frame: pd.DataFrame | None = None,
    design: Design | None = None,
    prior: PriorSpecification | None = None,
    **overrides,
):
    if design is None:
        row_count = len(graph.row_county_index)
        design = Design(
            x=np.ones((row_count, 1), dtype=np.float64),
            columns=["Intercept"],
            offset=np.zeros(row_count, dtype=np.float64),
            state_index=np.zeros(row_count, dtype=np.int64),
            year_index=np.zeros(row_count, dtype=np.int64),
            states=["00"],
            years=["2019"],
            spatial_graph=graph,
        )
    if frame is None:
        frame = pd.DataFrame(
            {
                "county_fips": [
                    graph.counties[int(index)] for index in graph.row_county_index
                ],
                "population": np.ones(len(graph.row_county_index), dtype=np.float64),
                "year": ["2019"] * len(graph.row_county_index),
                "q003_national_year_total": [1] * len(graph.row_county_index),
            }
        )
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
        "prior": spatial_prior_schema(prior),
        "intercept_mean_rule": "crude_national_log_rate",
        "intercept_mean_float_hex": float(intercept_mean).hex(),
        "design_schema": spatial_design_schema(design),
        "parameter_schema": spatial_parameter_schema(design),
        "extension_epoch": 0,
        "extension_authorization_sha256": "0" * 64,
    }
    target.update(overrides.pop("target", {}))
    chain = {
        "chain_id": 1,
        "chain_seed": 74291,
        "allocation_initialization_seed": 74251,
        "spatial_initialization_seed": 74261,
    }
    chain.update(overrides.pop("chain", {}))
    if overrides:
        raise AssertionError(f"unused identity overrides: {overrides}")
    return spatial_checkpoint_identity(target=target, **chain)


def _checkpoint_counters(
    iteration: int,
    *,
    adaptation: SpatialMALAState | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    state = SpatialMALAState() if adaptation is None else adaptation
    accepted = {name: 0 for name in SPATIAL_COUNTER_SCHEMA}
    proposed = {name: 0 for name in SPATIAL_COUNTER_SCHEMA}
    accepted["mala"] = state.accepted
    proposed["mala"] = iteration // 5
    for name in (
        "beta",
        "state",
        "year",
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
        "spatial_hyperparameters",
    ):
        proposed[name] = iteration
    return accepted, proposed


def _spatial_scalar_frame(
    theta: Theta,
    design: Design,
    draw_ids: np.ndarray,
    *,
    chain_id: int = 1,
    extension_epoch: int = 0,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for draw_id in draw_ids:
        for row in sampler_module._theta_to_rows(
            theta,
            design,
            chain=chain_id,
            draw=int(draw_id),
            iteration=45_000 + 30 * int(draw_id),
        ):
            rows.append(
                {
                    "chain_id": int(row["chain"]),
                    "draw_id": int(row["draw"]),
                    "extension_epoch": extension_epoch,
                    "parameter": str(row["parameter"]),
                    "value": np.float64(row["value"]),
                }
            )
    return pd.DataFrame(rows)


def _mala_state_at(iteration: int) -> SpatialMALAState:
    state = SpatialMALAState()
    for attempted_iteration in range(5, iteration + 1, 5):
        state = advance_spatial_mala_adaptation(
            state,
            accepted=(attempted_iteration // 5) % 2 == 0,
            iteration=attempted_iteration,
            extension_epoch=0,
        )
    return state


def _save_empty_spatial_checkpoint(
    path: Path,
    *,
    frame: pd.DataFrame,
    y: np.ndarray,
    design: Design,
    theta: Theta,
    identity: dict[str, object],
    adaptation_state: dict[str, object] | None = None,
    iteration: int = 0,
    accepted: dict[str, int] | None = None,
    proposed: dict[str, int] | None = None,
    current_target: float | None = None,
    prior: PriorSpecification | None = None,
    intercept_mean: float | None = None,
) -> None:
    runtime_intercept = (
        crude_intercept_prior(frame)
        if intercept_mean is None
        else float(intercept_mean)
    )
    adaptation = (
        SpatialMALAState()
        if adaptation_state is None
        else SpatialMALAState.from_dict(adaptation_state)
    )
    default_accepted, default_proposed = _checkpoint_counters(
        iteration,
        adaptation=adaptation,
    )
    save_spatial_checkpoint(
        path,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=np.random.default_rng(74291),
        frame=frame,
        design=design,
        intercept_mean=runtime_intercept,
        prior=prior,
        iteration=iteration,
        saved_draws=0,
        current_target=(
            log_posterior_theta(
                y,
                theta,
                design,
                intercept_mean=runtime_intercept,
                prior=prior,
            )
            if current_target is None
            else current_target
        ),
        accepted=default_accepted if accepted is None else accepted,
        proposed=default_proposed if proposed is None else proposed,
        committed_chunks=[],
        pending_scalar=pd.DataFrame(),
        pending_structured=np.empty((0, len(design.spatial_graph.counties))),
        pending_unstructured=np.empty((0, len(design.spatial_graph.counties))),
        adaptation_state=(
            adaptation.to_dict()
        ),
        next_draw_id=1,
        output_positions={"scalar_rows": 0, "spatial_draws": 0},
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"target": {"extension_epoch": 0.5}},
        {"chain": {"chain_id": 1.5}},
        {"chain": {"chain_seed": 74291.5}},
        {"chain": {"allocation_initialization_seed": True}},
        {"chain": {"spatial_initialization_seed": "74261"}},
    ],
)
def test_spatial_identity_rejects_fractional_boolean_and_string_integers(
    synthetic_graph, overrides: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match="exact integer"):
        _spatial_identity(synthetic_graph, **overrides)


@pytest.mark.parametrize(
    "replacement",
    ["A" * 64, int("1" * 64)],
)
def test_spatial_identity_rejects_noncanonical_hash_strings(
    synthetic_graph,
    replacement,
) -> None:
    with pytest.raises(ValueError, match="lowercase|SHA-256|string"):
        _spatial_identity(
            synthetic_graph,
            target={"config_sha256": replacement},
        )


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
        "resume_from",
        "attempt_evidence",
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


def test_spatial_disabled_default_nb2_trace_rng_counters_and_checkpoint_schema_are_exact(
    tmp_path: Path,
) -> None:
    reference = json.loads(
        (ROOT / "tests" / "fixtures" / "sr_v2_primary_rng_reference.json").read_text(
            encoding="utf-8"
        )
    )
    frame = structural_six_cycle_frame()
    design = make_design(frame)
    assert design.spatial_graph is None
    assert design.columns == reference["input"]["design_columns"]
    y = np.asarray(reference["input"]["initial_y"], dtype=int)
    frozen_theta = reference["input"]["initial_theta"]
    theta = Theta(
        np.asarray([float.fromhex(value) for value in frozen_theta["beta"]]),
        np.asarray([float.fromhex(value) for value in frozen_theta["state_effect"]]),
        np.asarray([float.fromhex(value) for value in frozen_theta["year_effect"]]),
        float.fromhex(frozen_theta["log_sigma_state"]),
        float.fromhex(frozen_theta["log_sigma_year"]),
        float.fromhex(frozen_theta["log_kappa"]),
    )
    intercept_mean = crude_intercept_prior(frame)
    assert float(intercept_mean).hex() == reference["input"]["intercept_mean_hex"]
    rng = np.random.default_rng(reference["driver"]["seed"])
    move = sampler_module.build_move_state(frame, y)
    weights = sampler_module._normalized_move_weights({})
    scales = sampler_module._proposal_scales(
        theta, likelihood_family=design.likelihood_family
    )
    assert {key: float(value).hex() for key, value in weights.items()} == reference[
        "driver"
    ]["move_weights_hex"]
    assert {key: float(value).hex() for key, value in scales.items()} == reference[
        "driver"
    ]["proposal_scales_hex"]
    assert list(scales) == reference["driver"]["parameter_block_order"]
    accepted = {
        "transfer": 0,
        "interval_transfer": 0,
        "interval_path": 0,
        "swap_2x2": 0,
        "cycle_swap": 0,
        "blocked_refresh": 0,
    }
    proposed = {key: 0 for key in accepted}
    param_accept = {key: 0 for key in scales}
    param_prop = {key: 0 for key in scales}
    current = log_posterior_theta(
        y, theta, design, intercept_mean=intercept_mean
    )
    trace = []
    for iteration in range(1, reference["driver"]["iterations"] + 1):
        fitted = mu(theta, design)
        kappa = float(np.exp(theta.log_kappa))
        for _ in range(reference["driver"]["count_moves_per_iteration"]):
            draw = rng.uniform()
            if draw < weights["state_year_transfer"]:
                proposed["transfer"] += 1
                accepted["transfer"] += int(
                    sampler_module.state_year_transfer(y, move, fitted, kappa, rng)
                )
            elif draw < weights["state_year_transfer"] + weights["county_period_exploration"]:
                proposed["interval_transfer"] += 1
                accepted["interval_transfer"] += int(
                    sampler_module.period_interval_transfer(y, move, fitted, kappa, rng)
                )
            elif draw < sum(
                weights[key]
                for key in (
                    "state_year_transfer",
                    "county_period_exploration",
                    "interval_path_transfer",
                )
            ):
                proposed["interval_path"] += 1
                accepted["interval_path"] += int(
                    sampler_module.interval_path_transfer(y, move, fitted, kappa, rng)
                )
            elif draw < sum(
                weights[key]
                for key in (
                    "state_year_transfer",
                    "county_period_exploration",
                    "interval_path_transfer",
                    "swap_2x2",
                )
            ):
                proposed["swap_2x2"] += 1
                accepted["swap_2x2"] += int(
                    sampler_module.state_2x2_swap(y, move, fitted, kappa, rng)
                )
            else:
                proposed["cycle_swap"] += 1
                accepted["cycle_swap"] += int(
                    sampler_module.state_cycle_swap(
                        y,
                        move,
                        fitted,
                        kappa,
                        rng,
                        max_cycle_half_length=reference["driver"][
                            "max_cycle_half_length"
                        ],
                    )
                )
        if iteration % reference["driver"]["blocked_refresh_frequency"] == 0:
            attempts = reference["driver"]["blocked_refresh_attempts"]
            proposed["blocked_refresh"] += attempts
            accepted["blocked_refresh"] += sampler_module.blocked_refresh(
                y, move, fitted, kappa, rng, attempts=attempts
            )
        current = log_posterior_theta(
            y, theta, design, intercept_mean=intercept_mean
        )
        for block, scale in scales.items():
            param_prop[block] += 1
            theta, current, ok = sampler_module._update_theta_block(
                y,
                theta,
                design,
                intercept_mean,
                rng,
                block,
                scale,
                current,
            )
            param_accept[block] += int(ok)
        semantic = {
            "iteration": iteration,
            "y": y.tolist(),
            "theta": _theta_semantic(theta),
            "accepted": dict(accepted),
            "proposed": dict(proposed),
            "param_accept": dict(param_accept),
            "param_prop": dict(param_prop),
            "rng_state": copy.deepcopy(rng.bit_generator.state),
        }
        trace.append(_canonical_sha256(semantic))
    assert trace == reference["trace_semantic_sha256"]
    assert y.tolist() == reference["final"]["y"]
    assert accepted == reference["final"]["accepted"]
    assert proposed == reference["final"]["proposed"]
    assert param_accept == reference["final"]["param_accept"]
    assert param_prop == reference["final"]["param_prop"]
    assert float(current) == pytest.approx(
        float(reference["final"]["current_lp_decimal"]), rel=1e-14, abs=1e-12
    )
    assert rng.bit_generator.state == reference["final"]["rng_state"]
    continuation = np.random.default_rng()
    continuation.bit_generator.state = copy.deepcopy(rng.bit_generator.state)
    assert continuation.bit_generator.random_raw(8).tolist() == reference["final"][
        "next_raw_uint64"
    ]

    parameter_rows = sampler_module._theta_to_rows(
        theta, design, chain=7, draw=11, iteration=30
    )
    assert all(set(row) == {"chain", "draw", "iteration", "parameter", "value"} for row in parameter_rows)
    assert all(
        (row["chain"], row["draw"], row["iteration"]) == (7, 11, 30)
        for row in parameter_rows
    )
    assert [row["parameter"] for row in parameter_rows] == [
        *reference["input"]["design_columns"],
        "state_effect[01]",
        "year_effect[2019]",
        "year_effect[2020]",
        "year_effect[2021]",
        "sigma_state",
        "sigma_year",
        "kappa",
    ]
    expected_parameter_values = [
        *theta.beta,
        *(theta.state_effect - theta.state_effect.mean()),
        *(theta.year_effect - theta.year_effect.mean()),
        np.exp(theta.log_sigma_state),
        np.exp(theta.log_sigma_year),
        np.exp(theta.log_kappa),
    ]
    assert [float(row["value"]).hex() for row in parameter_rows] == [
        float(value).hex() for value in expected_parameter_values
    ]

    checkpoint = tmp_path / "checkpoint_iter_000000030.npz"
    sampler_module.save_chain_checkpoint(
        checkpoint,
        y=y,
        theta=theta,
        rng=rng,
        iteration=30,
        saved_draws=0,
        current_lp=current,
        accepted=accepted,
        proposed=proposed,
        param_accept=param_accept,
        param_prop=param_prop,
    )
    with np.load(checkpoint, allow_pickle=True) as stored:
        assert sorted(stored.files) == reference["checkpoint"]["base_keys"]
        assert not any(
            key.startswith(tuple(reference["checkpoint"]["spatial_disabled_forbidden_key_prefixes"]))
            for key in stored.files
        )
    assert {path.name for path in tmp_path.iterdir()} == {checkpoint.name}


def test_real_yaml_graph_certificate_has_one_explicit_builder_adapter() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    frozen = frozen_graph_contract_from_execution(config)
    assert frozen == {
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
    frame = pd.read_parquet(MODEL_FRAME_PATH, columns=["county_fips", "year"])
    graph = build_bym2_graph(
        frame,
        ADJACENCY_PATH,
        expected_sha256=config["source_authorities"][
            "outputs/scientific_reports_v2/spatial_residual_diagnostics/county_adjacency2024.txt"
        ],
        frozen_contract=frozen,
    )
    assert graph.contract_sha256 == "1e781fb7c314025c39543c4691e61713aa0b3c9d3e23e4d2a9a00c744135befe"
    fractional = copy.deepcopy(config)
    fractional["graph_certificate"]["nodes"] = 3142.0
    with pytest.raises(ValueError, match="exact integer|translated"):
        frozen_graph_contract_from_execution(fractional)


def test_spatial_config_code_and_manuscript_share_the_crude_intercept_rule() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    intercept = config["model"]["priors"]["intercept"]
    assert intercept == {
        "distribution": "Normal",
        "mean_rule": "crude_national_log_rate",
        "sd": 5.0,
    }
    assert "model_frame_semantic_sha256" in config["fingerprints"]["target_fields"]
    assert "intercept_mean_rule" in config["fingerprints"]["target_fields"]
    assert "intercept_mean_float_hex" in config["fingerprints"]["target_fields"]
    manuscript_source = (
        ROOT / "src" / "submission_viz" / "manuscript_text.py"
    ).read_text(encoding="utf-8")
    assert "centered on the crude national log rate" in manuscript_source
    governing_plan = (
        ROOT
        / "docs"
        / "superpowers"
        / "plans"
        / "2026-08-18-sr-v2-spatial-bym2.md"
    ).read_text(encoding="utf-8")
    assert "Corrective amendment" in governing_plan
    assert "crude_national_log_rate" in governing_plan


def test_legacy_six_positional_theta_and_default_design_remain_compatible() -> None:
    theta = Theta(
        np.asarray([1.0]),
        np.asarray([0.0]),
        np.asarray([0.0]),
        -1.0,
        -1.0,
        np.log(10.0),
    )
    design = Design(
        np.ones((1, 1)),
        ["Intercept"],
        np.zeros(1),
        np.zeros(1, dtype=int),
        np.zeros(1, dtype=int),
        ["01"],
        ["2019"],
    )
    assert theta.spatial_structured is None
    assert theta.spatial_unstructured is None
    assert theta.log_sigma_county is None
    assert theta.logit_phi_structured is None
    assert design.spatial_graph is None
    np.testing.assert_array_equal(linear_predictor(theta, design), [1.0])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spatial_structured", np.zeros(1, dtype=np.float64)),
        ("spatial_unstructured", np.zeros(1, dtype=np.float64)),
        ("log_sigma_county", 0.0),
        ("logit_phi_structured", 0.0),
    ],
)
def test_legacy_checkpoint_writer_rejects_every_partial_spatial_state(
    field: str,
    value,
) -> None:
    theta = Theta(
        np.asarray([0.0]),
        np.asarray([0.0]),
        np.asarray([0.0]),
        -1.0,
        -1.0,
        np.log(10.0),
    )
    setattr(theta, field, value)
    with pytest.raises(ValueError, match="schema-v2 spatial checkpoint"):
        sampler_module._theta_payload(theta)


def test_spatial_design_rejects_graph_row_mapping_from_a_different_frame_order(
    tmp_path: Path,
) -> None:
    frame, _, design, _ = _spatial_model_case(tmp_path)
    permuted = frame.iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError, match="row.*county|mapping|frame order"):
        make_design(permuted, spatial_graph=design.spatial_graph)


def test_zero_spatial_state_preserves_predictor_and_county_effect_is_constant_by_year(
    tmp_path: Path,
) -> None:
    frame, _y, spatial_design, theta = _spatial_model_case(tmp_path)
    default_design = make_design(frame)
    zero = theta.copy()
    zero.spatial_structured = np.zeros(3)
    zero.spatial_unstructured = np.zeros(3)
    zero.log_sigma_county = 0.0
    zero.logit_phi_structured = 0.0
    np.testing.assert_array_equal(
        linear_predictor(zero, spatial_design),
        linear_predictor(zero, default_design),
    )

    delta = linear_predictor(theta, spatial_design) - linear_predictor(
        theta, default_design
    )
    for county in frame["county_fips"].unique():
        county_rows = frame["county_fips"].eq(county).to_numpy()
        np.testing.assert_allclose(
            delta[county_rows], delta[county_rows][0], rtol=0.0, atol=1e-15
        )


def test_canonical_full_target_uses_the_existing_nb2_likelihood_and_prior(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    intercept_mean = crude_intercept_prior(frame)
    target = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
    assert np.isfinite(target)
    kappa = float(np.exp(theta.log_kappa))
    np.testing.assert_allclose(
        log_likelihood(y, theta, design),
        count_logpmf(y, mu(theta, design), kappa=kappa).sum(),
        rtol=0.0,
        atol=0.0,
    )


def test_latent_count_local_ratio_equals_full_spatial_target_ratio(tmp_path: Path) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    changed = y.copy()
    changed[[0, 2]] += np.asarray([1, -1])
    intercept_mean = crude_intercept_prior(frame)
    full = log_posterior_theta(
        changed, theta, design, intercept_mean=intercept_mean
    ) - log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
    affected = np.asarray([0, 2])
    fitted = mu(theta, design)
    local = _local_loglik(
        changed[affected], fitted[affected], float(np.exp(theta.log_kappa))
    ) - _local_loglik(
        y[affected], fitted[affected], float(np.exp(theta.log_kappa))
    )
    assert full == pytest.approx(local, rel=0.0, abs=1e-12)


def test_spatial_nb2_score_matches_target_floor_and_clip_derivatives(
    synthetic_graph,
) -> None:
    graph = synthetic_graph
    design = Design(
        x=np.ones((6, 1)),
        columns=["Intercept"],
        offset=np.asarray([0.0, -29.0, 31.0, 0.0, 0.0, 0.0]),
        state_index=np.zeros(6, dtype=int),
        year_index=np.zeros(6, dtype=int),
        states=["01"],
        years=["2019"],
        spatial_graph=graph,
    )
    theta = Theta(
        np.asarray([0.0]),
        np.zeros(1),
        np.zeros(1),
        -1.0,
        -1.0,
        np.log(4.0),
        spatial_structured=np.zeros(6),
        spatial_unstructured=np.zeros(6),
        log_sigma_county=0.0,
        logit_phi_structured=0.0,
    )
    score = spatial_county_score(np.asarray([2, 2, 2, 0, 0, 0]), theta, design)
    expected_first = 2.0 - 6.0 * 1.0 / 5.0
    assert score[0] == pytest.approx(expected_first)
    assert score[1] == 0.0  # nb2_logpmf floors exp(-29) to 1e-12
    assert score[2] == 0.0  # predictor is clipped at +30
    step = 1.0e-6
    for index in range(3):
        plus = theta.copy()
        minus = theta.copy()
        plus.spatial_unstructured[index] += step
        minus.spatial_unstructured[index] -= step
        numerical = (
            log_likelihood(np.asarray([2, 2, 2, 0, 0, 0]), plus, design)
            - log_likelihood(np.asarray([2, 2, 2, 0, 0, 0]), minus, design)
        ) / (2.0 * step)
        assert numerical == pytest.approx(
            np.sqrt(0.5) * score[index], rel=2e-6, abs=2e-8
        )


def test_spatial_mala_gradients_match_canonical_full_target_finite_difference(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    intercept_mean = crude_intercept_prior(frame)
    gradient_u, gradient_v = sampler_module._spatial_gradients(y, theta, design)
    direction_u = componentwise_center(
        np.asarray([0.7, -0.2, -0.5], dtype=np.float64),
        design.spatial_graph,
    )
    direction_v = np.asarray([-0.4, 0.3, 0.8], dtype=np.float64)
    step = 1.0e-6

    def directional_difference(field: str, direction: np.ndarray) -> float:
        plus = theta.copy()
        minus = theta.copy()
        setattr(plus, field, getattr(plus, field) + step * direction)
        setattr(minus, field, getattr(minus, field) - step * direction)
        return (
            log_posterior_theta(
                y,
                plus,
                design,
                intercept_mean=intercept_mean,
            )
            - log_posterior_theta(
                y,
                minus,
                design,
                intercept_mean=intercept_mean,
            )
        ) / (2.0 * step)

    assert directional_difference(
        "spatial_structured", direction_u
    ) == pytest.approx(float(gradient_u @ direction_u), rel=2e-6, abs=2e-8)
    assert directional_difference(
        "spatial_unstructured", direction_v
    ) == pytest.approx(float(gradient_v @ direction_v), rel=2e-6, abs=2e-8)


def test_centered_subspace_mala_forward_reverse_density_is_exact(synthetic_graph) -> None:
    current_u = componentwise_center(np.asarray([0.2, -0.4, 0.7, 0.5, -0.2, 0.0]), synthetic_graph)
    proposed_u = componentwise_center(np.asarray([-0.1, 0.3, 0.2, -0.4, 0.8, 0.0]), synthetic_graph)
    current_v = np.linspace(-0.3, 0.2, 6)
    proposed_v = np.linspace(0.25, -0.15, 6)
    grad_current_u = componentwise_center(np.linspace(-0.2, 0.3, 6), synthetic_graph)
    grad_proposed_u = componentwise_center(np.linspace(0.4, -0.1, 6), synthetic_graph)
    grad_current_v = np.linspace(-0.5, 0.5, 6)
    grad_proposed_v = np.linspace(0.1, -0.4, 6)
    epsilon_u, epsilon_v = 0.02, 0.04
    forward = spatial_mala_log_q(
        proposed_u,
        proposed_v,
        from_structured=current_u,
        from_unstructured=current_v,
        gradient_structured=grad_current_u,
        gradient_unstructured=grad_current_v,
        epsilon_structured=epsilon_u,
        epsilon_unstructured=epsilon_v,
        graph=synthetic_graph,
    )
    reverse = spatial_mala_log_q(
        current_u,
        current_v,
        from_structured=proposed_u,
        from_unstructured=proposed_v,
        gradient_structured=grad_proposed_u,
        gradient_unstructured=grad_proposed_v,
        epsilon_structured=epsilon_u,
        epsilon_unstructured=epsilon_v,
        graph=synthetic_graph,
    )
    f_u = proposed_u - current_u - 0.5 * epsilon_u**2 * grad_current_u
    r_u = current_u - proposed_u - 0.5 * epsilon_u**2 * grad_proposed_u
    f_v = proposed_v - current_v - 0.5 * epsilon_v**2 * grad_current_v
    r_v = current_v - proposed_v - 0.5 * epsilon_v**2 * grad_proposed_v
    expected = (
        (f_u @ f_u - r_u @ r_u) / (2.0 * epsilon_u**2)
        + (f_v @ f_v - r_v @ r_v) / (2.0 * epsilon_v**2)
    )
    assert reverse - forward == pytest.approx(expected, rel=0.0, abs=1e-12)


def test_mala_adaptation_has_exact_100_attempt_windows_and_freezes_after_window_90() -> None:
    state = SpatialMALAState()
    for attempt in range(1, 9001):
        iteration = attempt * 5
        state = advance_spatial_mala_adaptation(
            state,
            accepted=(attempt % 2 == 0),
            iteration=iteration,
            extension_epoch=0,
        )
    assert state.attempted == 9000
    assert state.windows_completed == 90
    assert state.window_attempted == 0
    assert state.adaptation_frozen is True
    frozen = state
    for attempt in range(10):
        state = advance_spatial_mala_adaptation(
            state,
            accepted=True,
            iteration=45005 + attempt * 5,
            extension_epoch=0,
        )
    assert state.multiplier == frozen.multiplier
    extension = advance_spatial_mala_adaptation(
        SpatialMALAState(), accepted=True, iteration=5, extension_epoch=1
    )
    assert extension.adaptation_frozen is True
    assert extension.multiplier == 1.0


def test_short_spatial_kernel_recovery_stays_finite_centered_and_canonical(
    tmp_path: Path,
) -> None:
    frame, _, design, theta = _spatial_model_case(tmp_path)
    y = np.asarray([9, 8, 4, 4, 0, 0], dtype=int)
    theta.spatial_structured[:] = 0.0
    theta.spatial_unstructured[:] = 0.0
    theta.log_sigma_county = np.log(0.5)
    theta.logit_phi_structured = 0.0
    intercept_mean = crude_intercept_prior(frame)
    rng = np.random.default_rng(9182)
    state = SpatialMALAState()
    current = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
    accepted = 0
    retained_effects = []
    for iteration in range(1, 501):
        theta, current, _ = update_spatial_hyperparameters(
            y,
            theta,
            design,
            intercept_mean=intercept_mean,
            rng=rng,
            current_target=current,
        )
        if iteration % 5 == 0:
            theta, current, state, ok = update_spatial_fields_mala(
                y,
                theta,
                design,
                intercept_mean=intercept_mean,
                rng=rng,
                current_target=current,
                adaptation_state=state,
                iteration=iteration,
                extension_epoch=0,
            )
            accepted += int(ok)
            if iteration > 250:
                retained_effects.append(
                    combined_county_effect(
                        theta.spatial_structured,
                        theta.spatial_unstructured,
                        theta.log_sigma_county,
                        theta.logit_phi_structured,
                        design.spatial_graph,
                    )
                )
    assert np.isfinite(current)
    assert accepted > 0
    validate_structured_effect(theta.spatial_structured, design.spatial_graph)
    recovered = np.mean(retained_effects, axis=0)
    assert recovered[0] > recovered[1] > recovered[2]
    assert recovered[0] - recovered[1] > 0.3
    assert recovered[1] - recovered[2] > 0.3
    assert current == pytest.approx(
        log_posterior_theta(y, theta, design, intercept_mean=intercept_mean),
        rel=1e-12,
        abs=1e-8,
    )


def test_spatial_checkpoint_v2_round_trip_recomputes_target_and_rng_continuation(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    intercept_mean = crude_intercept_prior(frame)
    current = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
    rng = np.random.default_rng(74291)
    _ = rng.normal(size=7)
    continuation = np.random.default_rng()
    continuation.bit_generator.state = copy.deepcopy(rng.bit_generator.state)
    expected = continuation.normal(size=8)
    sigma_value = np.float64.fromhex("0x1.0000000000001p-3")
    phi_value = np.float64.fromhex("0x1.999999999999bp-2")
    pending_scalar = _spatial_scalar_frame(
        theta,
        design,
        np.asarray([1], dtype=np.int64),
    )
    pending_scalar.loc[
        pending_scalar["parameter"].eq("sigma_county"), "value"
    ] = sigma_value
    pending_scalar.loc[
        pending_scalar["parameter"].eq("phi_structured"), "value"
    ] = phi_value
    iteration = 45_030
    adaptation = _mala_state_at(iteration)
    accepted, proposed = _checkpoint_counters(
        iteration,
        adaptation=adaptation,
    )
    checkpoint = tmp_path / "checkpoint_iter_000045030.json"
    save_spatial_checkpoint(
        checkpoint,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=rng,
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        iteration=iteration,
        saved_draws=1,
        current_target=current,
        accepted=accepted,
        proposed=proposed,
        committed_chunks=[],
        pending_scalar=pending_scalar,
        pending_structured=theta.spatial_structured[None, :],
        pending_unstructured=theta.spatial_unstructured[None, :],
        adaptation_state=adaptation.to_dict(),
        next_draw_id=2,
        output_positions={
            "scalar_rows": len(identity["target"]["parameter_schema"]),
            "spatial_draws": 1,
        },
    )
    checkpoint_payload = json.loads(checkpoint.read_text(encoding="ascii"))
    frozen_fields = set(
        yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["output_schemas"]
        ["chain_checkpoint_v2"]["exact_fields"]
    )
    expected_fields = {
        "schema_version",
        "run_id",
        "model_id",
        "target_fingerprint",
        "chain_fingerprint",
        "extension_epoch",
        "job_attempt",
        "chain_id",
        "seeds",
        "current_state",
        "rng_state",
        "current_target",
        "iteration",
        "saved_draws",
        "accepted",
        "proposed",
        "committed_chunks",
        "pending_buffers",
        "adaptation_state",
        "next_draw_id",
        "output_positions",
    }
    assert frozen_fields == spatial_module._SPATIAL_CHECKPOINT_FIELDS
    assert set(checkpoint_payload) == frozen_fields == expected_fields
    assert checkpoint_payload["run_id"] == identity["target"]["run_id"]
    assert checkpoint_payload["model_id"] == identity["target"]["model_id"]
    assert checkpoint_payload["chain_id"] == 1
    assert checkpoint.read_bytes() == _canonical_bytes(checkpoint_payload)
    loaded = load_spatial_checkpoint(
        checkpoint,
        expected_identity=identity,
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        chunk_dir=tmp_path / "chunks",
    )
    assert checkpoint.with_name(checkpoint.name + ".sha256").is_file()
    assert loaded["schema_version"] == 2
    assert loaded["identity"] == identity
    assert loaded["iteration"] == iteration
    assert loaded["next_draw_id"] == 2
    assert loaded["output_positions"] == {
        "scalar_rows": len(identity["target"]["parameter_schema"]),
        "spatial_draws": 1,
    }
    pd.testing.assert_frame_equal(loaded["pending_scalar"], pending_scalar)
    np.testing.assert_array_equal(
        loaded["pending_scalar"]["value"].to_numpy(dtype=np.float64).view(np.uint64),
        pending_scalar["value"].to_numpy(dtype=np.float64).view(np.uint64),
    )
    np.testing.assert_array_equal(
        loaded["theta"].spatial_structured, theta.spatial_structured
    )
    np.testing.assert_array_equal(loaded["theta"].spatial_unstructured, theta.spatial_unstructured)
    np.testing.assert_array_equal(loaded["rng"].normal(size=8), expected)


def test_spatial_checkpoint_save_binds_complete_runtime_target(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph,
        frame=frame,
        design=design,
    )
    intercept_mean = crude_intercept_prior(frame)

    wrong_family = copy.copy(design)
    wrong_family.likelihood_family = "poisson"
    with pytest.raises(ValueError, match="runtime target.*likelihood|likelihood.*identity"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-family.json",
            frame=frame,
            y=y,
            design=wrong_family,
            theta=theta,
            identity=identity,
            current_target=log_posterior_theta(
                y,
                theta,
                wrong_family,
                intercept_mean=intercept_mean,
            ),
        )

    renamed_prior = PriorSpecification(
        **{
            **DEFAULT_PRIOR_SPECIFICATION.to_dict(),
            "name": "same-density-wrong-identity",
        }
    )
    with pytest.raises(ValueError, match="runtime target.*prior|prior.*identity"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-prior.json",
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
            prior=renamed_prior,
        )

    relabeled_design = copy.copy(design)
    relabeled_design.columns = ["wrong_intercept", *design.columns[1:]]
    with pytest.raises(ValueError, match="runtime target.*design|design schema"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-design.json",
            frame=frame,
            y=y,
            design=relabeled_design,
            theta=theta,
            identity=identity,
        )

    wrong_parameter_target = copy.deepcopy(identity["target"])
    wrong_parameter_target["parameter_schema"] = list(
        reversed(wrong_parameter_target["parameter_schema"])
    )
    wrong_parameter_identity = spatial_checkpoint_identity(
        target=wrong_parameter_target,
        chain_id=1,
        chain_seed=74291,
        allocation_initialization_seed=74251,
        spatial_initialization_seed=74261,
    )
    with pytest.raises(ValueError, match="runtime target.*parameter|parameter schema"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-parameter-schema.json",
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=wrong_parameter_identity,
        )

    with pytest.raises(ValueError, match="intercept.*identity|crude_national_log_rate"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-intercept.json",
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
            intercept_mean=np.nextafter(intercept_mean, np.inf),
        )

    changed_frame = frame.copy()
    changed_frame["unused_runtime_marker"] = "changed"
    with pytest.raises(ValueError, match="model frame|frame.*identity"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-frame.json",
            frame=changed_frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
            intercept_mean=intercept_mean,
        )


def test_spatial_checkpoint_load_revalidates_runtime_target_not_just_fingerprint(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph,
        frame=frame,
        design=design,
    )
    checkpoint = tmp_path / "checkpoint.json"
    _save_empty_spatial_checkpoint(
        checkpoint,
        frame=frame,
        y=y,
        design=design,
        theta=theta,
        identity=identity,
    )
    intercept_mean = crude_intercept_prior(frame)

    relabeled_design = copy.copy(design)
    relabeled_design.states = ["99"]
    with pytest.raises(ValueError, match="runtime target.*design|design schema"):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=identity,
            frame=frame,
            design=relabeled_design,
            intercept_mean=intercept_mean,
            chunk_dir=tmp_path / "chunks-design",
        )

    renamed_prior = PriorSpecification(
        **{
            **DEFAULT_PRIOR_SPECIFICATION.to_dict(),
            "name": "same-density-wrong-identity",
        }
    )
    with pytest.raises(ValueError, match="runtime target.*prior|prior.*identity"):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=identity,
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
            prior=renamed_prior,
            chunk_dir=tmp_path / "chunks-prior",
        )

    changed_frame = frame.copy()
    changed_frame["unused_runtime_marker"] = "changed"
    with pytest.raises(ValueError, match="model frame|frame.*identity"):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=identity,
            frame=changed_frame,
            design=design,
            intercept_mean=intercept_mean,
            chunk_dir=tmp_path / "chunks-frame",
        )


@pytest.mark.parametrize(
    ("section", "field", "replacement", "match"),
    [
        ("target", "run_id", "wrong-run", "identity"),
        ("chain", "chain_id", 2, "identity"),
        ("target", "graph_contract_sha256", "4" * 64, "identity"),
        ("target", "source_manifest_sha256", "5" * 64, "identity"),
        ("target", "schema_id", "wrong-schema", "identity"),
    ],
)
def test_spatial_checkpoint_rejects_wrong_full_fingerprint(
    tmp_path: Path, section: str, field: str, replacement, match: str
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    intercept_mean = crude_intercept_prior(frame)
    checkpoint = tmp_path / "checkpoint.json"
    save_spatial_checkpoint(
        checkpoint,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=np.random.default_rng(1),
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        iteration=0,
        saved_draws=0,
        current_target=log_posterior_theta(
            y, theta, design, intercept_mean=intercept_mean
        ),
        accepted=_checkpoint_counters(0)[0],
        proposed=_checkpoint_counters(0)[1],
        committed_chunks=[],
        pending_scalar=pd.DataFrame(),
        pending_structured=np.empty((0, 3)),
        pending_unstructured=np.empty((0, 3)),
        adaptation_state=SpatialMALAState().to_dict(),
        next_draw_id=1,
        output_positions={"scalar_rows": 0, "spatial_draws": 0},
    )
    wrong = copy.deepcopy(identity)
    wrong[section][field] = replacement
    if section == "target" and field == "graph_contract_sha256":
        wrong["target"]["design_schema"]["graph_contract_sha256"] = replacement
    # Rebuild the fingerprints so this is a coherent but different target/chain,
    # not merely an internally corrupt identity mapping.
    wrong = spatial_checkpoint_identity(
        target=wrong["target"],
        chain_id=wrong["chain"]["chain_id"],
        chain_seed=wrong["chain"]["chain_seed"],
        allocation_initialization_seed=wrong["chain"]["allocation_initialization_seed"],
        spatial_initialization_seed=wrong["chain"]["spatial_initialization_seed"],
    )
    with pytest.raises(ValueError, match=match):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=wrong,
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
            chunk_dir=tmp_path / "chunks",
        )


def test_spatial_checkpoint_rejects_corrupt_sidecar_and_noncanonical_state(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    checkpoint = tmp_path / "checkpoint.json"
    save_spatial_checkpoint(
        checkpoint,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=np.random.default_rng(2),
        frame=frame,
        design=design,
        intercept_mean=crude_intercept_prior(frame),
        iteration=0,
        saved_draws=0,
        current_target=log_posterior_theta(
            y, theta, design, intercept_mean=crude_intercept_prior(frame)
        ),
        accepted=_checkpoint_counters(0)[0],
        proposed=_checkpoint_counters(0)[1],
        committed_chunks=[],
        pending_scalar=pd.DataFrame(),
        pending_structured=np.empty((0, 3)),
        pending_unstructured=np.empty((0, 3)),
        adaptation_state=SpatialMALAState().to_dict(),
        next_draw_id=1,
        output_positions={"scalar_rows": 0, "spatial_draws": 0},
    )
    checkpoint.with_name(checkpoint.name + ".sha256").write_text(
        "0" * 64 + "\n", encoding="ascii"
    )
    with pytest.raises(ValueError, match="SHA-256"):
        load_spatial_checkpoint(checkpoint, expected_identity=identity)


def test_spatial_checkpoint_rejects_sidecar_valid_but_target_stale_state(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    intercept_mean = crude_intercept_prior(frame)
    checkpoint = tmp_path / "checkpoint.json"
    save_spatial_checkpoint(
        checkpoint,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=np.random.default_rng(3),
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        iteration=0,
        saved_draws=0,
        current_target=log_posterior_theta(
            y, theta, design, intercept_mean=intercept_mean
        ),
        accepted=_checkpoint_counters(0)[0],
        proposed=_checkpoint_counters(0)[1],
        committed_chunks=[],
        pending_scalar=pd.DataFrame(),
        pending_structured=np.empty((0, 3)),
        pending_unstructured=np.empty((0, 3)),
        adaptation_state=SpatialMALAState().to_dict(),
        next_draw_id=1,
        output_positions={"scalar_rows": 0, "spatial_draws": 0},
    )
    payload = json.loads(checkpoint.read_text(encoding="ascii"))
    payload["current_target"] = np.nextafter(
        float.fromhex(payload["current_target"]), np.inf
    ).hex()
    checkpoint.write_bytes(_canonical_bytes(payload))
    checkpoint.with_name(checkpoint.name + ".sha256").write_bytes(
        (_sha256(checkpoint.read_bytes()) + "\n").encode("ascii")
    )
    with pytest.raises(ValueError, match="target"):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=identity,
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
            chunk_dir=tmp_path / "chunks",
        )


def test_spatial_checkpoint_rejects_noncanonical_json_duplicate_keys_and_base64(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    intercept_mean = crude_intercept_prior(frame)

    def check_rejected(name: str, mutate) -> None:
        checkpoint = tmp_path / f"{name}.json"
        _save_empty_spatial_checkpoint(
            checkpoint,
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
        )
        raw = mutate(checkpoint.read_bytes())
        checkpoint.write_bytes(raw)
        checkpoint.with_name(checkpoint.name + ".sha256").write_bytes(
            (_sha256(raw) + "\n").encode("ascii")
        )
        with pytest.raises(ValueError, match="canonical|schema|duplicate|base64"):
            load_spatial_checkpoint(
                checkpoint,
                expected_identity=identity,
                frame=frame,
                design=design,
                intercept_mean=intercept_mean,
                chunk_dir=tmp_path / f"{name}-chunks",
            )

    check_rejected(
        "whitespace",
        lambda raw: json.dumps(json.loads(raw), indent=2).encode("ascii"),
    )
    check_rejected(
        "duplicate",
        lambda raw: raw.replace(
            b'"schema_version":2',
            b'"schema_version":2,"schema_version":2',
            1,
        ),
    )

    def extra_key(raw: bytes) -> bytes:
        payload = json.loads(raw)
        payload["unexpected"] = True
        return _canonical_bytes(payload)

    check_rejected("extra-key", extra_key)

    def noncanonical_base64(raw: bytes) -> bytes:
        payload = json.loads(raw)
        payload["current_state"]["beta"]["data_base64"] += "="
        return _canonical_bytes(payload)

    check_rejected("base64", noncanonical_base64)


def test_spatial_checkpoint_rejects_noncanonical_theta_shapes_and_centering(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )

    shifted = theta.copy()
    shifted.state_effect = shifted.state_effect + 1.0
    with pytest.raises(ValueError, match="centered|state_effect"):
        _save_empty_spatial_checkpoint(
            tmp_path / "shifted.json",
            frame=frame,
            y=y,
            design=design,
            theta=shifted,
            identity=identity,
        )

    wrong_shape = theta.copy()
    wrong_shape.beta = np.append(wrong_shape.beta, 0.0)
    with pytest.raises(ValueError, match="shape|beta"):
        _save_empty_spatial_checkpoint(
            tmp_path / "wrong-shape.json",
            frame=frame,
            y=y,
            design=design,
            theta=wrong_shape,
            identity=identity,
            current_target=log_posterior_theta(
                y,
                theta,
                design,
                intercept_mean=crude_intercept_prior(frame),
            ),
        )


def test_spatial_checkpoint_rejects_fractional_job_attempt_and_incoherent_adaptation(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    intercept_mean = crude_intercept_prior(frame)
    base = dict(
        path=tmp_path / "fractional-attempt.json",
        identity=identity,
        extension_epoch=0,
        job_attempt=1.5,
        y=y,
        theta=theta,
        rng=np.random.default_rng(2),
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        iteration=0,
        saved_draws=0,
        current_target=log_posterior_theta(
            y, theta, design, intercept_mean=intercept_mean
        ),
        accepted=_checkpoint_counters(0)[0],
        proposed=_checkpoint_counters(0)[1],
        committed_chunks=[],
        pending_scalar=pd.DataFrame(),
        pending_structured=np.empty((0, 3)),
        pending_unstructured=np.empty((0, 3)),
        adaptation_state=SpatialMALAState().to_dict(),
        next_draw_id=1,
        output_positions={"scalar_rows": 0, "spatial_draws": 0},
    )
    with pytest.raises(ValueError, match="exact integer"):
        save_spatial_checkpoint(**base)

    incoherent = SpatialMALAState(
        attempted=1,
        accepted=0,
        window_attempted=1,
        window_accepted=1,
    ).to_dict()
    with pytest.raises(ValueError, match="adaptation"):
        _save_empty_spatial_checkpoint(
            tmp_path / "incoherent-adaptation.json",
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
            adaptation_state=incoherent,
            iteration=5,
        )

    with pytest.raises(ValueError, match="counter schema|counter universe"):
        _save_empty_spatial_checkpoint(
            tmp_path / "missing-counters.json",
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
            accepted={},
            proposed={},
        )


def _chunk_payload(
    counties: int,
    *,
    start: int = 1,
    count: int = 250,
    parameter_schema: tuple[str, ...] = TEST_SCALAR_PARAMETER_SCHEMA,
):
    draw_ids = np.arange(start, start + count, dtype=np.int64)
    scalar = pd.DataFrame(
        [
            {
                "chain_id": 1,
                "draw_id": int(draw),
                "extension_epoch": 0,
                "parameter": parameter,
                "value": offset + float(draw) / 100_000.0,
            }
            for draw in draw_ids
            for parameter, offset in (
                (
                    parameter,
                    (
                        0.5
                        if parameter == "sigma_county"
                        else 0.35
                        if parameter == "phi_structured"
                        else float(parameter_index + 1)
                    ),
                )
                for parameter_index, parameter in enumerate(parameter_schema)
            )
        ]
    )
    base_structured = np.arange(counties, dtype=np.float64)
    base_structured -= base_structured.mean()
    structured = np.repeat(base_structured[None, :], count, axis=0)
    unstructured = -structured.copy()
    return draw_ids, scalar, structured, unstructured


def test_paired_spatial_chunks_validate_exact_inventory_and_merge_without_duplicates(
    tmp_path: Path,
) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    chunk_dir = tmp_path / "chunks"
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)
    record = commit_spatial_draw_chunk(
        chunk_dir,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    records = validate_spatial_chunk_inventory(
        chunk_dir,
        expected_records=[record],
        expected_next_draw_id=251,
        expected_graph=graph,
    )
    assert records == [record]
    assert record["graph_contract_sha256"] == graph.contract_sha256
    assert record["county_count"] == 3
    assert record["parameter_schema"] == list(TEST_SCALAR_PARAMETER_SCHEMA)
    merged_scalar = tmp_path / "posterior_parameter_draws.parquet"
    merged_spatial = tmp_path / "draws_spatial.npz"
    merge_spatial_draw_chunks(
        chunk_dir,
        records=records,
        scalar_output=merged_scalar,
        spatial_output=merged_spatial,
        graph=graph,
    )
    scalar_result = pd.read_parquet(merged_scalar)
    assert len(scalar_result) == 500
    assert not scalar_result.duplicated(["chain_id", "draw_id", "parameter"]).any()
    with np.load(merged_spatial) as spatial:
        np.testing.assert_array_equal(spatial["draw_id"], draw_ids)
        np.testing.assert_array_equal(spatial["structured"], structured)
        np.testing.assert_array_equal(spatial["unstructured"], unstructured)

    (chunk_dir / "orphan.txt").write_text("orphan", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory|orphan"):
        validate_spatial_chunk_inventory(chunk_dir, expected_records=[record])


def test_spatial_chunk_manifest_and_npz_identity_schema_are_exact(
    tmp_path: Path,
) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    chunk_contract = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))[
        "output_schemas"
    ]["spatial_draw_chunk"]
    assert chunk_contract == {
        "format": "npz_float64",
        "exact_arrays": {
            "chain_id": {"dtype": "<i8", "shape": []},
            "draw_id": {"dtype": "<i8", "shape": ["draw_count"]},
            "extension_epoch": {"dtype": "<i8", "shape": []},
            "structured": {
                "dtype": "<f8",
                "shape": ["draw_count", "county_count"],
            },
            "unstructured": {
                "dtype": "<f8",
                "shape": ["draw_count", "county_count"],
            },
        },
    }

    manifest_dir = tmp_path / "manifest-extra"
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)
    commit_spatial_draw_chunk(
        manifest_dir,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    manifest_path = manifest_dir / "spatial_chunk_manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="ascii"))
    manifest_payload["unexpected"] = "discarded-by-old-reader"
    manifest_path.write_bytes(_canonical_bytes(manifest_payload))
    with pytest.raises(ValueError, match="manifest schema"):
        validate_spatial_chunk_inventory(manifest_dir)

    for mode in ("chain-shape", "epoch-dtype", "draw-dtype"):
        chunk_dir = tmp_path / mode
        record = commit_spatial_draw_chunk(
            chunk_dir,
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
        )
        spatial_path = chunk_dir / record["spatial_path"]
        with np.load(spatial_path, allow_pickle=False) as stored:
            payload = {key: stored[key].copy() for key in stored.files}
        if mode == "chain-shape":
            payload["chain_id"] = np.asarray([1], dtype=np.int64)
        elif mode == "epoch-dtype":
            payload["extension_epoch"] = np.asarray(0, dtype=np.int32)
        else:
            payload["draw_id"] = payload["draw_id"].astype(np.int32)
        np.savez_compressed(spatial_path, **payload)
        record["spatial_sha256"] = _sha256(spatial_path.read_bytes())
        (chunk_dir / "spatial_chunk_manifest.json").write_bytes(
            _canonical_bytes(
                {
                    "schema_id": "sr_v2_spatial_chunk_manifest/v1",
                    "records": [record],
                }
            )
        )
        with pytest.raises(ValueError, match="identity.*shape|identity.*dtype|schema"):
            validate_spatial_chunk_inventory(chunk_dir)


def test_spatial_chunks_reject_fractional_draw_chain_and_epoch_labels(
    tmp_path: Path,
) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)
    fractional_ids = draw_ids.astype(np.float64)
    fractional_ids[-1] += 0.5
    with pytest.raises(ValueError, match="exact integers"):
        commit_spatial_draw_chunk(
            tmp_path / "fractional-draw",
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=fractional_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
        )


def test_spatial_chunks_bind_chain_epoch_count_graph_and_exact_scalar_schema(
    tmp_path: Path, synthetic_graph
) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)

    incomplete = scalar.loc[scalar["parameter"].eq("sigma_county")].copy()
    with pytest.raises(ValueError, match="parameter schema|cardinality"):
        commit_spatial_draw_chunk(
            tmp_path / "incomplete-schema",
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=incomplete,
            structured=structured,
            unstructured=unstructured,
        )

    bad_support = scalar.copy()
    bad_support.loc[bad_support["parameter"].eq("phi_structured"), "value"] = 1.0
    with pytest.raises(ValueError, match="phi_structured|support"):
        commit_spatial_draw_chunk(
            tmp_path / "bad-support",
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=bad_support,
            structured=structured,
            unstructured=unstructured,
        )

    wrong_width = structured[:, :2]
    with pytest.raises(ValueError, match="county"):
        commit_spatial_draw_chunk(
            tmp_path / "wrong-count",
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=wrong_width,
            unstructured=unstructured[:, :2],
        )

    future_scalar = scalar.copy()
    future_scalar["extension_epoch"] = 1
    with pytest.raises(ValueError, match="epoch|draw range"):
        commit_spatial_draw_chunk(
            tmp_path / "future-epoch",
            chain_id=1,
            extension_epoch=1,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=future_scalar,
            structured=structured,
            unstructured=unstructured,
        )

    chain_dir = tmp_path / "chain-bound"
    commit_spatial_draw_chunk(
        chain_dir,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    next_ids, next_scalar, next_structured, next_unstructured = _chunk_payload(
        3, start=251
    )
    next_scalar["chain_id"] = 2
    with pytest.raises(ValueError, match="chain|identity"):
        commit_spatial_draw_chunk(
            chain_dir,
            chain_id=2,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=2,
            draw_ids=next_ids,
            scalar_draws=next_scalar,
            structured=next_structured,
            unstructured=next_unstructured,
        )

    ids6, scalar6, _, _ = _chunk_payload(len(synthetic_graph.counties))
    a = ids6.astype(np.float64) / 10_000.0
    b = ids6.astype(np.float64) / 20_000.0
    valid6 = np.column_stack((a, -2.0 * a, a, b, -b, np.zeros_like(a)))
    noncentered6 = valid6.copy()
    noncentered6[0, 0] += 0.1
    with pytest.raises(ValueError, match="center"):
        commit_spatial_draw_chunk(
            tmp_path / "noncentered",
            chain_id=1,
            extension_epoch=0,
            graph=synthetic_graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=ids6,
            scalar_draws=scalar6,
            structured=noncentered6,
            unstructured=np.zeros_like(valid6),
        )
    singleton6 = valid6.copy()
    singleton6[0, -1] = 0.1
    with pytest.raises(ValueError, match="singleton"):
        commit_spatial_draw_chunk(
            tmp_path / "singleton",
            chain_id=1,
            extension_epoch=0,
            graph=synthetic_graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=ids6,
            scalar_draws=scalar6,
            structured=singleton6,
            unstructured=np.zeros_like(valid6),
        )
    bad_scalar = scalar.copy()
    bad_scalar["chain_id"] = bad_scalar["chain_id"].astype(np.float64)
    bad_scalar.loc[0, "chain_id"] = 1.5
    with pytest.raises(ValueError, match="exact integers"):
        commit_spatial_draw_chunk(
            tmp_path / "fractional-chain",
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=bad_scalar,
            structured=structured,
            unstructured=unstructured,
        )


def test_checkpoint_binds_exact_committed_pair_inventory_and_pending_tail(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph, frame=frame, design=design
    )
    parameter_schema = tuple(identity["target"]["parameter_schema"])
    chunk_dir = tmp_path / "chunks"
    draw_ids, scalar, structured, unstructured = _chunk_payload(
        3,
        parameter_schema=parameter_schema,
    )
    record = commit_spatial_draw_chunk(
        chunk_dir,
        chain_id=1,
        extension_epoch=0,
        graph=design.spatial_graph,
        parameter_schema=identity["target"]["parameter_schema"],
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    pending_scalar = _spatial_scalar_frame(
        theta,
        design,
        np.asarray([251], dtype=np.int64),
    )
    checkpoint = tmp_path / "checkpoint.json"
    intercept_mean = crude_intercept_prior(frame)
    iteration = 52_530
    adaptation = _mala_state_at(iteration)
    accepted, proposed = _checkpoint_counters(
        iteration,
        adaptation=adaptation,
    )
    save_spatial_checkpoint(
        checkpoint,
        identity=identity,
        extension_epoch=0,
        job_attempt=1,
        y=y,
        theta=theta,
        rng=np.random.default_rng(74291),
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        iteration=iteration,
        saved_draws=251,
        current_target=log_posterior_theta(
            y, theta, design, intercept_mean=intercept_mean
        ),
        accepted=accepted,
        proposed=proposed,
        committed_chunks=[record],
        pending_scalar=pending_scalar,
        pending_structured=theta.spatial_structured[None, :],
        pending_unstructured=theta.spatial_unstructured[None, :],
        adaptation_state=adaptation.to_dict(),
        next_draw_id=252,
        output_positions={
            "scalar_rows": 251 * len(parameter_schema),
            "spatial_draws": 251,
        },
        chunk_dir=chunk_dir,
    )
    loaded = load_spatial_checkpoint(
        checkpoint,
        expected_identity=identity,
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        chunk_dir=chunk_dir,
    )
    assert loaded["committed_chunks"] == [record]
    with pytest.raises(ValueError, match="chunk directory|chunk_dir|committed"):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=identity,
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
        )
    (chunk_dir / record["spatial_path"]).unlink()
    with pytest.raises(ValueError, match="missing|inventory"):
        load_spatial_checkpoint(
            checkpoint,
            expected_identity=identity,
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
            chunk_dir=chunk_dir,
        )


def test_spatial_chunk_epoch_zero_to_one_boundary_is_exact(tmp_path: Path) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    chunk_dir = tmp_path / "boundary-chunks"
    records = []
    for chunk_id in range(1, 19):
        start = 1 + (chunk_id - 1) * 250
        draw_ids, scalar, structured, unstructured = _chunk_payload(3, start=start)
        records.append(
            commit_spatial_draw_chunk(
                chunk_dir,
                chain_id=1,
                extension_epoch=0,
                graph=graph,
                parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
                chunk_id=chunk_id,
                draw_ids=draw_ids,
                scalar_draws=scalar,
                structured=structured,
                unstructured=unstructured,
            )
        )
    assert records[-1]["draw_end"] == 4_500

    draw_ids, scalar, structured, unstructured = _chunk_payload(3, start=4_501)
    scalar["extension_epoch"] = 1
    with pytest.raises(ValueError, match="epoch|draw range"):
        commit_spatial_draw_chunk(
            chunk_dir,
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=19,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
        )
    record = commit_spatial_draw_chunk(
        chunk_dir,
        chain_id=1,
        extension_epoch=1,
        graph=graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        chunk_id=19,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    assert record["draw_start"] == 4_501
    assert record["extension_epoch"] == 1
    validate_spatial_chunk_inventory(
        chunk_dir,
        expected_records=[*records, record],
        expected_next_draw_id=4_751,
        expected_chain_id=1,
        maximum_extension_epoch=1,
        expected_graph=graph,
        expected_parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
    )


def test_checkpoint_rejects_cross_chain_chunks_and_incomplete_pending_scalar_schema(
    tmp_path: Path,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    identity = _spatial_identity(graph, frame=frame, design=design)
    parameter_schema = tuple(identity["target"]["parameter_schema"])
    intercept_mean = crude_intercept_prior(frame)
    draw_ids, scalar, structured, unstructured = _chunk_payload(
        3,
        parameter_schema=parameter_schema,
    )
    scalar["chain_id"] = 2
    chunk_dir = tmp_path / "chain-two-chunks"
    record = commit_spatial_draw_chunk(
        chunk_dir,
        chain_id=2,
        extension_epoch=0,
        graph=graph,
        parameter_schema=identity["target"]["parameter_schema"],
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    iteration = 52_500
    adaptation = _mala_state_at(iteration)
    accepted, proposed = _checkpoint_counters(
        iteration,
        adaptation=adaptation,
    )
    with pytest.raises(ValueError, match="chain|identity"):
        save_spatial_checkpoint(
            tmp_path / "cross-chain.json",
            identity=identity,
            extension_epoch=0,
            job_attempt=1,
            y=y,
            theta=theta,
            rng=np.random.default_rng(74291),
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
            iteration=iteration,
            saved_draws=250,
            current_target=log_posterior_theta(
                y, theta, design, intercept_mean=intercept_mean
            ),
            accepted=accepted,
            proposed=proposed,
            committed_chunks=[record],
            pending_scalar=pd.DataFrame(),
            pending_structured=np.empty((0, 3)),
            pending_unstructured=np.empty((0, 3)),
            adaptation_state=adaptation.to_dict(),
            next_draw_id=251,
            output_positions={
                "scalar_rows": 250 * len(parameter_schema),
                "spatial_draws": 250,
            },
            chunk_dir=chunk_dir,
        )

    incomplete = pd.DataFrame(
        [
            {
                "chain_id": 1,
                "draw_id": 1,
                "extension_epoch": 0,
                "parameter": "sigma_county",
                "value": 0.7,
            }
        ]
    )
    iteration = 45_030
    adaptation = _mala_state_at(iteration)
    accepted, proposed = _checkpoint_counters(
        iteration,
        adaptation=adaptation,
    )
    with pytest.raises(ValueError, match="parameter schema|cardinality"):
        save_spatial_checkpoint(
            tmp_path / "incomplete-pending.json",
            identity=identity,
            extension_epoch=0,
            job_attempt=1,
            y=y,
            theta=theta,
            rng=np.random.default_rng(74291),
            frame=frame,
            design=design,
            intercept_mean=intercept_mean,
            iteration=iteration,
            saved_draws=1,
            current_target=log_posterior_theta(
                y, theta, design, intercept_mean=intercept_mean
            ),
            accepted=accepted,
            proposed=proposed,
            committed_chunks=[],
            pending_scalar=incomplete,
            pending_structured=theta.spatial_structured[None, :],
            pending_unstructured=theta.spatial_unstructured[None, :],
            adaptation_state=adaptation.to_dict(),
            next_draw_id=2,
            output_positions={
                "scalar_rows": len(parameter_schema),
                "spatial_draws": 1,
            },
        )


def test_spatial_diagnostics_consumes_merged_schema_and_enforces_grid_and_constraints(
    tmp_path: Path, synthetic_graph
) -> None:
    graph = synthetic_graph
    scalar_frames: list[pd.DataFrame] = []
    spatial_frames: dict[str, list[np.ndarray]] = {
        "chain_id": [],
        "draw_id": [],
        "extension_epoch": [],
        "structured": [],
        "unstructured": [],
    }
    draw_ids = np.arange(1, 251, dtype=np.int64)
    for chain_id in (1, 2, 3, 4):
        _, scalar, _, _ = _chunk_payload(len(graph.counties))
        scalar["chain_id"] = chain_id
        scalar["value"] += (chain_id - 1) * 1e-4
        a = draw_ids.astype(np.float64) / 10_000.0 + chain_id * 1e-3
        b = draw_ids.astype(np.float64) / 20_000.0 - chain_id * 1e-3
        structured = np.column_stack((a, -2.0 * a, a, b, -b, np.zeros_like(a)))
        unstructured = np.column_stack(
            [
                np.sin(draw_ids / (7.0 + county_index) + chain_id)
                for county_index in range(len(graph.counties))
            ]
        ).astype(np.float64)
        chunk_dir = tmp_path / f"chain-{chain_id}" / "chunks"
        record = commit_spatial_draw_chunk(
            chunk_dir,
            chain_id=chain_id,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
        )
        scalar_output = tmp_path / f"chain-{chain_id}" / "scalar.parquet"
        spatial_output = tmp_path / f"chain-{chain_id}" / "spatial.npz"
        merge_spatial_draw_chunks(
            chunk_dir,
            records=[record],
            scalar_output=scalar_output,
            spatial_output=spatial_output,
            graph=graph,
        )
        scalar_frames.append(pd.read_parquet(scalar_output))
        with np.load(spatial_output, allow_pickle=False) as stored:
            for key in spatial_frames:
                spatial_frames[key].append(stored[key].copy())
    scalar_draws = pd.concat(scalar_frames, ignore_index=True)
    spatial_draws = {
        key: np.concatenate(parts, axis=0) for key, parts in spatial_frames.items()
    }
    diagnostics = spatial_diagnostics_table(
        scalar_draws,
        spatial_draws,
        graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
    )
    assert len(diagnostics) == 2 + 5 + 6 + 6
    assert {
        "parameter",
        "r_hat",
        "ess_bulk",
        "ess_tail",
        "arviz_version",
        "constraint_failures",
    }.issubset(diagnostics.columns)
    assert diagnostics["constraint_failures"].eq(0).all()
    assert diagnostics["arviz_version"].nunique() == 1
    assert not diagnostics["parameter"].eq("spatial_structured[03001]").any()

    fractional = {key: value.copy() for key, value in spatial_draws.items()}
    fractional["chain_id"] = fractional["chain_id"].astype(np.float64)
    fractional["chain_id"][0] = 1.5
    with pytest.raises(ValueError, match="exact integer"):
        spatial_diagnostics_table(
            scalar_draws,
            fractional,
            graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        )

    noncentered = {key: value.copy() for key, value in spatial_draws.items()}
    noncentered["structured"][0, 0] += 0.5
    with pytest.raises(ValueError, match="center|structured"):
        spatial_diagnostics_table(
            scalar_draws,
            noncentered,
            graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        )

    incomplete_scalar = scalar_draws.drop(
        scalar_draws.index[
            scalar_draws["parameter"].eq("phi_structured")
        ][-1]
    )
    with pytest.raises(ValueError, match="grid|missing|unequal"):
        spatial_diagnostics_table(
            incomplete_scalar,
            spatial_draws,
            graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        )

    replaced_scalar = scalar_draws.copy()
    replaced_spatial = {key: value.copy() for key, value in spatial_draws.items()}
    replaced_scalar.loc[replaced_scalar["draw_id"].eq(250), "draw_id"] = 251
    replaced_spatial["draw_id"][replaced_spatial["draw_id"] == 250] = 251
    with pytest.raises(ValueError, match="prefix|draw grid|1..N"):
        spatial_diagnostics_table(
            replaced_scalar,
            replaced_spatial,
            graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        )

    wrong_schema = scalar_draws.copy()
    wrong_schema.loc[
        wrong_schema["parameter"].eq("sigma_county"), "parameter"
    ] = "arbitrary"
    with pytest.raises(ValueError, match="parameter schema"):
        spatial_diagnostics_table(
            wrong_schema,
            spatial_draws,
            graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        )


@pytest.mark.parametrize(
    "boundary",
    [
        "after_scalar_temp",
        "after_spatial_temp",
        "after_scalar_rename",
        "after_spatial_rename",
        "after_manifest_rename",
    ],
)
def test_paired_chunk_crash_windows_never_acknowledge_half_a_draw_pair(
    tmp_path: Path, boundary: str
) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    chunk_dir = tmp_path / boundary
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)

    def crash(observed: str) -> None:
        if observed == boundary:
            raise RuntimeError(f"crash at {boundary}")

    with pytest.raises(RuntimeError, match="crash"):
        commit_spatial_draw_chunk(
            chunk_dir,
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
            crash_hook=crash,
        )
    if boundary == "after_manifest_rename":
        records = validate_spatial_chunk_inventory(
            chunk_dir, expected_next_draw_id=251
        )
        assert len(records) == 1
    else:
        with pytest.raises(ValueError, match="manifest|inventory|orphan|temporary"):
            validate_spatial_chunk_inventory(chunk_dir)


def test_checkpoint_sidecar_crash_windows_are_fail_closed(tmp_path: Path) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    identity = _spatial_identity(
        design.spatial_graph,
        frame=frame,
        design=design,
    )
    intercept_mean = crude_intercept_prior(frame)
    base = {
        "identity": identity,
        "extension_epoch": 0,
        "job_attempt": 1,
        "y": y,
        "theta": theta,
        "rng": np.random.default_rng(74291),
        "frame": frame,
        "design": design,
        "intercept_mean": intercept_mean,
        "iteration": 0,
        "saved_draws": 0,
        "current_target": log_posterior_theta(
            y,
            theta,
            design,
            intercept_mean=intercept_mean,
        ),
        "accepted": _checkpoint_counters(0)[0],
        "proposed": _checkpoint_counters(0)[1],
        "committed_chunks": [],
        "pending_scalar": pd.DataFrame(),
        "pending_structured": np.empty((0, 3), dtype=np.float64),
        "pending_unstructured": np.empty((0, 3), dtype=np.float64),
        "adaptation_state": SpatialMALAState().to_dict(),
        "next_draw_id": 1,
        "output_positions": {"scalar_rows": 0, "spatial_draws": 0},
    }
    for boundary in ("after_checkpoint_publish", "after_sidecar_publish"):
        checkpoint = tmp_path / f"{boundary}.json"

        def crash(observed: str) -> None:
            if observed == boundary:
                raise RuntimeError(f"crash at {boundary}")

        with pytest.raises(RuntimeError, match="crash"):
            save_spatial_checkpoint(
                checkpoint,
                **base,
                crash_hook=crash,
            )
        assert checkpoint.is_file()
        sidecar = checkpoint.with_name(checkpoint.name + ".sha256")
        if boundary == "after_checkpoint_publish":
            assert not sidecar.exists()
            with pytest.raises(ValueError, match="sidecar"):
                load_spatial_checkpoint(
                    checkpoint,
                    expected_identity=identity,
                    frame=frame,
                    design=design,
                    intercept_mean=intercept_mean,
                    chunk_dir=tmp_path / "chunks",
                )
        else:
            assert sidecar.is_file()
            loaded = load_spatial_checkpoint(
                checkpoint,
                expected_identity=identity,
                frame=frame,
                design=design,
                intercept_mean=intercept_mean,
                chunk_dir=tmp_path / "chunks",
            )
            assert loaded["iteration"] == 0


def test_checkpoint_chunk_and_merge_publication_never_overwrite_raced_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame, y, design, theta = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    identity = _spatial_identity(graph, frame=frame, design=design)
    real_link = os.link

    def race_once(expected: Path):
        raced = {"done": False}

        def raced_link(source, destination, *args, **kwargs):
            destination_path = Path(destination)
            if destination_path == expected and not raced["done"]:
                destination_path.write_bytes(b"raced-writer")
                raced["done"] = True
            return real_link(source, destination, *args, **kwargs)

        monkeypatch.setattr(spatial_module.os, "link", raced_link)
        return raced

    checkpoint = tmp_path / "raced-checkpoint.json"
    checkpoint_race = race_once(checkpoint)
    with pytest.raises(FileExistsError, match="exists|publish|race"):
        _save_empty_spatial_checkpoint(
            checkpoint,
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
        )
    assert checkpoint_race["done"]
    assert checkpoint.read_bytes() == b"raced-writer"

    chunk_dir = tmp_path / "raced-chunk"
    scalar_destination = chunk_dir / "scalar_chunk_000001.parquet"
    chunk_race = race_once(scalar_destination)
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)
    with pytest.raises(FileExistsError, match="exists|publish|race"):
        commit_spatial_draw_chunk(
            chunk_dir,
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
        )
    assert chunk_race["done"]
    assert scalar_destination.read_bytes() == b"raced-writer"

    source_dir = tmp_path / "merge-source"
    record = commit_spatial_draw_chunk(
        source_dir,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    merged_scalar = tmp_path / "raced-merged.parquet"
    merged_spatial = tmp_path / "raced-merged.npz"
    merge_race = race_once(merged_scalar)
    with pytest.raises(FileExistsError, match="exists|publish|race"):
        merge_spatial_draw_chunks(
            source_dir,
            records=[record],
            scalar_output=merged_scalar,
            spatial_output=merged_spatial,
            graph=graph,
        )
    assert merge_race["done"]
    assert merged_scalar.read_bytes() == b"raced-writer"
    assert not merged_spatial.exists()


def test_spatial_checkpoint_and_chunk_paths_reject_symlink_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_target = tmp_path / "probe-target"
    probe_target.mkdir()
    probe_link = tmp_path / "probe-link"
    try:
        os.symlink(probe_target, probe_link, target_is_directory=True)
    except OSError:
        fake_checkpoint = tmp_path / "fake-checkpoint-link.json"
        fake_chunk_dir = tmp_path / "fake-chunk-link"
        real_is_symlink = Path.is_symlink

        def simulated_is_symlink(path: Path) -> bool:
            return path in {fake_checkpoint, fake_chunk_dir} or real_is_symlink(path)

        monkeypatch.setattr(Path, "is_symlink", simulated_is_symlink)
        with pytest.raises(ValueError, match="symbolic"):
            load_spatial_checkpoint(fake_checkpoint, expected_identity={})
        with pytest.raises(ValueError, match="symbolic"):
            validate_spatial_chunk_inventory(fake_chunk_dir)
        return
    probe_link.unlink()

    frame, y, design, theta = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    identity = _spatial_identity(graph, frame=frame, design=design)

    dangling_checkpoint = tmp_path / "dangling-checkpoint.json"
    os.symlink(tmp_path / "missing-checkpoint.json", dangling_checkpoint)
    with pytest.raises((FileExistsError, ValueError), match="exists|symbolic"):
        _save_empty_spatial_checkpoint(
            dangling_checkpoint,
            frame=frame,
            y=y,
            design=design,
            theta=theta,
            identity=identity,
        )

    real_checkpoint = tmp_path / "real-checkpoint.json"
    _save_empty_spatial_checkpoint(
        real_checkpoint,
        frame=frame,
        y=y,
        design=design,
        theta=theta,
        identity=identity,
    )
    alias_checkpoint = tmp_path / "alias-checkpoint.json"
    os.symlink(real_checkpoint, alias_checkpoint)
    os.symlink(
        real_checkpoint.with_name(real_checkpoint.name + ".sha256"),
        alias_checkpoint.with_name(alias_checkpoint.name + ".sha256"),
    )
    with pytest.raises(ValueError, match="symbolic"):
        load_spatial_checkpoint(
            alias_checkpoint,
            expected_identity=identity,
            frame=frame,
            design=design,
            intercept_mean=crude_intercept_prior(frame),
            chunk_dir=tmp_path / "chunks",
        )

    real_chunk_dir = tmp_path / "real-chunks"
    linked_chunk_dir = tmp_path / "linked-chunks"
    os.symlink(real_chunk_dir, linked_chunk_dir, target_is_directory=True)
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)
    with pytest.raises(ValueError, match="symbolic"):
        commit_spatial_draw_chunk(
            linked_chunk_dir,
            chain_id=1,
            extension_epoch=0,
            graph=graph,
            parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
            chunk_id=1,
            draw_ids=draw_ids,
            scalar_draws=scalar,
            structured=structured,
            unstructured=unstructured,
        )


@pytest.mark.parametrize("boundary", ["after_scalar_publish", "after_spatial_publish"])
def test_merge_crash_windows_and_identical_destinations_fail_closed(
    tmp_path: Path,
    boundary: str,
) -> None:
    _, _, design, _ = _spatial_model_case(tmp_path)
    graph = design.spatial_graph
    source_dir = tmp_path / "source"
    draw_ids, scalar, structured, unstructured = _chunk_payload(3)
    record = commit_spatial_draw_chunk(
        source_dir,
        chain_id=1,
        extension_epoch=0,
        graph=graph,
        parameter_schema=TEST_SCALAR_PARAMETER_SCHEMA,
        chunk_id=1,
        draw_ids=draw_ids,
        scalar_draws=scalar,
        structured=structured,
        unstructured=unstructured,
    )
    same = tmp_path / "same-output"
    with pytest.raises(ValueError, match="distinct|identical"):
        merge_spatial_draw_chunks(
            source_dir,
            records=[record],
            scalar_output=same,
            spatial_output=same,
            graph=graph,
        )

    scalar_output = tmp_path / f"{boundary}.parquet"
    spatial_output = tmp_path / f"{boundary}.npz"

    def crash(observed: str) -> None:
        if observed == boundary:
            raise RuntimeError(f"crash at {boundary}")

    with pytest.raises(RuntimeError, match="crash"):
        merge_spatial_draw_chunks(
            source_dir,
            records=[record],
            scalar_output=scalar_output,
            spatial_output=spatial_output,
            graph=graph,
            crash_hook=crash,
        )
    assert scalar_output.is_file()
    assert spatial_output.exists() is (boundary == "after_spatial_publish")
