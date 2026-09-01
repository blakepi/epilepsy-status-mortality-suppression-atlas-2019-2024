"""Canonical county graph and scaled BYM2 prior primitives.

The graph contract is deliberately independent of model-frame row order.  Its
county and edge hashes are over the exact line-oriented formats frozen by the
SR-v2 spatial sensitivity plan, while the contract hash is over canonical JSON.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, diags
from scipy.sparse.csgraph import connected_components
from scipy.special import expit


_DIRECT_SCALE_MAX_COMPONENT_SIZE = 512


@dataclass(frozen=True)
class BYM2Prior:
    sigma_county_halfnormal_sd: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.sigma_county_halfnormal_sd):
            raise ValueError("sigma_county_halfnormal_sd must be finite.")
        if self.sigma_county_halfnormal_sd <= 0:
            raise ValueError("sigma_county_halfnormal_sd must be positive.")


@dataclass(frozen=True)
class BYM2Graph:
    counties: tuple[str, ...]
    row_county_index: np.ndarray
    adjacency: csr_matrix
    scaled_precision: csr_matrix
    component_id: np.ndarray
    components: tuple[np.ndarray, ...]
    component_scale: np.ndarray
    singleton_mask: np.ndarray
    contract_sha256: str


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _strict_integer(value: Any, *, label: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise ValueError(f"{label} must be an exact integer.")
    return int(value)


def _parameter_schema(value: Any, *, label: str = "parameter_schema") -> list[str]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{label} must be a nonempty ordered list.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item.strip() != item:
            raise ValueError(f"{label} entries must be nonempty canonical strings.")
        result.append(item)
    if len(set(result)) != len(result):
        raise ValueError(f"{label} entries must be unique.")
    return result


def _array_digest_schema(
    values: Any,
    *,
    dtype: np.dtype[Any],
) -> dict[str, Any]:
    expected_dtype = np.dtype(dtype)
    observed = np.asarray(values)
    if observed.dtype != expected_dtype:
        raise ValueError(
            f"Runtime Design array dtype {observed.dtype.str} is not {expected_dtype.str}."
        )
    array = np.ascontiguousarray(observed)
    return {
        "dtype": expected_dtype.str,
        "shape": list(array.shape),
        "sha256": _sha256(array.tobytes(order="C")),
    }


def spatial_design_schema(design: Any) -> dict[str, Any]:
    """Return the exact runtime Design contract bound by target fingerprints."""

    graph = getattr(design, "spatial_graph", None)
    if graph is None:
        raise ValueError("A spatial runtime Design schema requires a graph.")
    columns = _parameter_schema(list(design.columns), label="design columns")
    states = _parameter_schema(list(design.states), label="design states")
    years = _parameter_schema(list(design.years), label="design years")
    return {
        "schema_id": "sr_v2_spatial_design/v1",
        "columns": columns,
        "states": states,
        "years": years,
        "x": _array_digest_schema(design.x, dtype=np.dtype("<f8")),
        "offset": _array_digest_schema(design.offset, dtype=np.dtype("<f8")),
        "state_index": _array_digest_schema(
            design.state_index, dtype=np.dtype("<i8")
        ),
        "year_index": _array_digest_schema(
            design.year_index, dtype=np.dtype("<i8")
        ),
        "row_county_index": _array_digest_schema(
            graph.row_county_index, dtype=np.dtype("<i8")
        ),
        "graph_contract_sha256": _require_sha256(
            graph.contract_sha256,
            label="graph_contract_sha256",
        ),
    }


def spatial_parameter_schema(design: Any) -> list[str]:
    """Return the exact scalar draw universe implied by a spatial Design."""

    if getattr(design, "spatial_graph", None) is None:
        raise ValueError("A spatial parameter schema requires a spatial Design.")
    result = [
        *list(design.columns),
        *(f"state_effect[{state}]" for state in design.states),
        *(f"year_effect[{year}]" for year in design.years),
        "sigma_state",
        "sigma_year",
    ]
    if design.likelihood_family == "negative_binomial_2":
        result.append("kappa")
    result.extend(["sigma_county", "phi_structured"])
    return _parameter_schema(result)


def spatial_prior_schema(prior: Any | None = None) -> dict[str, Any]:
    """Return the exact base and BYM2 prior contract used by the full target."""

    from .model import active_prior_specification

    specification = prior or active_prior_specification()
    base_prior = specification.to_dict()
    return {
        "schema_id": "sr_v2_spatial_prior/v1",
        "base_prior": base_prior,
        "sigma_county": {
            "distribution": "HalfNormal",
            "sd": 1.0,
            "sampled_as": "log_sigma_county",
            "transformed_jacobian": "log_sigma_county",
        },
        "phi_structured": {
            "distribution": "Beta",
            "alpha": 1.0,
            "beta": 1.0,
            "sampled_as": "logit_phi_structured",
            "transformed_jacobian": "log_phi_plus_log_one_minus_phi",
        },
    }


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
            raise ValueError("Model frame semantic hash rejects infinite values.")
        return f"float:{numeric.hex()}".encode("ascii")
    if isinstance(value, pd.Timestamp):
        return f"timestamp:{value.isoformat()}".encode("utf-8")
    if isinstance(value, str):
        return b"str:" + value.encode("utf-8")
    raise ValueError(
        f"Model frame semantic hash does not support {type(value).__name__}."
    )


def spatial_model_frame_sha256(frame: pd.DataFrame) -> str:
    """Hash exact frame schema, row order, and scalar values without coercion."""

    if not isinstance(frame, pd.DataFrame):
        raise ValueError("Spatial model frame must be a pandas DataFrame.")
    digest = hashlib.sha256()

    def add(payload: bytes) -> None:
        digest.update(len(payload).to_bytes(8, "little", signed=False))
        digest.update(payload)

    add(b"sr_v2_spatial_model_frame_semantic/v1")
    add(str(len(frame)).encode("ascii"))
    for key in sorted(frame.attrs):
        if not isinstance(key, str):
            raise ValueError("Spatial model frame attribute names must be strings.")
        add(b"attr:" + key.encode("utf-8"))
        add(_frame_scalar_token(frame.attrs[key]))
    for column in frame.columns:
        if not isinstance(column, str):
            raise ValueError("Spatial model frame columns must be strings.")
        add(column.encode("utf-8"))
        add(str(frame[column].dtype).encode("ascii"))
        for value in frame[column].array:
            add(_frame_scalar_token(value))
    return digest.hexdigest()


def frozen_graph_contract_from_execution(
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    """Translate the immutable operational YAML graph schema exactly once.

    The human-facing YAML uses count names such as ``nodes`` and places the
    component table under ``non_singleton_components``.  The graph builder has
    a deliberately smaller internal certificate schema.  This adapter is the
    sole documented bridge, preventing preparation/runner code from growing
    ad-hoc translations that silently omit fields.
    """

    try:
        certificate = execution["graph_certificate"]
        if not isinstance(certificate, Mapping):
            raise TypeError("graph_certificate is not a mapping")
        translated = {
            "node_count": _strict_integer(certificate["nodes"], label="nodes"),
            "edge_count": _strict_integer(
                certificate["undirected_edges"], label="undirected_edges"
            ),
            "component_count": _strict_integer(
                certificate["components"], label="components"
            ),
            "nonisolated_count": _strict_integer(
                certificate["nonisolated_nodes"], label="nonisolated_nodes"
            ),
            "county_order_sha256": str(certificate["county_order_sha256"]),
            "edge_list_sha256": str(certificate["edge_list_sha256"]),
            "singletons": [str(value) for value in certificate["singletons"]],
            "components": [
                {
                    "minimum_fips": str(row["minimum_fips"]),
                    "size": _strict_integer(row["size"], label="component size"),
                    "scale_hex": str(row["scale_hex"]),
                }
                for row in certificate["non_singleton_components"]
            ],
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Operational graph_certificate cannot be translated to the frozen builder contract."
        ) from error
    for field in ("county_order_sha256", "edge_list_sha256"):
        value = translated[field]
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"Operational graph certificate has invalid {field}.")
    return translated


def _normalized_fips(values: pd.Series, *, label: str) -> pd.Series:
    if values.isna().any():
        raise ValueError(f"{label} contains missing county FIPS values.")
    normalized = values.astype(str).str.strip().str.zfill(5)
    invalid = ~normalized.str.fullmatch(r"\d{5}", na=False)
    if invalid.any():
        examples = sorted(normalized[invalid].unique())[:5]
        raise ValueError(f"{label} contains invalid county FIPS values: {examples}")
    return normalized


def _frame_counties(frame: pd.DataFrame) -> tuple[tuple[str, ...], np.ndarray]:
    if "county_fips" not in frame.columns:
        raise ValueError("Model frame is missing county_fips.")
    normalized = _normalized_fips(frame["county_fips"], label="Model frame")
    if "year" in frame.columns:
        year = frame["year"]
        if pd.DataFrame({"county_fips": normalized, "year": year}).duplicated().any():
            raise ValueError("Model frame contains duplicate county-year rows.")
    elif normalized.duplicated().any():
        raise ValueError("Model frame contains duplicate county rows.")
    counties = tuple(sorted(normalized.unique()))
    index = {county: position for position, county in enumerate(counties)}
    row_county_index = normalized.map(index).to_numpy(dtype=np.int64)
    return counties, row_county_index


def _read_adjacency_edges(
    adjacency_path: Path,
    counties: tuple[str, ...],
) -> tuple[list[tuple[str, str]], str]:
    payload = adjacency_path.read_bytes()
    raw_sha256 = _sha256(payload)
    adjacency = pd.read_csv(adjacency_path, sep="|", dtype=str)
    required = {"County GEOID", "Neighbor GEOID"}
    missing = required - set(adjacency.columns)
    if missing:
        raise ValueError(f"Adjacency file is missing columns: {sorted(missing)}")
    left = _normalized_fips(adjacency["County GEOID"], label="Adjacency source")
    right = _normalized_fips(adjacency["Neighbor GEOID"], label="Adjacency source")
    county_set = set(counties)
    edges = sorted(
        {
            (min(a, b), max(a, b))
            for a, b in zip(left, right, strict=True)
            if a in county_set and b in county_set and a != b
        }
    )
    return edges, raw_sha256


def _graph_components(
    adjacency: csr_matrix,
    counties: tuple[str, ...],
) -> tuple[tuple[np.ndarray, ...], np.ndarray]:
    count, raw_labels = connected_components(
        adjacency, directed=False, return_labels=True
    )
    unordered = [np.flatnonzero(raw_labels == label) for label in range(count)]
    components = tuple(
        sorted(
            (np.asarray(component, dtype=np.int64) for component in unordered),
            key=lambda component: counties[int(component[0])],
        )
    )
    component_id = np.empty(len(counties), dtype=np.int64)
    for identifier, component in enumerate(components):
        component_id[component] = identifier
    return components, component_id


def _laplacian_scale(precision: np.ndarray) -> float:
    marginal_variance = np.diag(np.linalg.pinv(precision, hermitian=True))
    if (
        not np.isfinite(marginal_variance).all()
        or np.any(marginal_variance <= 0.0)
    ):
        raise ValueError("ICAR pseudoinverse has invalid marginal variances.")
    scale = float(np.exp(np.mean(np.log(marginal_variance))))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("ICAR component scale must be finite and positive.")
    return scale


def _frozen_scale_by_minimum_fips(
    frozen_contract: Mapping[str, Any] | None,
) -> dict[str, float]:
    if frozen_contract is None:
        return {}
    result: dict[str, float] = {}
    for row in frozen_contract.get("components", []):
        try:
            result[str(row["minimum_fips"])] = float.fromhex(str(row["scale_hex"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Frozen component scale certificate is malformed.") from error
    return result


def _component_scales(
    precision: csr_matrix,
    components: tuple[np.ndarray, ...],
    counties: tuple[str, ...],
    frozen_contract: Mapping[str, Any] | None,
) -> np.ndarray:
    certified = _frozen_scale_by_minimum_fips(frozen_contract)
    scales = np.zeros(len(components), dtype=np.float64)
    for identifier, component in enumerate(components):
        if len(component) == 1:
            continue
        minimum_fips = counties[int(component[0])]
        certified_scale = certified.get(minimum_fips)
        if len(component) > _DIRECT_SCALE_MAX_COMPONENT_SIZE and certified_scale is not None:
            # The large frozen component is cryptographically fixed by both the
            # county-order and edge-list certificates validated below.  Its
            # independently computed scale is frozen as a hexadecimal float so
            # routine graph construction does not repeat a cubic decomposition.
            scales[identifier] = certified_scale
            continue
        dense_precision = precision[np.ix_(component, component)].toarray()
        computed = _laplacian_scale(dense_precision)
        if certified_scale is not None:
            if not np.isclose(computed, certified_scale, rtol=5e-13, atol=1e-15):
                raise ValueError(
                    f"Frozen component scale mismatch for {minimum_fips}: "
                    f"computed={computed.hex()} expected={certified_scale.hex()}"
                )
            scales[identifier] = certified_scale
        else:
            scales[identifier] = computed
    return scales


def _validate_frozen_contract(
    frozen: Mapping[str, Any],
    *,
    counties: tuple[str, ...],
    edges: list[tuple[str, str]],
    components: tuple[np.ndarray, ...],
    component_scale: np.ndarray,
    singleton_mask: np.ndarray,
    county_order_sha256: str,
    edge_list_sha256: str,
) -> None:
    actual_counts = {
        "node_count": len(counties),
        "edge_count": len(edges),
        "component_count": len(components),
        "nonisolated_count": int(len(counties) - singleton_mask.sum()),
    }
    for field, actual in actual_counts.items():
        if int(frozen.get(field, -1)) != actual:
            raise ValueError(
                f"Frozen graph {field} mismatch: actual={actual} expected={frozen.get(field)!r}."
            )
    if frozen.get("county_order_sha256") != county_order_sha256:
        raise ValueError("Frozen graph county-order SHA-256 mismatch.")
    if frozen.get("edge_list_sha256") != edge_list_sha256:
        raise ValueError("Frozen graph edge-list SHA-256 mismatch.")

    actual_singletons = [
        counties[index] for index in np.flatnonzero(singleton_mask)
    ]
    if list(frozen.get("singletons", [])) != actual_singletons:
        raise ValueError(
            "Frozen graph singleton county mismatch: "
            f"actual={actual_singletons} expected={frozen.get('singletons')!r}."
        )

    actual_non_singletons = [
        {
            "minimum_fips": counties[int(component[0])],
            "size": len(component),
            "scale_hex": float(component_scale[identifier]).hex(),
        }
        for identifier, component in enumerate(components)
        if len(component) > 1
    ]
    expected_non_singletons = list(frozen.get("components", []))
    if actual_non_singletons != expected_non_singletons:
        raise ValueError(
            "Frozen graph component certificate mismatch: "
            f"actual={actual_non_singletons} expected={expected_non_singletons}."
        )


def _validate_frozen_structure(
    frozen: Mapping[str, Any],
    *,
    counties: tuple[str, ...],
    edges: list[tuple[str, str]],
    components: tuple[np.ndarray, ...],
    singleton_mask: np.ndarray,
    county_order_sha256: str,
    edge_list_sha256: str,
) -> None:
    actual_counts = {
        "node_count": len(counties),
        "edge_count": len(edges),
        "component_count": len(components),
        "nonisolated_count": int(len(counties) - singleton_mask.sum()),
    }
    for field, actual in actual_counts.items():
        if int(frozen.get(field, -1)) != actual:
            raise ValueError(
                f"Frozen graph county/edge structure {field} mismatch: "
                f"actual={actual} expected={frozen.get(field)!r}."
            )
    if frozen.get("county_order_sha256") != county_order_sha256:
        raise ValueError("Frozen graph county-order SHA-256 mismatch.")
    if frozen.get("edge_list_sha256") != edge_list_sha256:
        raise ValueError("Frozen graph edge-list SHA-256 mismatch.")


def build_bym2_graph(
    frame: pd.DataFrame,
    adjacency_path: str | Path,
    *,
    expected_sha256: str,
    frozen_contract: Mapping[str, Any] | None = None,
) -> BYM2Graph:
    """Build the canonical binary graph and component-scaled ICAR precision."""

    counties, row_county_index = _frame_counties(frame)
    edges, raw_sha256 = _read_adjacency_edges(Path(adjacency_path), counties)
    if raw_sha256 != expected_sha256:
        raise ValueError(
            "County adjacency SHA-256 mismatch: "
            f"actual={raw_sha256} expected={expected_sha256}."
        )

    county_index = {county: position for position, county in enumerate(counties)}
    rows: list[int] = []
    columns: list[int] = []
    for left, right in edges:
        left_index = county_index[left]
        right_index = county_index[right]
        rows.extend((left_index, right_index))
        columns.extend((right_index, left_index))
    adjacency = csr_matrix(
        (np.ones(len(rows), dtype=np.float64), (rows, columns)),
        shape=(len(counties), len(counties)),
        dtype=np.float64,
    )
    adjacency.sum_duplicates()
    if adjacency.nnz:
        adjacency.data.fill(1.0)
    components, component_id = _graph_components(adjacency, counties)
    singleton_mask = np.asarray(adjacency.getnnz(axis=1) == 0, dtype=bool)
    county_order_sha256 = _sha256(
        "".join(f"{county}\n" for county in counties).encode("utf-8")
    )
    edge_list_sha256 = _sha256(
        "".join(f"{left}|{right}\n" for left, right in edges).encode("utf-8")
    )
    if frozen_contract is not None:
        _validate_frozen_structure(
            frozen_contract,
            counties=counties,
            edges=edges,
            components=components,
            singleton_mask=singleton_mask,
            county_order_sha256=county_order_sha256,
            edge_list_sha256=edge_list_sha256,
        )
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    precision = (diags(degree, format="csr") - adjacency).tocsr()
    component_scale = _component_scales(
        precision, components, counties, frozen_contract
    )
    scaled_precision = (
        diags(component_scale[component_id], format="csr") @ precision
    ).tocsr()

    if frozen_contract is not None:
        _validate_frozen_contract(
            frozen_contract,
            counties=counties,
            edges=edges,
            components=components,
            component_scale=component_scale,
            singleton_mask=singleton_mask,
            county_order_sha256=county_order_sha256,
            edge_list_sha256=edge_list_sha256,
        )

    contract = {
        "components": [
            {
                "members": [counties[int(index)] for index in component],
                "scale_hex": float(component_scale[identifier]).hex(),
            }
            for identifier, component in enumerate(components)
        ],
        "counties_sha256": county_order_sha256,
        "edges_sha256": edge_list_sha256,
    }
    return BYM2Graph(
        counties=counties,
        row_county_index=row_county_index,
        adjacency=adjacency,
        scaled_precision=scaled_precision,
        component_id=component_id,
        components=components,
        component_scale=component_scale,
        singleton_mask=singleton_mask,
        contract_sha256=_sha256(_canonical_json(contract)),
    )


def _effect_array(values: np.ndarray, graph: BYM2Graph, *, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.shape != (len(graph.counties),):
        raise ValueError(
            f"{label} must have shape ({len(graph.counties)},), got {array.shape}."
        )
    if not np.isfinite(array).all():
        raise ValueError(f"{label} values must all be finite.")
    return array


def componentwise_center(values: np.ndarray, graph: BYM2Graph) -> np.ndarray:
    """Center each connected component and pin singleton effects to zero."""

    centered = _effect_array(values, graph, label="Structured effect").copy()
    for component in graph.components:
        if len(component) == 1:
            centered[component] = 0.0
        else:
            centered[component] -= float(centered[component].mean())
    return centered


def validate_structured_effect(
    values: np.ndarray,
    graph: BYM2Graph,
    *,
    atol: float = 1e-12,
) -> None:
    """Reject values outside the centered ICAR subspace."""

    if not np.isfinite(atol) or atol < 0:
        raise ValueError("atol must be finite and nonnegative.")
    structured = _effect_array(values, graph, label="Structured effect")
    if np.any(structured[graph.singleton_mask] != 0.0):
        raise ValueError("Structured singleton effects must be exactly zero.")
    for component in graph.components:
        if len(component) > 1 and abs(float(structured[component].mean())) > atol:
            raise ValueError("Structured effects must be component-wise centered.")


def _sigma_phi(log_sigma: float, logit_phi: float) -> tuple[float, float]:
    if not np.isfinite(log_sigma) or not np.isfinite(logit_phi):
        raise ValueError("log_sigma and logit_phi must be finite.")
    with np.errstate(over="ignore", under="ignore"):
        sigma = float(np.exp(log_sigma))
    phi = float(expit(logit_phi))
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma_county must be finite and positive.")
    if not np.isfinite(phi) or not 0.0 < phi < 1.0:
        raise ValueError("phi_structured must be finite and strictly between zero and one.")
    return sigma, phi


def combined_county_effect(
    structured: np.ndarray,
    unstructured: np.ndarray,
    log_sigma: float,
    logit_phi: float,
    graph: BYM2Graph,
) -> np.ndarray:
    """Return ``sigma * (sqrt(phi) * u + sqrt(1-phi) * v)``."""

    validate_structured_effect(structured, graph)
    u = _effect_array(structured, graph, label="Structured effect")
    v = _effect_array(unstructured, graph, label="Unstructured effect")
    sigma, phi = _sigma_phi(log_sigma, logit_phi)
    result = sigma * (np.sqrt(phi) * u + np.sqrt(1.0 - phi) * v)
    if not np.isfinite(result).all():
        raise ValueError("Combined county effects must all be finite.")
    return result


def bym2_log_prior(
    structured: np.ndarray,
    unstructured: np.ndarray,
    log_sigma: float,
    logit_phi: float,
    graph: BYM2Graph,
    prior: BYM2Prior,
) -> float:
    """Evaluate the scaled BYM2 log prior, omitting fixed normalizers."""

    try:
        validate_structured_effect(structured, graph)
        u = _effect_array(structured, graph, label="Structured effect")
        v = _effect_array(unstructured, graph, label="Unstructured effect")
        sigma, phi = _sigma_phi(log_sigma, logit_phi)
    except (TypeError, ValueError, OverflowError):
        return float("-inf")

    structured_log_density = -0.5 * float(u @ (graph.scaled_precision @ u))
    unstructured_log_density = -0.5 * float(v @ v)
    with np.errstate(over="ignore", invalid="ignore"):
        standardized_sigma_squared = float(
            np.square(np.float64(sigma / prior.sigma_county_halfnormal_sd))
        )
    sigma_log_density = -0.5 * standardized_sigma_squared + log_sigma
    phi_log_density = float(np.log(phi) + np.log1p(-phi))
    total = (
        structured_log_density
        + unstructured_log_density
        + sigma_log_density
        + phi_log_density
    )
    if not np.isfinite(total):
        return float("-inf")
    return float(total)


SPATIAL_CHECKPOINT_SCHEMA_VERSION = 2
SPATIAL_DRAW_CHUNK_SIZE = 250
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
_SPATIAL_TARGET_FIELDS = {
    "schema_id",
    "run_id",
    "model_id",
    "config_sha256",
    "input_manifest_sha256",
    "source_manifest_sha256",
    "model_frame_semantic_sha256",
    "graph_contract_sha256",
    "likelihood",
    "prior",
    "intercept_mean_rule",
    "intercept_mean_float_hex",
    "design_schema",
    "parameter_schema",
    "extension_epoch",
    "extension_authorization_sha256",
}
_SPATIAL_CHAIN_FIELDS = {
    "chain_id",
    "chain_seed",
    "allocation_initialization_seed",
    "spatial_initialization_seed",
}


def _canonical_mapping(value: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    try:
        return json.loads(_canonical_json(dict(value)).decode("utf-8"))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is not canonically serializable.") from error


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 string.")
    return value


def _validated_array_digest_schema(
    value: Any,
    *,
    dtype: str,
    dimensions: int,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "dtype",
        "shape",
        "sha256",
    }:
        raise ValueError(f"Spatial target {label} schema mismatch.")
    if value["dtype"] != dtype or not isinstance(value["shape"], list):
        raise ValueError(f"Spatial target {label} dtype/shape mismatch.")
    shape = [
        _strict_integer(part, label=f"{label} shape") for part in value["shape"]
    ]
    if len(shape) != dimensions or any(part < 0 for part in shape):
        raise ValueError(f"Spatial target {label} shape mismatch.")
    return {
        "dtype": dtype,
        "shape": shape,
        "sha256": _require_sha256(value["sha256"], label=f"{label} sha256"),
    }


def _validated_design_schema(value: Any) -> dict[str, Any]:
    fields = {
        "schema_id",
        "columns",
        "states",
        "years",
        "x",
        "offset",
        "state_index",
        "year_index",
        "row_county_index",
        "graph_contract_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("Spatial target design_schema fields mismatch.")
    if value["schema_id"] != "sr_v2_spatial_design/v1":
        raise ValueError("Spatial target design_schema id mismatch.")
    result = {
        "schema_id": value["schema_id"],
        "columns": _parameter_schema(value["columns"], label="design columns"),
        "states": _parameter_schema(value["states"], label="design states"),
        "years": _parameter_schema(value["years"], label="design years"),
        "x": _validated_array_digest_schema(
            value["x"], dtype="<f8", dimensions=2, label="design x"
        ),
        "offset": _validated_array_digest_schema(
            value["offset"], dtype="<f8", dimensions=1, label="design offset"
        ),
        "state_index": _validated_array_digest_schema(
            value["state_index"],
            dtype="<i8",
            dimensions=1,
            label="design state_index",
        ),
        "year_index": _validated_array_digest_schema(
            value["year_index"],
            dtype="<i8",
            dimensions=1,
            label="design year_index",
        ),
        "row_county_index": _validated_array_digest_schema(
            value["row_county_index"],
            dtype="<i8",
            dimensions=1,
            label="design row_county_index",
        ),
        "graph_contract_sha256": _require_sha256(
            value["graph_contract_sha256"],
            label="design graph_contract_sha256",
        ),
    }
    row_count = result["x"]["shape"][0]
    if (
        result["x"]["shape"][1] != len(result["columns"])
        or result["offset"]["shape"] != [row_count]
        or result["state_index"]["shape"] != [row_count]
        or result["year_index"]["shape"] != [row_count]
        or result["row_county_index"]["shape"] != [row_count]
    ):
        raise ValueError("Spatial target design_schema dimensions disagree.")
    return result


def spatial_checkpoint_identity(
    *,
    target: Mapping[str, Any],
    chain_id: int,
    chain_seed: int,
    allocation_initialization_seed: int,
    spatial_initialization_seed: int,
) -> dict[str, Any]:
    """Build the complete canonical target/chain fingerprint for checkpoint v2."""

    target_payload = _canonical_mapping(target, label="Spatial target identity")
    if set(target_payload) != _SPATIAL_TARGET_FIELDS:
        raise ValueError(
            "Spatial target identity fields mismatch: "
            f"missing={sorted(_SPATIAL_TARGET_FIELDS - set(target_payload))} "
            f"extra={sorted(set(target_payload) - _SPATIAL_TARGET_FIELDS)}"
        )
    for field in (
        "config_sha256",
        "input_manifest_sha256",
        "source_manifest_sha256",
        "model_frame_semantic_sha256",
        "graph_contract_sha256",
        "extension_authorization_sha256",
    ):
        target_payload[field] = _require_sha256(
            target_payload[field], label=field
        )
    for field in ("schema_id", "run_id", "model_id"):
        if (
            not isinstance(target_payload[field], str)
            or not target_payload[field]
            or target_payload[field].strip() != target_payload[field]
        ):
            raise ValueError(f"Spatial target {field} must be a canonical string.")
    target_payload["design_schema"] = _validated_design_schema(
        target_payload["design_schema"]
    )
    target_payload["parameter_schema"] = _parameter_schema(
        target_payload["parameter_schema"]
    )
    if (
        target_payload["design_schema"]["graph_contract_sha256"]
        != target_payload["graph_contract_sha256"]
    ):
        raise ValueError("Spatial target design and graph fingerprints disagree.")
    prior_payload = _canonical_mapping(
        target_payload["prior"], label="Spatial target prior"
    )
    if set(prior_payload) != {
        "schema_id",
        "base_prior",
        "sigma_county",
        "phi_structured",
    }:
        raise ValueError("Spatial target prior fields mismatch.")
    from .model import PriorSpecification

    if not isinstance(prior_payload["base_prior"], Mapping):
        raise ValueError("Spatial target base prior fields mismatch.")
    try:
        prior_specification = PriorSpecification(**prior_payload["base_prior"])
    except (TypeError, ValueError) as error:
        raise ValueError("Spatial target base prior is invalid.") from error
    if _canonical_json(prior_payload) != _canonical_json(
        spatial_prior_schema(prior_specification)
    ):
        raise ValueError("Spatial target prior schema mismatch.")
    target_payload["prior"] = prior_payload
    if target_payload["likelihood"] != "negative_binomial_2":
        raise ValueError("The frozen spatial target likelihood must be negative_binomial_2.")
    if target_payload["intercept_mean_rule"] != "crude_national_log_rate":
        raise ValueError(
            "Spatial target intercept_mean_rule must be crude_national_log_rate."
        )
    intercept_hex = target_payload["intercept_mean_float_hex"]
    if not isinstance(intercept_hex, str):
        raise ValueError("Spatial target intercept mean must be float.hex text.")
    try:
        intercept_value = float.fromhex(intercept_hex)
    except ValueError as error:
        raise ValueError("Spatial target intercept mean must be float.hex text.") from error
    if not np.isfinite(intercept_value) or intercept_value.hex() != intercept_hex:
        raise ValueError("Spatial target intercept mean must be canonical float.hex text.")
    extension_epoch = _strict_integer(
        target_payload["extension_epoch"], label="extension_epoch"
    )
    if extension_epoch not in range(4):
        raise ValueError("Spatial extension_epoch must be in 0..3.")
    target_payload["extension_epoch"] = extension_epoch
    authorization = target_payload["extension_authorization_sha256"]
    if (extension_epoch == 0 and authorization != "0" * 64) or (
        extension_epoch > 0 and authorization == "0" * 64
    ):
        raise ValueError(
            "Spatial extension authorization hash is inconsistent with extension_epoch."
        )
    target_fingerprint = _sha256(_canonical_json(target_payload))
    chain_payload = {
        "target_fingerprint": target_fingerprint,
        "chain_id": _strict_integer(chain_id, label="chain_id"),
        "chain_seed": _strict_integer(chain_seed, label="chain_seed"),
        "allocation_initialization_seed": _strict_integer(
            allocation_initialization_seed,
            label="allocation_initialization_seed",
        ),
        "spatial_initialization_seed": _strict_integer(
            spatial_initialization_seed,
            label="spatial_initialization_seed",
        ),
    }
    if chain_payload["chain_id"] not in range(1, 5):
        raise ValueError("Spatial chain_id must be in 1..4.")
    for field in _SPATIAL_CHAIN_FIELDS - {"chain_id"}:
        if chain_payload[field] <= 0:
            raise ValueError(f"{field} must be positive.")
    return {
        "schema_version": SPATIAL_CHECKPOINT_SCHEMA_VERSION,
        "target": target_payload,
        "target_fingerprint": target_fingerprint,
        "chain": chain_payload,
        "chain_fingerprint": _sha256(_canonical_json(chain_payload)),
    }


def _validated_spatial_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    payload = _canonical_mapping(identity, label="Spatial checkpoint identity")
    required = {
        "schema_version",
        "target",
        "target_fingerprint",
        "chain",
        "chain_fingerprint",
    }
    if set(payload) != required or _strict_integer(
        payload["schema_version"], label="schema_version"
    ) != 2:
        raise ValueError("Spatial checkpoint identity schema mismatch.")
    chain = payload["chain"]
    if not isinstance(chain, Mapping) or set(chain) != _SPATIAL_CHAIN_FIELDS | {
        "target_fingerprint"
    }:
        raise ValueError("Spatial checkpoint chain identity fields mismatch.")
    rebuilt = spatial_checkpoint_identity(
        target=payload["target"],
        chain_id=_strict_integer(chain["chain_id"], label="chain_id"),
        chain_seed=_strict_integer(chain["chain_seed"], label="chain_seed"),
        allocation_initialization_seed=_strict_integer(
            chain["allocation_initialization_seed"],
            label="allocation_initialization_seed",
        ),
        spatial_initialization_seed=_strict_integer(
            chain["spatial_initialization_seed"],
            label="spatial_initialization_seed",
        ),
    )
    if _canonical_json(payload) != _canonical_json(rebuilt):
        raise ValueError("Spatial checkpoint identity fingerprints are inconsistent.")
    return rebuilt


def _validate_runtime_target_binding(
    identity: Mapping[str, Any],
    *,
    frame: pd.DataFrame,
    design: Any,
    intercept_mean: float,
    prior: Any | None,
) -> None:
    """Bind a reviewed fingerprint to the exact objects evaluating the target."""

    target = identity["target"]
    graph = getattr(design, "spatial_graph", None)
    if graph is None:
        raise ValueError("Spatial runtime target requires a spatial Design.")
    if design.likelihood_family != target["likelihood"]:
        raise ValueError("Spatial runtime target likelihood disagrees with identity.")
    if graph.contract_sha256 != target["graph_contract_sha256"]:
        raise ValueError("Spatial runtime target graph disagrees with identity.")
    if _canonical_json(spatial_design_schema(design)) != _canonical_json(
        target["design_schema"]
    ):
        raise ValueError("Spatial runtime target design schema disagrees with identity.")
    if spatial_parameter_schema(design) != target["parameter_schema"]:
        raise ValueError(
            "Spatial runtime target parameter schema disagrees with identity."
        )
    if _canonical_json(spatial_prior_schema(prior)) != _canonical_json(
        target["prior"]
    ):
        raise ValueError("Spatial runtime target prior disagrees with identity.")
    if spatial_model_frame_sha256(frame) != target[
        "model_frame_semantic_sha256"
    ]:
        raise ValueError("Spatial runtime model frame disagrees with identity.")

    if "county_fips" not in frame.columns:
        raise ValueError("Spatial runtime model frame is missing county_fips.")
    normalized = frame["county_fips"].astype(str).str.strip().str.zfill(5)
    if not normalized.str.fullmatch(r"\d{5}", na=False).all():
        raise ValueError("Spatial runtime model frame has invalid county_fips.")
    if tuple(sorted(normalized.unique())) != tuple(graph.counties):
        raise ValueError("Spatial runtime model frame counties disagree with graph.")
    county_lookup = {
        county: index for index, county in enumerate(graph.counties)
    }
    expected_row_index = normalized.map(county_lookup).to_numpy(dtype=np.int64)
    observed_row_index = np.asarray(graph.row_county_index)
    if (
        observed_row_index.dtype != np.int64
        or observed_row_index.shape != expected_row_index.shape
        or not np.array_equal(observed_row_index, expected_row_index)
    ):
        raise ValueError(
            "Spatial runtime Design row-to-county mapping disagrees with frame order."
        )

    from .model import crude_intercept_prior

    if isinstance(intercept_mean, (bool, np.bool_)) or not isinstance(
        intercept_mean, (int, float, np.integer, np.floating)
    ):
        raise ValueError("Spatial runtime intercept mean must be a finite number.")
    runtime_intercept = float(intercept_mean)
    derived_intercept = float(crude_intercept_prior(frame))
    if (
        not np.isfinite(runtime_intercept)
        or runtime_intercept != derived_intercept
        or runtime_intercept.hex() != target["intercept_mean_float_hex"]
        or target["intercept_mean_rule"] != "crude_national_log_rate"
    ):
        raise ValueError(
            "Spatial runtime intercept disagrees with the crude_national_log_rate identity."
        )


def _path_lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _reject_symlink_path(path: Path, *, label: str) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f"{label} must not use a symbolic link: {current}")
        parent = current.parent
        if parent == current:
            break
        current = parent


def _write_exclusive_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_path(path.parent, label="Publication parent")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(os.fspath(path), flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _publish_new_file_no_clobber(temporary: Path, destination: Path) -> None:
    """Atomically publish a new file while refusing every existing path type."""

    _reject_symlink_path(destination.parent, label="Publication parent")
    _reject_symlink_path(temporary, label="Publication temporary")
    temporary_stat = os.lstat(temporary)
    if not temporary.is_file():
        raise ValueError(f"Publication temporary is not a regular file: {temporary}")
    if _path_lexists(destination):
        raise FileExistsError(f"Publication target already exists: {destination}")
    try:
        os.link(os.fspath(temporary), os.fspath(destination))
    except FileExistsError as error:
        raise FileExistsError(
            f"Publication race: target already exists: {destination}"
        ) from error
    destination_stat = os.lstat(destination)
    current_temporary_stat = os.lstat(temporary)
    identity = (temporary_stat.st_dev, temporary_stat.st_ino)
    if (
        (destination_stat.st_dev, destination_stat.st_ino) != identity
        or (current_temporary_stat.st_dev, current_temporary_stat.st_ino)
        != identity
    ):
        raise RuntimeError("Publication file identity changed during no-clobber commit.")
    temporary.unlink()


@contextmanager
def _exclusive_publication_lock(path: Path):
    _reject_symlink_path(path.parent, label="Publication lock parent")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(os.fspath(path), flags, 0o600)
    except FileExistsError as error:
        raise FileExistsError(f"Publication lock already exists: {path}") from error
    owned = os.fstat(descriptor)
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            current = os.lstat(path)
        except FileNotFoundError:
            current = None
        if current is not None and (current.st_dev, current.st_ino) == (
            owned.st_dev,
            owned.st_ino,
        ):
            path.unlink()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if _path_lexists(temporary):
        raise FileExistsError(f"Publication temporary already exists: {temporary}")
    _write_exclusive_bytes(temporary, text.encode("utf-8"))
    try:
        _publish_new_file_no_clobber(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _write_sha256_sidecar(path: Path) -> Path:
    sidecar = path.with_name(path.name + ".sha256")
    _atomic_text(sidecar, _sha256(path.read_bytes()) + "\n")
    return sidecar


def _verify_sha256_sidecar(path: Path) -> None:
    sidecar = path.with_name(path.name + ".sha256")
    _reject_symlink_path(path, label="Spatial checkpoint")
    _reject_symlink_path(sidecar, label="Spatial checkpoint sidecar")
    if not path.is_file():
        raise ValueError(f"Spatial checkpoint is missing: {path}")
    if not sidecar.is_file():
        raise ValueError(f"Spatial checkpoint SHA-256 sidecar is missing: {sidecar}")
    try:
        sidecar_bytes = sidecar.read_bytes()
        expected = sidecar_bytes[:-1].decode("ascii")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("Spatial checkpoint SHA-256 sidecar is noncanonical.") from error
    if (
        len(sidecar_bytes) != 65
        or sidecar_bytes[-1:] != b"\n"
        or len(expected) != 64
        or any(character not in "0123456789abcdef" for character in expected)
    ):
        raise ValueError("Spatial checkpoint SHA-256 sidecar is noncanonical.")
    actual = _sha256(path.read_bytes())
    if expected != actual:
        raise ValueError(
            f"Spatial checkpoint SHA-256 mismatch: expected {expected}, found {actual}."
        )


def _load_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(raw.decode("ascii"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("Spatial checkpoint JSON is invalid or has duplicate keys.") from error
    if not isinstance(payload, dict) or _canonical_json(payload) != raw:
        raise ValueError("Spatial checkpoint JSON is not canonical.")
    return payload


_SPATIAL_SCALAR_COLUMNS = (
    "chain_id",
    "draw_id",
    "extension_epoch",
    "parameter",
    "value",
)
_DRAW_EPOCH_RANGES = {
    0: (1, 4_500),
    1: (4_501, 7_500),
    2: (7_501, 10_500),
    3: (10_501, 13_500),
}


def _draw_extension_epoch(draw_id: int) -> int:
    exact = _strict_integer(draw_id, label="draw_id")
    for epoch, (start, end) in _DRAW_EPOCH_RANGES.items():
        if start <= exact <= end:
            return epoch
    raise ValueError("Spatial draw id is outside the frozen extension schedule.")


def _float_hex(value: Any, *, label: str) -> str:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result.hex()


def _float_from_hex(value: Any, *, label: str) -> float:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a float.hex string.")
    try:
        result = float.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{label} must be a float.hex string.") from error
    if not np.isfinite(result) or result.hex() != value:
        raise ValueError(f"{label} must be a canonical finite float.hex string.")
    return result


def _array_payload(values: Any, *, dtype: np.dtype[Any]) -> dict[str, Any]:
    array = np.ascontiguousarray(values, dtype=dtype)
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "data_base64": base64.b64encode(array.tobytes(order="C")).decode("ascii"),
    }


def _array_from_payload(
    payload: Any,
    *,
    dtype: np.dtype[Any],
    label: str,
) -> np.ndarray:
    if not isinstance(payload, Mapping) or set(payload) != {
        "dtype",
        "shape",
        "data_base64",
    }:
        raise ValueError(f"{label} array payload schema mismatch.")
    expected_dtype = np.dtype(dtype)
    if payload["dtype"] != expected_dtype.str:
        raise ValueError(f"{label} array dtype mismatch.")
    if not isinstance(payload["shape"], list):
        raise ValueError(f"{label} array shape is invalid.")
    shape = tuple(
        _strict_integer(value, label=f"{label} shape") for value in payload["shape"]
    )
    if any(value < 0 for value in shape):
        raise ValueError(f"{label} array shape is invalid.")
    if not isinstance(payload["data_base64"], str):
        raise ValueError(f"{label} array data is invalid.")
    try:
        raw = base64.b64decode(payload["data_base64"], validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError(f"{label} array data is invalid base64.") from error
    element_count = 1
    for dimension in shape:
        element_count *= dimension
    expected_size = element_count * expected_dtype.itemsize
    if (
        len(raw) != expected_size
        or base64.b64encode(raw).decode("ascii") != payload["data_base64"]
    ):
        raise ValueError(f"{label} array byte length disagrees with its shape.")
    return np.frombuffer(raw, dtype=expected_dtype).copy().reshape(shape)


def _normalize_scalar_frame(
    frame: pd.DataFrame,
    *,
    parameter_schema: Sequence[str],
    expected_draw_ids: Sequence[int],
    expected_chain_id: int,
    maximum_extension_epoch: int,
    label: str,
) -> pd.DataFrame:
    schema = _parameter_schema(parameter_schema)
    expected_ids = [_strict_integer(value, label="draw_id") for value in expected_draw_ids]
    if frame.empty and not expected_ids:
        return pd.DataFrame(
            {
                "chain_id": pd.Series(dtype=np.int64),
                "draw_id": pd.Series(dtype=np.int64),
                "extension_epoch": pd.Series(dtype=np.int64),
                "parameter": pd.Series(dtype=str),
                "value": pd.Series(dtype=np.float64),
            }
        )
    if set(frame.columns) != set(_SPATIAL_SCALAR_COLUMNS):
        raise ValueError(f"{label} scalar parameter schema/cardinality mismatch.")
    work = frame.loc[:, _SPATIAL_SCALAR_COLUMNS].copy()
    chain = _exact_integer_array(work["chain_id"], label=f"{label} chain_id")
    draw = _exact_integer_array(work["draw_id"], label=f"{label} draw_id")
    epoch = _exact_integer_array(
        work["extension_epoch"], label=f"{label} extension_epoch"
    )
    if not work["parameter"].map(lambda value: isinstance(value, str)).all():
        raise ValueError(f"{label} parameter names must be strings.")
    parameter = work["parameter"].astype(str)
    values = pd.to_numeric(work["value"], errors="raise").to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError(f"{label} scalar values must be finite float64 values.")
    if set(chain) != {_strict_integer(expected_chain_id, label="chain_id")}:
        raise ValueError(f"{label} scalar chain identity mismatch.")
    if sorted(np.unique(draw).tolist()) != list(expected_ids):
        raise ValueError(f"{label} scalar draw grid mismatch.")
    if len(work) != len(expected_ids) * len(schema):
        raise ValueError(f"{label} scalar parameter schema/cardinality mismatch.")
    normalized = pd.DataFrame(
        {
            "chain_id": chain,
            "draw_id": draw,
            "extension_epoch": epoch,
            "parameter": parameter.to_numpy(dtype=str),
            "value": values,
        }
    )
    if normalized.duplicated(["chain_id", "draw_id", "parameter"]).any():
        raise ValueError(f"{label} scalar parameter schema/cardinality mismatch.")
    schema_set = set(schema)
    observed = normalized.groupby("draw_id", sort=False)["parameter"].apply(set)
    if len(observed) != len(expected_ids) or any(value != schema_set for value in observed):
        raise ValueError(f"{label} scalar parameter schema/cardinality mismatch.")
    expected_epochs = np.asarray(
        [_draw_extension_epoch(int(value)) for value in draw], dtype=np.int64
    )
    if not np.array_equal(epoch, expected_epochs) or np.any(
        epoch > _strict_integer(maximum_extension_epoch, label="extension_epoch")
    ):
        raise ValueError(f"{label} scalar epoch disagrees with its draw range.")
    for parameter_name, support in (
        ("sigma_county", lambda value: value > 0.0),
        ("phi_structured", lambda value: 0.0 < value < 1.0),
    ):
        selected = normalized.loc[
            normalized["parameter"].eq(parameter_name), "value"
        ].to_numpy(dtype=np.float64)
        if len(selected) and not all(support(value) for value in selected):
            raise ValueError(f"{label} {parameter_name} values are outside support.")
    rank = {name: position for position, name in enumerate(schema)}
    normalized["_parameter_rank"] = normalized["parameter"].map(rank)
    if normalized["_parameter_rank"].isna().any():
        raise ValueError(f"{label} scalar parameter schema/cardinality mismatch.")
    return (
        normalized.sort_values(["draw_id", "_parameter_rank"], kind="stable")
        .drop(columns="_parameter_rank")
        .reset_index(drop=True)
    )


def _pending_scalar_payload(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "columns": list(_SPATIAL_SCALAR_COLUMNS),
        "row_count": int(len(frame)),
        "chain_id": _array_payload(frame["chain_id"], dtype=np.dtype("<i8")),
        "draw_id": _array_payload(frame["draw_id"], dtype=np.dtype("<i8")),
        "extension_epoch": _array_payload(
            frame["extension_epoch"], dtype=np.dtype("<i8")
        ),
        "parameter": frame["parameter"].tolist(),
        "value": _array_payload(frame["value"], dtype=np.dtype("<f8")),
    }


def _read_pending_scalar(payload: Any) -> pd.DataFrame:
    expected = {
        "columns",
        "row_count",
        "chain_id",
        "draw_id",
        "extension_epoch",
        "parameter",
        "value",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise ValueError("Pending scalar checkpoint schema mismatch.")
    if payload["columns"] != list(_SPATIAL_SCALAR_COLUMNS):
        raise ValueError("Pending scalar checkpoint columns mismatch.")
    row_count = _strict_integer(payload["row_count"], label="pending row_count")
    parameter = payload["parameter"]
    if not isinstance(parameter, list) or any(
        not isinstance(value, str) for value in parameter
    ):
        raise ValueError("Pending scalar parameter encoding is invalid.")
    frame = pd.DataFrame(
        {
            "chain_id": _array_from_payload(
                payload["chain_id"], dtype=np.dtype("<i8"), label="pending chain_id"
            ),
            "draw_id": _array_from_payload(
                payload["draw_id"], dtype=np.dtype("<i8"), label="pending draw_id"
            ),
            "extension_epoch": _array_from_payload(
                payload["extension_epoch"],
                dtype=np.dtype("<i8"),
                label="pending extension_epoch",
            ),
            "parameter": parameter,
            "value": _array_from_payload(
                payload["value"], dtype=np.dtype("<f8"), label="pending value"
            ),
        }
    )
    if len(frame) != row_count:
        raise ValueError("Pending scalar checkpoint row count mismatch.")
    return frame


def _validate_pending_draws(
    *,
    committed_chunks: Sequence[Mapping[str, Any]],
    pending_scalar: pd.DataFrame,
    pending_structured: np.ndarray,
    pending_unstructured: np.ndarray,
    next_draw_id: int,
    saved_draws: int,
    graph: BYM2Graph,
    parameter_schema: Sequence[str],
    chain_id: int,
    extension_epoch: int,
) -> pd.DataFrame:
    structured = np.asarray(pending_structured, dtype=np.float64)
    unstructured = np.asarray(pending_unstructured, dtype=np.float64)
    if (
        structured.ndim != 2
        or unstructured.ndim != 2
        or structured.shape != unstructured.shape
        or structured.shape[1:] != (len(graph.counties),)
        or not np.isfinite(structured).all()
        or not np.isfinite(unstructured).all()
    ):
        raise ValueError("Pending spatial buffers are malformed or nonfinite.")
    for row in structured:
        validate_structured_effect(row, graph)
    committed_end = 0
    if committed_chunks:
        committed_end = int(committed_chunks[-1]["draw_end"])
    expected_pending_ids = list(range(committed_end + 1, int(next_draw_id)))
    if (
        len(expected_pending_ids) >= SPATIAL_DRAW_CHUNK_SIZE
        or len(expected_pending_ids) != structured.shape[0]
    ):
        raise ValueError("Pending spatial buffers disagree with next_draw_id.")
    normalized_scalar = _normalize_scalar_frame(
        pending_scalar,
        parameter_schema=parameter_schema,
        expected_draw_ids=expected_pending_ids,
        expected_chain_id=chain_id,
        maximum_extension_epoch=extension_epoch,
        label="Pending",
    )
    if int(saved_draws) != int(next_draw_id) - 1:
        raise ValueError("saved_draws must equal next_draw_id minus one.")
    return normalized_scalar


def _validated_adaptation_state(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "multiplier",
        "epsilon_structured",
        "epsilon_unstructured",
        "attempted",
        "accepted",
        "window_attempted",
        "window_accepted",
        "windows_completed",
        "adaptation_frozen",
    }
    if set(value) != expected:
        raise ValueError("Spatial MALA adaptation checkpoint schema mismatch.")
    result = {
        "multiplier": float(value["multiplier"]),
        "epsilon_structured": float(value["epsilon_structured"]),
        "epsilon_unstructured": float(value["epsilon_unstructured"]),
        "attempted": _strict_integer(value["attempted"], label="MALA attempted"),
        "accepted": _strict_integer(value["accepted"], label="MALA accepted"),
        "window_attempted": _strict_integer(
            value["window_attempted"], label="MALA window_attempted"
        ),
        "window_accepted": _strict_integer(
            value["window_accepted"], label="MALA window_accepted"
        ),
        "windows_completed": _strict_integer(
            value["windows_completed"], label="MALA windows_completed"
        ),
        "adaptation_frozen": value["adaptation_frozen"],
    }
    if not isinstance(result["adaptation_frozen"], (bool, np.bool_)):
        raise ValueError("Spatial MALA adaptation_frozen must be boolean.")
    result["adaptation_frozen"] = bool(result["adaptation_frozen"])
    if (
        not np.isfinite(result["multiplier"])
        or not 0.1 <= result["multiplier"] <= 5.0
        or result["epsilon_structured"] != 0.02 * result["multiplier"]
        or result["epsilon_unstructured"] != 0.04 * result["multiplier"]
        or min(
            result["attempted"],
            result["accepted"],
            result["window_attempted"],
            result["window_accepted"],
            result["windows_completed"],
        )
        < 0
        or result["accepted"] > result["attempted"]
        or result["window_accepted"] > result["window_attempted"]
        or result["window_accepted"] > result["accepted"]
        or result["window_attempted"] > result["attempted"]
        or result["window_attempted"] >= 100
    ):
        raise ValueError("Spatial MALA adaptation checkpoint values are invalid.")
    return result


def _validate_checkpoint_progress(
    *,
    extension_epoch: int,
    iteration: int,
    saved_draws: int,
    adaptation: Mapping[str, Any],
    accepted: Mapping[str, Any],
    proposed: Mapping[str, Any],
) -> None:
    epoch = _strict_integer(extension_epoch, label="extension_epoch")
    if epoch not in range(4):
        raise ValueError("Checkpoint extension epoch must be in 0..3.")
    current_iteration = _strict_integer(iteration, label="iteration")
    if epoch == 0:
        lower_iteration, upper_iteration = 0, 180_000
    else:
        lower_iteration = 180_000 + (epoch - 1) * 90_000
        upper_iteration = 180_000 + epoch * 90_000
    if not lower_iteration <= current_iteration <= upper_iteration:
        raise ValueError("Checkpoint iteration is outside its extension epoch.")
    expected_saved = max(0, (current_iteration - 45_000) // 30)
    if _strict_integer(saved_draws, label="saved_draws") != expected_saved:
        raise ValueError("Checkpoint saved draw count disagrees with iteration schedule.")
    expected_attempts = current_iteration // 5
    if _strict_integer(adaptation["attempted"], label="MALA attempted") != expected_attempts:
        raise ValueError("Checkpoint MALA attempts disagree with iteration schedule.")
    adaptive_attempts = min(expected_attempts, 9_000)
    if _strict_integer(
        adaptation["windows_completed"], label="MALA windows_completed"
    ) != adaptive_attempts // 100:
        raise ValueError("Checkpoint MALA adaptation windows disagree with schedule.")
    expected_window_attempts = adaptive_attempts % 100 if expected_attempts < 9_000 else 0
    if _strict_integer(
        adaptation["window_attempted"], label="MALA window_attempted"
    ) != expected_window_attempts:
        raise ValueError("Checkpoint MALA adaptation window position is inconsistent.")
    should_be_frozen = epoch > 0 or current_iteration >= 45_000
    if bool(adaptation["adaptation_frozen"]) != should_be_frozen:
        raise ValueError("Checkpoint MALA freeze state disagrees with epoch/iteration.")
    if _strict_integer(proposed.get("mala", 0), label="proposed mala") != expected_attempts or _strict_integer(
        accepted.get("mala", 0), label="accepted mala"
    ) != _strict_integer(adaptation["accepted"], label="MALA accepted"):
        raise ValueError("Checkpoint MALA counters disagree with adaptation state.")
    for block in (
        "beta",
        "state",
        "year",
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
        "spatial_hyperparameters",
    ):
        if _strict_integer(
            proposed[block], label=f"proposed {block}"
        ) != current_iteration:
            raise ValueError(
                "Checkpoint scheduled parameter counters disagree with iteration."
            )


def _validated_counters(value: Mapping[str, Any], *, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Checkpoint {label} counters must be a mapping.")
    if set(value) != set(SPATIAL_COUNTER_SCHEMA):
        raise ValueError(
            f"Checkpoint {label} counter universe does not match the frozen counter schema."
        )
    result: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Checkpoint {label} counter names must be strings.")
        exact = _strict_integer(count, label=f"{label} counter {key}")
        if exact < 0:
            raise ValueError(f"Checkpoint {label} counters must be nonnegative.")
        result[key] = exact
    return dict(sorted(result.items()))


def _validate_checkpoint_theta(theta: Any, design: Any) -> None:
    graph = design.spatial_graph
    if graph is None:
        raise ValueError("Spatial checkpoint requires a spatial design.")
    arrays = {
        "beta": (theta.beta, (design.x.shape[1],)),
        "state_effect": (theta.state_effect, (len(design.states),)),
        "year_effect": (theta.year_effect, (len(design.years),)),
        "spatial_structured": (theta.spatial_structured, (len(graph.counties),)),
        "spatial_unstructured": (theta.spatial_unstructured, (len(graph.counties),)),
    }
    for label, (values, expected_shape) in arrays.items():
        if values is None:
            raise ValueError(f"Spatial checkpoint requires {label}.")
        array = np.asarray(values, dtype=np.float64)
        if array.shape != expected_shape or not np.isfinite(array).all():
            raise ValueError(
                f"Spatial checkpoint {label} shape/values disagree with Design."
            )
    for label in (
        "log_sigma_state",
        "log_sigma_year",
        "log_kappa",
        "log_sigma_county",
        "logit_phi_structured",
    ):
        if getattr(theta, label) is None or not np.isfinite(float(getattr(theta, label))):
            raise ValueError(f"Spatial checkpoint {label} must be finite.")
    for label in ("state_effect", "year_effect"):
        values = np.asarray(getattr(theta, label), dtype=np.float64)
        if abs(float(values.mean())) > 1e-12:
            raise ValueError(f"Spatial checkpoint {label} must be centered.")
    validate_structured_effect(theta.spatial_structured, graph)


def _adaptation_checkpoint_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    checked = _validated_adaptation_state(value)
    return {
        "multiplier_hex": _float_hex(checked["multiplier"], label="MALA multiplier"),
        "epsilon_structured_hex": _float_hex(
            checked["epsilon_structured"], label="MALA epsilon_structured"
        ),
        "epsilon_unstructured_hex": _float_hex(
            checked["epsilon_unstructured"], label="MALA epsilon_unstructured"
        ),
        "attempted": checked["attempted"],
        "accepted": checked["accepted"],
        "window_attempted": checked["window_attempted"],
        "window_accepted": checked["window_accepted"],
        "windows_completed": checked["windows_completed"],
        "adaptation_frozen": checked["adaptation_frozen"],
    }


def _adaptation_from_checkpoint_payload(value: Any) -> dict[str, Any]:
    expected = {
        "multiplier_hex",
        "epsilon_structured_hex",
        "epsilon_unstructured_hex",
        "attempted",
        "accepted",
        "window_attempted",
        "window_accepted",
        "windows_completed",
        "adaptation_frozen",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("Spatial MALA adaptation checkpoint schema mismatch.")
    return _validated_adaptation_state(
        {
            "multiplier": _float_from_hex(
                value["multiplier_hex"], label="MALA multiplier"
            ),
            "epsilon_structured": _float_from_hex(
                value["epsilon_structured_hex"], label="MALA epsilon_structured"
            ),
            "epsilon_unstructured": _float_from_hex(
                value["epsilon_unstructured_hex"], label="MALA epsilon_unstructured"
            ),
            "attempted": value["attempted"],
            "accepted": value["accepted"],
            "window_attempted": value["window_attempted"],
            "window_accepted": value["window_accepted"],
            "windows_completed": value["windows_completed"],
            "adaptation_frozen": value["adaptation_frozen"],
        }
    )


_SPATIAL_CHECKPOINT_FIELDS = {
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


def save_spatial_checkpoint(
    path: str | Path,
    *,
    identity: Mapping[str, Any],
    extension_epoch: int,
    job_attempt: int,
    y: np.ndarray,
    theta: Any,
    rng: np.random.Generator,
    frame: pd.DataFrame,
    design: Any,
    intercept_mean: float,
    prior: Any | None = None,
    iteration: int,
    saved_draws: int,
    current_target: float,
    accepted: Mapping[str, int],
    proposed: Mapping[str, int],
    committed_chunks: Sequence[Mapping[str, Any]],
    pending_scalar: pd.DataFrame,
    pending_structured: np.ndarray,
    pending_unstructured: np.ndarray,
    adaptation_state: Mapping[str, Any],
    next_draw_id: int,
    output_positions: Mapping[str, int],
    chunk_dir: str | Path | None = None,
    crash_hook: Callable[[str], None] | None = None,
) -> None:
    """Atomically publish one full schema-v2 spatial continuation checkpoint."""

    destination = Path(path)
    if destination.suffix.lower() != ".json":
        raise ValueError("Spatial checkpoint path must use the frozen .json format.")
    sidecar = destination.with_name(destination.name + ".sha256")
    _reject_symlink_path(destination.parent, label="Checkpoint parent")
    if _path_lexists(destination) or _path_lexists(sidecar):
        raise FileExistsError(f"Spatial checkpoint already exists: {destination}")
    checked_identity = _validated_spatial_identity(identity)
    _validate_runtime_target_binding(
        checked_identity,
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        prior=prior,
    )
    exact_epoch = _strict_integer(extension_epoch, label="extension_epoch")
    if exact_epoch != checked_identity["target"]["extension_epoch"]:
        raise ValueError("Checkpoint extension epoch disagrees with target identity.")
    exact_attempt = _strict_integer(job_attempt, label="job_attempt")
    if exact_attempt not in range(1, 4):
        raise ValueError("Spatial job_attempt must be in 1..3.")
    graph_hash = checked_identity["target"]["graph_contract_sha256"]
    if design.spatial_graph is None or design.spatial_graph.contract_sha256 != graph_hash:
        raise ValueError("Checkpoint design graph does not match target identity.")
    _validate_checkpoint_theta(theta, design)
    checked_y = _exact_integer_array(y, label="Spatial checkpoint counts")
    if checked_y.shape != (len(frame),) or len(design.offset) != len(frame):
        raise ValueError("Spatial checkpoint count/design shapes disagree.")
    from .constraints import assert_constraints
    from .model import log_posterior_theta

    assert_constraints(checked_y, frame, label="spatial_checkpoint_save")
    recomputed_target = log_posterior_theta(
        checked_y,
        theta,
        design,
        intercept_mean=float(intercept_mean),
        prior=prior,
    )
    if (
        not np.isfinite(recomputed_target)
        or not np.isfinite(float(current_target))
        or float(recomputed_target) != float(current_target)
    ):
        raise ValueError("Spatial checkpoint current target does not recompute exactly.")
    records = [_canonical_mapping(row, label="Committed chunk") for row in committed_chunks]
    if records and chunk_dir is None:
        raise ValueError("Committed spatial chunks require their exact chunk directory.")
    if chunk_dir is not None:
        validate_spatial_chunk_inventory(
            chunk_dir,
            expected_records=records,
            expected_next_draw_id=(
                1 if not records else int(records[-1]["draw_end"]) + 1
            ),
            expected_chain_id=checked_identity["chain"]["chain_id"],
            maximum_extension_epoch=exact_epoch,
            expected_graph=design.spatial_graph,
            expected_parameter_schema=checked_identity["target"]["parameter_schema"],
        )
    exact_next_draw = _strict_integer(next_draw_id, label="next_draw_id")
    exact_saved_draws = _strict_integer(saved_draws, label="saved_draws")
    normalized_pending_scalar = _validate_pending_draws(
        committed_chunks=records,
        pending_scalar=pending_scalar,
        pending_structured=pending_structured,
        pending_unstructured=pending_unstructured,
        next_draw_id=exact_next_draw,
        saved_draws=exact_saved_draws,
        graph=design.spatial_graph,
        parameter_schema=checked_identity["target"]["parameter_schema"],
        chain_id=checked_identity["chain"]["chain_id"],
        extension_epoch=exact_epoch,
    )
    if not isinstance(output_positions, Mapping):
        raise ValueError("Checkpoint output positions must be a mapping.")
    positions = {
        str(key): _strict_integer(value, label=f"output position {key}")
        for key, value in output_positions.items()
    }
    parameter_count = len(checked_identity["target"]["parameter_schema"])
    expected_scalar_rows = exact_saved_draws * parameter_count
    if (
        set(positions) != {"scalar_rows", "spatial_draws"}
        or any(value < 0 for value in positions.values())
        or positions["spatial_draws"] != exact_saved_draws
        or positions["scalar_rows"] != expected_scalar_rows
    ):
        raise ValueError("Checkpoint output positions disagree with saved draws.")
    checked_accepted = _validated_counters(accepted, label="accepted")
    checked_proposed = _validated_counters(proposed, label="proposed")
    for key, value in checked_accepted.items():
        if value > checked_proposed.get(key, -1):
            raise ValueError("Checkpoint accepted counters exceed proposals.")
    checked_adaptation = _validated_adaptation_state(adaptation_state)
    exact_iteration = _strict_integer(iteration, label="iteration")
    _validate_checkpoint_progress(
        extension_epoch=exact_epoch,
        iteration=exact_iteration,
        saved_draws=exact_saved_draws,
        adaptation=checked_adaptation,
        accepted=checked_accepted,
        proposed=checked_proposed,
    )
    chain = checked_identity["chain"]
    payload = {
        "schema_version": SPATIAL_CHECKPOINT_SCHEMA_VERSION,
        "run_id": checked_identity["target"]["run_id"],
        "model_id": checked_identity["target"]["model_id"],
        "target_fingerprint": checked_identity["target_fingerprint"],
        "chain_fingerprint": checked_identity["chain_fingerprint"],
        "extension_epoch": exact_epoch,
        "job_attempt": exact_attempt,
        "chain_id": chain["chain_id"],
        "seeds": {
            "chain_seed": chain["chain_seed"],
            "allocation_initialization_seed": chain[
                "allocation_initialization_seed"
            ],
            "spatial_initialization_seed": chain["spatial_initialization_seed"],
        },
        "current_state": {
            "y": _array_payload(checked_y, dtype=np.dtype("<i8")),
            "beta": _array_payload(theta.beta, dtype=np.dtype("<f8")),
            "state_effect": _array_payload(
                theta.state_effect, dtype=np.dtype("<f8")
            ),
            "year_effect": _array_payload(
                theta.year_effect, dtype=np.dtype("<f8")
            ),
            "log_sigma_state_hex": _float_hex(
                theta.log_sigma_state, label="log_sigma_state"
            ),
            "log_sigma_year_hex": _float_hex(
                theta.log_sigma_year, label="log_sigma_year"
            ),
            "log_kappa_hex": _float_hex(theta.log_kappa, label="log_kappa"),
            "spatial_structured": _array_payload(
                theta.spatial_structured, dtype=np.dtype("<f8")
            ),
            "spatial_unstructured": _array_payload(
                theta.spatial_unstructured, dtype=np.dtype("<f8")
            ),
            "log_sigma_county_hex": _float_hex(
                theta.log_sigma_county, label="log_sigma_county"
            ),
            "logit_phi_structured_hex": _float_hex(
                theta.logit_phi_structured, label="logit_phi_structured"
            ),
        },
        "rng_state": _canonical_mapping(
            rng.bit_generator.state, label="RNG state"
        ),
        "current_target": _float_hex(
            recomputed_target, label="current target"
        ),
        "iteration": exact_iteration,
        "saved_draws": exact_saved_draws,
        "accepted": checked_accepted,
        "proposed": checked_proposed,
        "committed_chunks": records,
        "pending_buffers": {
            "scalar": _pending_scalar_payload(normalized_pending_scalar),
            "structured": _array_payload(
                pending_structured, dtype=np.dtype("<f8")
            ),
            "unstructured": _array_payload(
                pending_unstructured, dtype=np.dtype("<f8")
            ),
        },
        "adaptation_state": _adaptation_checkpoint_payload(checked_adaptation),
        "next_draw_id": exact_next_draw,
        "output_positions": positions,
    }
    if set(payload) != _SPATIAL_CHECKPOINT_FIELDS:
        raise AssertionError("Internal spatial checkpoint field drift.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.with_name(destination.name + ".publish.lock")
    with _exclusive_publication_lock(lock):
        if _path_lexists(destination) or _path_lexists(sidecar):
            raise FileExistsError(
                f"Spatial checkpoint publication target already exists: {destination}"
            )
        _atomic_text(destination, _canonical_json(payload).decode("ascii"))
        if crash_hook is not None:
            crash_hook("after_checkpoint_publish")
        _write_sha256_sidecar(destination)
        if crash_hook is not None:
            crash_hook("after_sidecar_publish")


def load_spatial_checkpoint(
    path: str | Path,
    *,
    expected_identity: Mapping[str, Any],
    frame: pd.DataFrame | None = None,
    design: Any | None = None,
    intercept_mean: float | None = None,
    prior: Any | None = None,
    chunk_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load only an exact identity-bound, constraint-valid continuation."""

    source = Path(path)
    _verify_sha256_sidecar(source)
    payload = _load_canonical_json(source)
    if set(payload) != _SPATIAL_CHECKPOINT_FIELDS:
        raise ValueError("Spatial checkpoint top-level schema mismatch.")
    expected = _validated_spatial_identity(expected_identity)
    if design is None or frame is None or intercept_mean is None:
        raise ValueError(
            "Spatial checkpoint resume requires frame, spatial design, and intercept for target recomputation."
        )
    if design.spatial_graph is None:
        raise ValueError("Checkpoint target recomputation requires a spatial design.")
    _validate_runtime_target_binding(
        expected,
        frame=frame,
        design=design,
        intercept_mean=intercept_mean,
        prior=prior,
    )
    if _strict_integer(payload["schema_version"], label="schema_version") != 2:
        raise ValueError("Spatial checkpoint schema version mismatch.")
    expected_top = {
        "run_id": expected["target"]["run_id"],
        "model_id": expected["target"]["model_id"],
        "target_fingerprint": expected["target_fingerprint"],
        "chain_fingerprint": expected["chain_fingerprint"],
    }
    if any(payload[key] != value for key, value in expected_top.items()):
        raise ValueError("Spatial checkpoint identity mismatch.")
    extension_epoch = _strict_integer(
        payload["extension_epoch"], label="extension_epoch"
    )
    job_attempt = _strict_integer(payload["job_attempt"], label="job_attempt")
    chain_id = _strict_integer(payload["chain_id"], label="chain_id")
    if (
        extension_epoch != expected["target"]["extension_epoch"]
        or job_attempt not in range(1, 4)
        or chain_id != expected["chain"]["chain_id"]
    ):
        raise ValueError("Spatial checkpoint chain/epoch/attempt identity mismatch.")
    seeds = payload["seeds"]
    expected_seed_fields = {
        "chain_seed",
        "allocation_initialization_seed",
        "spatial_initialization_seed",
    }
    if not isinstance(seeds, Mapping) or set(seeds) != expected_seed_fields:
        raise ValueError("Spatial checkpoint seed schema mismatch.")
    for field in expected_seed_fields:
        if _strict_integer(seeds[field], label=field) != expected["chain"][field]:
            raise ValueError("Spatial checkpoint seed identity mismatch.")
    state = payload["current_state"]
    state_fields = {
        "y",
        "beta",
        "state_effect",
        "year_effect",
        "log_sigma_state_hex",
        "log_sigma_year_hex",
        "log_kappa_hex",
        "spatial_structured",
        "spatial_unstructured",
        "log_sigma_county_hex",
        "logit_phi_structured_hex",
    }
    if not isinstance(state, Mapping) or set(state) != state_fields:
        raise ValueError("Spatial checkpoint current_state schema mismatch.")
    from .model import Theta

    y = _array_from_payload(state["y"], dtype=np.dtype("<i8"), label="y")
    theta = Theta(
        beta=_array_from_payload(
            state["beta"], dtype=np.dtype("<f8"), label="beta"
        ),
        state_effect=_array_from_payload(
            state["state_effect"], dtype=np.dtype("<f8"), label="state_effect"
        ),
        year_effect=_array_from_payload(
            state["year_effect"], dtype=np.dtype("<f8"), label="year_effect"
        ),
        log_sigma_state=_float_from_hex(
            state["log_sigma_state_hex"], label="log_sigma_state"
        ),
        log_sigma_year=_float_from_hex(
            state["log_sigma_year_hex"], label="log_sigma_year"
        ),
        log_kappa=_float_from_hex(state["log_kappa_hex"], label="log_kappa"),
        spatial_structured=_array_from_payload(
            state["spatial_structured"],
            dtype=np.dtype("<f8"),
            label="spatial_structured",
        ),
        spatial_unstructured=_array_from_payload(
            state["spatial_unstructured"],
            dtype=np.dtype("<f8"),
            label="spatial_unstructured",
        ),
        log_sigma_county=_float_from_hex(
            state["log_sigma_county_hex"], label="log_sigma_county"
        ),
        logit_phi_structured=_float_from_hex(
            state["logit_phi_structured_hex"], label="logit_phi_structured"
        ),
    )
    pending = payload["pending_buffers"]
    if not isinstance(pending, Mapping) or set(pending) != {
        "scalar",
        "structured",
        "unstructured",
    }:
        raise ValueError("Spatial checkpoint pending_buffers schema mismatch.")
    pending_scalar = _read_pending_scalar(pending["scalar"])
    pending_structured = _array_from_payload(
        pending["structured"], dtype=np.dtype("<f8"), label="pending structured"
    )
    pending_unstructured = _array_from_payload(
        pending["unstructured"],
        dtype=np.dtype("<f8"),
        label="pending unstructured",
    )
    if not isinstance(payload["committed_chunks"], list):
        raise ValueError("Spatial checkpoint committed_chunks must be a list.")
    committed_chunks = [
        _canonical_mapping(record, label="Committed chunk")
        for record in payload["committed_chunks"]
    ]
    saved_draws = _strict_integer(payload["saved_draws"], label="saved_draws")
    next_draw_id = _strict_integer(payload["next_draw_id"], label="next_draw_id")
    iteration = _strict_integer(payload["iteration"], label="iteration")
    current_target = _float_from_hex(
        payload["current_target"], label="current_target"
    )
    checked_accepted = _validated_counters(payload["accepted"], label="accepted")
    checked_proposed = _validated_counters(payload["proposed"], label="proposed")
    for key, value in checked_accepted.items():
        if value > checked_proposed.get(key, -1):
            raise ValueError("Spatial checkpoint acceptance counters are invalid.")
    adaptation = _adaptation_from_checkpoint_payload(payload["adaptation_state"])
    normalized_pending = _validate_pending_draws(
        committed_chunks=committed_chunks,
        pending_scalar=pending_scalar,
        pending_structured=pending_structured,
        pending_unstructured=pending_unstructured,
        next_draw_id=next_draw_id,
        saved_draws=saved_draws,
        graph=design.spatial_graph,
        parameter_schema=expected["target"]["parameter_schema"],
        chain_id=chain_id,
        extension_epoch=extension_epoch,
    )
    if _canonical_json(_pending_scalar_payload(normalized_pending)) != _canonical_json(
        pending["scalar"]
    ):
        raise ValueError("Pending scalar checkpoint ordering is noncanonical.")
    positions = payload["output_positions"]
    if (
        not isinstance(positions, dict)
        or set(positions) != {"scalar_rows", "spatial_draws"}
    ):
        raise ValueError("Spatial checkpoint output positions are invalid.")
    checked_positions = {
        key: _strict_integer(value, label=f"output position {key}")
        for key, value in positions.items()
    }
    if checked_positions != {
        "spatial_draws": saved_draws,
        "scalar_rows": saved_draws * len(expected["target"]["parameter_schema"]),
    }:
        raise ValueError("Spatial checkpoint output positions are invalid.")
    _validate_checkpoint_progress(
        extension_epoch=extension_epoch,
        iteration=iteration,
        saved_draws=saved_draws,
        adaptation=adaptation,
        accepted=checked_accepted,
        proposed=checked_proposed,
    )
    if committed_chunks and chunk_dir is None:
        raise ValueError(
            "A checkpoint with committed chunks requires its exact chunk directory."
        )
    if chunk_dir is not None:
        validate_spatial_chunk_inventory(
            chunk_dir,
            expected_records=committed_chunks,
            expected_next_draw_id=(
                1 if not committed_chunks else int(committed_chunks[-1]["draw_end"]) + 1
            ),
            expected_chain_id=chain_id,
            maximum_extension_epoch=extension_epoch,
            expected_graph=design.spatial_graph,
            expected_parameter_schema=expected["target"]["parameter_schema"],
        )
    if design.spatial_graph.contract_sha256 != expected["target"][
        "graph_contract_sha256"
    ]:
        raise ValueError("Checkpoint design graph does not match target identity.")
    _validate_checkpoint_theta(theta, design)
    from .constraints import assert_constraints
    from .model import log_posterior_theta

    assert_constraints(y, frame, label="spatial_checkpoint_resume")
    recomputed = log_posterior_theta(
        y,
        theta,
        design,
        intercept_mean=float(intercept_mean),
        prior=prior,
    )
    if not np.isfinite(recomputed) or float(recomputed) != current_target:
        raise ValueError("Spatial checkpoint current target does not recompute exactly.")
    rng = np.random.default_rng()
    try:
        rng.bit_generator.state = payload["rng_state"]
    except (TypeError, ValueError) as error:
        raise ValueError("Spatial checkpoint RNG state is invalid.") from error
    if _canonical_json(rng.bit_generator.state) != _canonical_json(
        payload["rng_state"]
    ):
        raise ValueError("Spatial checkpoint RNG state is noncanonical.")
    return {
        "schema_version": SPATIAL_CHECKPOINT_SCHEMA_VERSION,
        "identity": expected,
        "extension_epoch": extension_epoch,
        "job_attempt": job_attempt,
        "y": y,
        "theta": theta,
        "iteration": iteration,
        "saved_draws": saved_draws,
        "current_target": float(recomputed),
        "accepted": checked_accepted,
        "proposed": checked_proposed,
        "committed_chunks": committed_chunks,
        "pending_scalar": normalized_pending,
        "pending_structured": pending_structured,
        "pending_unstructured": pending_unstructured,
        "adaptation_state": adaptation,
        "next_draw_id": next_draw_id,
        "output_positions": checked_positions,
        "rng": rng,
    }


