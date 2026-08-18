"""Canonical county graph and scaled BYM2 prior primitives.

The graph contract is deliberately independent of model-frame row order.  Its
county and edge hashes are over the exact line-oriented formats frozen by the
SR-v2 spatial sensitivity plan, while the contract hash is over canonical JSON.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

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


__all__ = [
    "BYM2Graph",
    "BYM2Prior",
    "build_bym2_graph",
    "bym2_log_prior",
    "combined_county_effect",
    "componentwise_center",
    "validate_structured_effect",
]