_CHUNK_MANIFEST_NAME = "spatial_chunk_manifest.json"


def _exact_integer_array(values: Any, *, label: str) -> np.ndarray:
    array = np.asarray(values)
    if (
        array.ndim != 1
        or np.issubdtype(array.dtype, np.bool_)
        or not np.issubdtype(array.dtype, np.integer)
    ):
        raise ValueError(f"{label} must contain finite exact integers.")
    return array.astype(np.int64)


def _exact_integer_value(value: Any, *, label: str) -> int:
    return _strict_integer(value, label=label)


def _load_chunk_manifest(chunk_dir: Path) -> list[dict[str, Any]]:
    manifest = chunk_dir / _CHUNK_MANIFEST_NAME
    _reject_symlink_path(chunk_dir, label="Spatial chunk directory")
    _reject_symlink_path(manifest, label="Spatial chunk manifest")
    if not manifest.is_file():
        if not chunk_dir.exists() or not any(chunk_dir.iterdir()):
            return []
        raise ValueError("Spatial chunk manifest is missing while orphan files exist.")
    try:
        payload = _load_canonical_json(manifest)
    except (OSError, ValueError) as error:
        raise ValueError("Spatial chunk manifest is corrupt.") from error
    if (
        set(payload) != {"schema_id", "records"}
        or payload["schema_id"] != "sr_v2_spatial_chunk_manifest/v1"
        or not isinstance(payload["records"], list)
    ):
        raise ValueError("Spatial chunk manifest schema mismatch.")
    return [
        _canonical_mapping(record, label="Spatial chunk record")
        for record in payload["records"]
    ]


def validate_spatial_chunk_inventory(
    chunk_dir: str | Path,
    *,
    expected_records: Sequence[Mapping[str, Any]] | None = None,
    expected_next_draw_id: int | None = None,
    expected_chain_id: int | None = None,
    maximum_extension_epoch: int | None = None,
    expected_graph: BYM2Graph | None = None,
    expected_parameter_schema: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Verify exact paired chunk inventory, hashes, ranges, and schemas."""

    root = Path(chunk_dir)
    _reject_symlink_path(root, label="Spatial chunk directory")
    if root.exists() and not root.is_dir():
        raise ValueError("Spatial chunk directory path is not a directory.")
    records = _load_chunk_manifest(root)
    if expected_records is not None:
        expected = [
            _canonical_mapping(record, label="Expected spatial chunk record")
            for record in expected_records
        ]
        if _canonical_json(records) != _canonical_json(expected):
            raise ValueError("Spatial chunk manifest disagrees with checkpoint inventory.")
    allowed = {_CHUNK_MANIFEST_NAME} if records else set()
    next_draw = 1
    previous_chunk_id = 0
    bound_chain = (
        None
        if expected_chain_id is None
        else _strict_integer(expected_chain_id, label="expected_chain_id")
    )
    maximum_epoch = (
        3
        if maximum_extension_epoch is None
        else _strict_integer(
            maximum_extension_epoch, label="maximum_extension_epoch"
        )
    )
    if maximum_epoch not in range(4):
        raise ValueError("maximum_extension_epoch must be in 0..3.")
    bound_schema = (
        None
        if expected_parameter_schema is None
        else _parameter_schema(expected_parameter_schema)
    )
    bound_graph_hash = None if expected_graph is None else expected_graph.contract_sha256
    bound_county_count = None if expected_graph is None else len(expected_graph.counties)
    inventory_identity: tuple[int, str, str, int, tuple[str, ...]] | None = None
    for record in records:
        required = {
            "schema_id",
            "chain_id",
            "extension_epoch",
            "chunk_id",
            "draw_start",
            "draw_end",
            "draw_count",
            "scalar_path",
            "scalar_sha256",
            "spatial_path",
            "spatial_sha256",
            "graph_contract_sha256",
            "county_order_sha256",
            "county_count",
            "parameter_schema",
        }
        if set(record) != required or record["schema_id"] != "sr_v2_spatial_draw_chunk/v1":
            raise ValueError("Spatial chunk record schema mismatch.")
        chunk_id = _exact_integer_value(record["chunk_id"], label="chunk_id")
        draw_start = _exact_integer_value(record["draw_start"], label="draw_start")
        draw_end = _exact_integer_value(record["draw_end"], label="draw_end")
        draw_count = _exact_integer_value(record["draw_count"], label="draw_count")
        record_chain = _exact_integer_value(record["chain_id"], label="chain_id")
        record_epoch = _exact_integer_value(
            record["extension_epoch"], label="extension_epoch"
        )
        graph_hash = _require_sha256(
            record["graph_contract_sha256"], label="graph_contract_sha256"
        )
        county_order_hash = _require_sha256(
            record["county_order_sha256"], label="county_order_sha256"
        )
        county_count = _exact_integer_value(
            record["county_count"], label="county_count"
        )
        parameter_schema = _parameter_schema(record["parameter_schema"])
        record_identity = (
            record_chain,
            graph_hash,
            county_order_hash,
            county_count,
            tuple(parameter_schema),
        )
        if inventory_identity is None:
            inventory_identity = record_identity
        elif record_identity != inventory_identity:
            raise ValueError("Spatial chunk identity changes within one inventory.")
        expected_epoch = _draw_extension_epoch(draw_start)
        if (
            chunk_id != previous_chunk_id + 1
            or draw_start != next_draw
            or draw_end - draw_start + 1 != draw_count
            or draw_count != SPATIAL_DRAW_CHUNK_SIZE
            or _draw_extension_epoch(draw_end) != expected_epoch
            or record_epoch != expected_epoch
            or record_epoch > maximum_epoch
            or record_chain not in range(1, 5)
            or county_count <= 0
        ):
            raise ValueError("Spatial chunk ranges overlap, are missing, or are out of order.")
        if bound_chain is not None and record_chain != bound_chain:
            raise ValueError("Spatial chunk chain identity mismatch.")
        if bound_graph_hash is not None and graph_hash != bound_graph_hash:
            raise ValueError("Spatial chunk graph identity mismatch.")
        if bound_county_count is not None and county_count != bound_county_count:
            raise ValueError("Spatial chunk county count mismatch.")
        if bound_schema is not None and parameter_schema != bound_schema:
            raise ValueError("Spatial chunk parameter schema mismatch.")
        expected_county_order_hash = (
            None
            if expected_graph is None
            else _sha256(
                "".join(f"{county}\n" for county in expected_graph.counties).encode(
                    "utf-8"
                )
            )
        )
        if (
            expected_county_order_hash is not None
            and county_order_hash != expected_county_order_hash
        ):
            raise ValueError("Spatial chunk county order identity mismatch.")
        previous_chunk_id = chunk_id
        next_draw = draw_end + 1
        scalar_name = str(record["scalar_path"])
        spatial_name = str(record["spatial_path"])
        if (
            Path(scalar_name).name != scalar_name
            or Path(spatial_name).name != spatial_name
            or scalar_name != f"scalar_chunk_{chunk_id:06d}.parquet"
            or spatial_name != f"spatial_chunk_{chunk_id:06d}.npz"
        ):
            raise ValueError("Spatial chunk paths must be simple relative file names.")
        allowed.update((scalar_name, spatial_name))
        scalar_path = root / scalar_name
        spatial_path = root / spatial_name
        _reject_symlink_path(scalar_path, label="Scalar chunk")
        _reject_symlink_path(spatial_path, label="Spatial chunk")
        if not scalar_path.is_file() or not spatial_path.is_file():
            raise ValueError("Spatial chunk pair is missing one or both files.")
        if _sha256(scalar_path.read_bytes()) != _require_sha256(
            record["scalar_sha256"], label="scalar_sha256"
        ) or _sha256(spatial_path.read_bytes()) != _require_sha256(
            record["spatial_sha256"], label="spatial_sha256"
        ):
            raise ValueError("Spatial chunk file SHA-256 mismatch.")
        scalar = pd.read_parquet(scalar_path)
        required_scalar = {
            "chain_id",
            "draw_id",
            "extension_epoch",
            "parameter",
            "value",
        }
        if set(scalar.columns) != required_scalar:
            raise ValueError("Scalar chunk schema/cardinality mismatch.")
        expected_ids = list(range(draw_start, draw_end + 1))
        normalized_scalar = _normalize_scalar_frame(
            scalar,
            parameter_schema=parameter_schema,
            expected_draw_ids=expected_ids,
            expected_chain_id=record_chain,
            maximum_extension_epoch=record_epoch,
            label="Scalar chunk",
        )
        if not normalized_scalar.equals(scalar.reset_index(drop=True)):
            raise ValueError("Scalar chunk row order/dtypes are noncanonical.")
        with np.load(spatial_path, allow_pickle=False) as spatial:
            if set(spatial.files) != {
                "chain_id",
                "extension_epoch",
                "draw_id",
                "structured",
                "unstructured",
            }:
                raise ValueError("Spatial chunk NPZ schema mismatch.")
            spatial_ids = spatial["draw_id"]
            spatial_chain = spatial["chain_id"]
            spatial_epoch = spatial["extension_epoch"]
            structured = spatial["structured"]
            unstructured = spatial["unstructured"]
            if (
                spatial_chain.dtype != np.dtype("<i8")
                or spatial_chain.shape != ()
                or spatial_epoch.dtype != np.dtype("<i8")
                or spatial_epoch.shape != ()
                or spatial_ids.dtype != np.dtype("<i8")
                or spatial_ids.shape != (draw_count,)
                or spatial_ids.tolist() != expected_ids
                or _exact_integer_value(spatial_chain.item(), label="spatial chain_id") != record_chain
                or _exact_integer_value(spatial_epoch.item(), label="spatial extension_epoch")
                != record_epoch
                or structured.dtype != np.float64
                or unstructured.dtype != np.float64
                or structured.ndim != 2
                or structured.shape != unstructured.shape
                or structured.shape != (draw_count, county_count)
                or not np.isfinite(structured).all()
                or not np.isfinite(unstructured).all()
            ):
                raise ValueError("Spatial chunk identity/shape/value mismatch.")
            if expected_graph is not None:
                for row in structured:
                    validate_structured_effect(row, expected_graph)
    if root.exists():
        for path in root.iterdir():
            if path.is_symlink():
                raise ValueError("Spatial chunk inventory must not contain symlinks.")
    actual = {path.name for path in root.iterdir()} if root.exists() else set()
    if actual != allowed:
        raise ValueError(
            "Spatial chunk inventory contains orphan or temporary files: "
            f"extra={sorted(actual - allowed)} missing={sorted(allowed - actual)}"
        )
    if expected_next_draw_id is not None and next_draw != _strict_integer(
        expected_next_draw_id, label="expected_next_draw_id"
    ):
        raise ValueError("Spatial chunk next draw id disagrees with checkpoint.")
    return records


def commit_spatial_draw_chunk(
    chunk_dir: str | Path,
    *,
    chain_id: int,
    extension_epoch: int,
    graph: BYM2Graph,
    parameter_schema: Sequence[str],
    chunk_id: int,
    draw_ids: np.ndarray,
    scalar_draws: pd.DataFrame,
    structured: np.ndarray,
    unstructured: np.ndarray,
    final_chunk: bool = False,
    crash_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Commit one scalar/spatial pair; the manifest rename is the commit point."""

    root = Path(chunk_dir)
    _reject_symlink_path(root, label="Spatial chunk directory")
    root.mkdir(parents=True, exist_ok=True)
    exact_chain_id = _exact_integer_value(chain_id, label="chain_id")
    exact_extension_epoch = _exact_integer_value(
        extension_epoch, label="extension_epoch"
    )
    if exact_chain_id not in range(1, 5):
        raise ValueError("Spatial chunk chain_id must be in 1..4.")
    if exact_extension_epoch not in range(4):
        raise ValueError("Spatial chunk extension_epoch must be in 0..3.")
    schema = _parameter_schema(parameter_schema)
    existing = validate_spatial_chunk_inventory(
        root,
        expected_chain_id=exact_chain_id,
        maximum_extension_epoch=exact_extension_epoch,
        expected_graph=graph,
        expected_parameter_schema=schema,
    )
    ids = _exact_integer_array(draw_ids, label="Spatial chunk draw ids")
    if ids.ndim != 1 or len(ids) == 0 or not np.array_equal(
        ids, np.arange(ids[0], ids[0] + len(ids), dtype=np.int64)
    ):
        raise ValueError("Spatial chunk draw ids must be a nonempty contiguous range.")
    if len(ids) != SPATIAL_DRAW_CHUNK_SIZE:
        raise ValueError("Spatial chunks must contain exactly 250 draws.")
    _ = final_chunk
    expected_start = 1 if not existing else int(existing[-1]["draw_end"]) + 1
    exact_chunk_id = _exact_integer_value(chunk_id, label="chunk_id")
    if (
        int(ids[0]) != expected_start
        or exact_chunk_id != len(existing) + 1
        or _draw_extension_epoch(int(ids[0])) != exact_extension_epoch
        or _draw_extension_epoch(int(ids[-1])) != exact_extension_epoch
    ):
        raise ValueError(
            "Spatial chunk id, epoch, or draw range does not continue the committed inventory."
        )
    structured_array = np.asarray(structured, dtype=np.float64)
    unstructured_array = np.asarray(unstructured, dtype=np.float64)
    if (
        structured_array.ndim != 2
        or structured_array.shape != unstructured_array.shape
        or structured_array.shape != (len(ids), len(graph.counties))
        or not np.isfinite(structured_array).all()
        or not np.isfinite(unstructured_array).all()
    ):
        raise ValueError(
            "Spatial chunk arrays have malformed county dimensions or nonfinite values."
        )
    for row in structured_array:
        validate_structured_effect(row, graph)
    scalar = _normalize_scalar_frame(
        scalar_draws,
        parameter_schema=schema,
        expected_draw_ids=ids.tolist(),
        expected_chain_id=exact_chain_id,
        maximum_extension_epoch=exact_extension_epoch,
        label="Scalar chunk",
    )
    scalar_name = f"scalar_chunk_{exact_chunk_id:06d}.parquet"
    spatial_name = f"spatial_chunk_{exact_chunk_id:06d}.npz"
    scalar_path = root / scalar_name
    spatial_path = root / spatial_name
    scalar_temporary = root / (scalar_name + ".tmp")
    spatial_temporary = root / (spatial_name + ".tmp.npz")
    manifest = root / _CHUNK_MANIFEST_NAME
    manifest_temporary = root / (_CHUNK_MANIFEST_NAME + ".tmp")
    scalar_buffer = io.BytesIO()
    scalar.to_parquet(scalar_buffer, index=False)
    spatial_buffer = io.BytesIO()
    np.savez_compressed(
        spatial_buffer,
        chain_id=np.asarray(exact_chain_id, dtype=np.int64),
        extension_epoch=np.asarray(exact_extension_epoch, dtype=np.int64),
        draw_id=ids.astype(np.int64, copy=False),
        structured=structured_array,
        unstructured=unstructured_array,
    )
    scalar_payload = scalar_buffer.getvalue()
    spatial_payload = spatial_buffer.getvalue()
    record = {
        "schema_id": "sr_v2_spatial_draw_chunk/v1",
        "chain_id": exact_chain_id,
        "extension_epoch": exact_extension_epoch,
        "chunk_id": exact_chunk_id,
        "draw_start": int(ids[0]),
        "draw_end": int(ids[-1]),
        "draw_count": int(len(ids)),
        "scalar_path": scalar_name,
        "scalar_sha256": _sha256(scalar_payload),
        "spatial_path": spatial_name,
        "spatial_sha256": _sha256(spatial_payload),
        "graph_contract_sha256": graph.contract_sha256,
        "county_order_sha256": _sha256(
            "".join(f"{county}\n" for county in graph.counties).encode("utf-8")
        ),
        "county_count": len(graph.counties),
        "parameter_schema": schema,
    }
    lock = root.parent / f".{root.name}.commit.lock"
    with _exclusive_publication_lock(lock):
        validate_spatial_chunk_inventory(
            root,
            expected_records=existing,
            expected_next_draw_id=expected_start,
            expected_chain_id=exact_chain_id,
            maximum_extension_epoch=exact_extension_epoch,
            expected_graph=graph,
            expected_parameter_schema=schema,
        )
        for candidate in (
            scalar_path,
            spatial_path,
            scalar_temporary,
            spatial_temporary,
            manifest_temporary,
        ):
            if _path_lexists(candidate):
                raise FileExistsError(
                    f"Spatial chunk target already exists: {candidate}"
                )
        _write_exclusive_bytes(scalar_temporary, scalar_payload)
        if crash_hook is not None:
            crash_hook("after_scalar_temp")
        _write_exclusive_bytes(spatial_temporary, spatial_payload)
        if crash_hook is not None:
            crash_hook("after_spatial_temp")
        _publish_new_file_no_clobber(scalar_temporary, scalar_path)
        if crash_hook is not None:
            crash_hook("after_scalar_rename")
        _publish_new_file_no_clobber(spatial_temporary, spatial_path)
        if crash_hook is not None:
            crash_hook("after_spatial_rename")
        manifest_payload = {
            "schema_id": "sr_v2_spatial_chunk_manifest/v1",
            "records": existing + [record],
        }
        _write_exclusive_bytes(
            manifest_temporary,
            _canonical_json(manifest_payload),
        )
        if existing:
            _reject_symlink_path(manifest, label="Spatial chunk manifest")
            if _canonical_json(_load_chunk_manifest(root)) != _canonical_json(
                existing
            ):
                raise ValueError("Spatial chunk manifest changed during publication.")
            os.replace(manifest_temporary, manifest)
        else:
            _publish_new_file_no_clobber(manifest_temporary, manifest)
        if crash_hook is not None:
            crash_hook("after_manifest_rename")
        validate_spatial_chunk_inventory(
            root,
            expected_records=existing + [record],
            expected_next_draw_id=int(ids[-1]) + 1,
            expected_chain_id=exact_chain_id,
            maximum_extension_epoch=exact_extension_epoch,
            expected_graph=graph,
            expected_parameter_schema=schema,
        )
    return record


def merge_spatial_draw_chunks(
    chunk_dir: str | Path,
    *,
    records: Sequence[Mapping[str, Any]],
    scalar_output: str | Path,
    spatial_output: str | Path,
    graph: BYM2Graph,
    crash_hook: Callable[[str], None] | None = None,
) -> None:
    """Merge a verified single-chain chunk sequence without duplicate draws."""

    root = Path(chunk_dir)
    if not records:
        raise ValueError("At least one verified spatial chunk is required.")
    first = records[0]
    verified = validate_spatial_chunk_inventory(
        root,
        expected_records=records,
        expected_graph=graph,
        expected_chain_id=_exact_integer_value(
            first["chain_id"], label="record chain_id"
        ),
        maximum_extension_epoch=max(
            _exact_integer_value(record["extension_epoch"], label="record epoch")
            for record in records
        ),
        expected_parameter_schema=first["parameter_schema"],
    )
    if not verified:
        raise ValueError("At least one verified spatial chunk is required.")
    scalar_frames: list[pd.DataFrame] = []
    draw_ids: list[np.ndarray] = []
    chain_ids: list[np.ndarray] = []
    extension_epochs: list[np.ndarray] = []
    structured: list[np.ndarray] = []
    unstructured: list[np.ndarray] = []
    for record in verified:
        scalar_frames.append(pd.read_parquet(root / record["scalar_path"]))
        with np.load(root / record["spatial_path"], allow_pickle=False) as spatial:
            ids = spatial["draw_id"].astype(np.int64)
            draw_ids.append(ids)
            chain_ids.append(np.full(len(ids), int(record["chain_id"]), dtype=np.int64))
            extension_epochs.append(
                np.full(len(ids), int(record["extension_epoch"]), dtype=np.int64)
            )
            structured.append(spatial["structured"].astype(np.float64))
            unstructured.append(spatial["unstructured"].astype(np.float64))
    scalar = pd.concat(scalar_frames, ignore_index=True)
    if scalar.duplicated(["chain_id", "draw_id", "parameter"]).any():
        raise ValueError("Merged scalar chunks contain duplicate draws.")
    ids = np.concatenate(draw_ids)
    chains = np.concatenate(chain_ids)
    if pd.DataFrame({"chain_id": chains, "draw_id": ids}).duplicated().any():
        raise ValueError("Merged spatial chunks contain duplicate draws.")
    scalar_destination = Path(scalar_output)
    spatial_destination = Path(spatial_output)
    if os.path.abspath(scalar_destination) == os.path.abspath(spatial_destination):
        raise ValueError("Merged scalar and spatial destinations must be distinct.")
    _reject_symlink_path(scalar_destination.parent, label="Merged scalar parent")
    _reject_symlink_path(spatial_destination.parent, label="Merged spatial parent")
    if _path_lexists(scalar_destination) or _path_lexists(spatial_destination):
        raise FileExistsError("Merged spatial draw output already exists.")
    scalar_destination.parent.mkdir(parents=True, exist_ok=True)
    spatial_destination.parent.mkdir(parents=True, exist_ok=True)
    scalar_temporary = scalar_destination.with_name(scalar_destination.name + ".tmp")
    spatial_temporary = spatial_destination.with_name(spatial_destination.name + ".tmp.npz")
    scalar_buffer = io.BytesIO()
    scalar.to_parquet(scalar_buffer, index=False)
    spatial_buffer = io.BytesIO()
    np.savez_compressed(
        spatial_buffer,
        chain_id=chains,
        extension_epoch=np.concatenate(extension_epochs),
        draw_id=ids,
        structured=np.concatenate(structured, axis=0).astype(np.float64),
        unstructured=np.concatenate(unstructured, axis=0).astype(np.float64),
    )
    lock_digest = _sha256(
        (
            os.path.abspath(scalar_destination)
            + "\n"
            + os.path.abspath(spatial_destination)
        ).encode("utf-8")
    )
    lock = scalar_destination.parent / f".spatial-merge-{lock_digest}.lock"
    with _exclusive_publication_lock(lock):
        for candidate in (
            scalar_destination,
            spatial_destination,
            scalar_temporary,
            spatial_temporary,
        ):
            if _path_lexists(candidate):
                raise FileExistsError(
                    f"Merged spatial draw publication target already exists: {candidate}"
                )
        _write_exclusive_bytes(scalar_temporary, scalar_buffer.getvalue())
        _write_exclusive_bytes(spatial_temporary, spatial_buffer.getvalue())
        _publish_new_file_no_clobber(scalar_temporary, scalar_destination)
        if crash_hook is not None:
            crash_hook("after_scalar_publish")
        _publish_new_file_no_clobber(spatial_temporary, spatial_destination)
        if crash_hook is not None:
            crash_hook("after_spatial_publish")


__all__ = [
    "BYM2Graph",
    "BYM2Prior",
    "SPATIAL_CHECKPOINT_SCHEMA_VERSION",
    "SPATIAL_DRAW_CHUNK_SIZE",
    "build_bym2_graph",
    "bym2_log_prior",
    "commit_spatial_draw_chunk",
    "combined_county_effect",
    "componentwise_center",
    "frozen_graph_contract_from_execution",
    "load_spatial_checkpoint",
    "merge_spatial_draw_chunks",
    "save_spatial_checkpoint",
    "spatial_checkpoint_identity",
    "validate_spatial_chunk_inventory",
    "validate_structured_effect",
]
