from __future__ import annotations

import hashlib
import io
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix


CENSUS_COUNTY_ADJACENCY_2024_URL = (
    "https://www2.census.gov/geo/docs/reference/county_adjacency/"
    "county_adjacency2024.txt"
)


@dataclass(frozen=True)
class MoranResult:
    statistic: float
    expected_under_randomization: float
    permutation_p_two_sided: float
    permutations: int
    observations: int
    nonisolated_observations: int
    directed_weight_sum: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "statistic": float(self.statistic),
            "expected_under_randomization": float(self.expected_under_randomization),
            "permutation_p_two_sided": float(self.permutation_p_two_sided),
            "permutations": int(self.permutations),
            "observations": int(self.observations),
            "nonisolated_observations": int(self.nonisolated_observations),
            "directed_weight_sum": float(self.directed_weight_sum),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_county_adjacency(
    destination: Path,
    *,
    url: str = CENSUS_COUNTY_ADJACENCY_2024_URL,
    timeout_seconds: int = 60,
) -> dict[str, str | int]:
    """Download and checksum the public Census county-adjacency file.

    The retrieved file is archived with the analysis so later reproduction does
    not depend on the remote resource remaining byte-identical.
    """

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "epilepsy-mortality-suppression-atlas/2"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"County-adjacency download returned no bytes: {url}")
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return {
        "url": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "path": str(destination),
        "bytes": int(destination.stat().st_size),
        "sha256": sha256_file(destination),
    }


def read_county_adjacency(source: str | Path | bytes) -> pd.DataFrame:
    """Read the four-column pipe-delimited Census county-adjacency layout."""

    if isinstance(source, bytes):
        handle: str | Path | io.BytesIO = io.BytesIO(source)
    else:
        handle = source
    frame = pd.read_csv(handle, sep="|", dtype=str)
    required = {"County GEOID", "Neighbor GEOID"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Adjacency file is missing columns: {sorted(missing)}")
    out = frame.rename(
        columns={
            "County Name": "county_name",
            "County GEOID": "county_fips",
            "Neighbor Name": "neighbor_name",
            "Neighbor GEOID": "neighbor_fips",
        }
    ).copy()
    out["county_fips"] = out["county_fips"].astype(str).str.zfill(5)
    out["neighbor_fips"] = out["neighbor_fips"].astype(str).str.zfill(5)
    out = out[out["county_fips"].str.fullmatch(r"\d{5}", na=False)]
    out = out[out["neighbor_fips"].str.fullmatch(r"\d{5}", na=False)]
    return out.drop_duplicates(["county_fips", "neighbor_fips"]).reset_index(drop=True)


def neighbor_map(
    adjacency: pd.DataFrame,
    county_fips: Iterable[str],
    *,
    include_self: bool = False,
) -> dict[str, tuple[str, ...]]:
    """Return a symmetric, model-frame-filtered county neighbor map."""

    counties = {str(value).zfill(5) for value in county_fips}
    work = adjacency[
        adjacency["county_fips"].isin(counties)
        & adjacency["neighbor_fips"].isin(counties)
    ].copy()
    if not include_self:
        work = work[~work["county_fips"].eq(work["neighbor_fips"])]
    pairs = {
        (str(left).zfill(5), str(right).zfill(5))
        for left, right in work[["county_fips", "neighbor_fips"]].itertuples(index=False)
    }
    # The Census file is expected to contain both directions. Add the reverse
    # explicitly so a partially filtered or hand-constructed test file remains
    # safe for symmetric spatial diagnostics.
    pairs |= {(right, left) for left, right in pairs}
    result: dict[str, tuple[str, ...]] = {}
    for county in sorted(counties):
        result[county] = tuple(sorted(right for left, right in pairs if left == county))
    return result


def row_standardized_weights(
    ordered_counties: list[str],
    neighbors: dict[str, tuple[str, ...]],
) -> np.ndarray:
    """Construct a dense row-standardized matrix for auditable diagnostics."""

    index = {county: position for position, county in enumerate(ordered_counties)}
    weights = np.zeros((len(ordered_counties), len(ordered_counties)), dtype=float)
    for county, adjacent in neighbors.items():
        if county not in index:
            continue
        valid = [neighbor for neighbor in adjacent if neighbor in index and neighbor != county]
        if not valid:
            continue
        row = index[county]
        weight = 1.0 / len(valid)
        for neighbor in valid:
            weights[row, index[neighbor]] = weight
    return weights


def _moran_components(
    values: np.ndarray,
    weights: np.ndarray | csr_matrix,
) -> tuple[np.ndarray, csr_matrix, float, float]:
    x = np.asarray(values, dtype=float)
    w = weights if isinstance(weights, csr_matrix) else csr_matrix(weights)
    if w.shape != (len(x), len(x)):
        raise ValueError(f"Weight matrix shape {w.shape} does not match {len(x)} values.")
    if not np.isfinite(x).all():
        raise ValueError("Moran's I values must all be finite after analytic filtering.")
    centered = x - x.mean()
    denominator = float(centered @ centered)
    weight_sum = float(w.sum())
    return centered, w, denominator, weight_sum


def morans_i(values: np.ndarray, weights: np.ndarray) -> float:
    """Calculate global Moran's I for a supplied weight matrix."""

    centered, w, denominator, weight_sum = _moran_components(values, weights)
    if denominator <= 0 or weight_sum <= 0:
        return float("nan")
    numerator = float(centered @ (w @ centered))
    return float(len(centered) / weight_sum * numerator / denominator)


def permutation_morans_i(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    permutations: int = 9999,
    seed: int = 20260811,
) -> MoranResult:
    """Evaluate Moran's I using a deterministic two-sided permutation test."""

    if permutations < 0:
        raise ValueError("permutations must be nonnegative")
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    nonisolated = np.asarray(weights.sum(axis=1) > 0)
    if nonisolated.sum() < 3:
        raise ValueError("At least three nonisolated observations are required.")
    # Isolated counties contribute no numerator information. Excluding them also
    # prevents their values from changing the mean used for connected counties.
    x = values[nonisolated]
    centered, sparse_weights, denominator, weight_sum = _moran_components(
        x,
        csr_matrix(weights[np.ix_(nonisolated, nonisolated)]),
    )
    if denominator <= 0 or weight_sum <= 0:
        observed = float("nan")
    else:
        observed_numerator = float(centered @ (sparse_weights @ centered))
        observed = float(len(x) / weight_sum * observed_numerator / denominator)
    expected = -1.0 / (len(x) - 1)
    rng = np.random.default_rng(seed)
    if permutations:
        simulated = np.empty(permutations, dtype=float)
        if denominator <= 0 or weight_sum <= 0:
            simulated.fill(np.nan)
        else:
            for index in range(permutations):
                permuted = rng.permutation(x)
                permuted_centered = permuted - permuted.mean()
                numerator = float(
                    permuted_centered @ (sparse_weights @ permuted_centered)
                )
                simulated[index] = float(
                    len(x) / weight_sum * numerator / denominator
                )
        observed_distance = abs(observed - expected)
        simulated_distance = np.abs(simulated - expected)
        p_value = float((1 + np.count_nonzero(simulated_distance >= observed_distance)) / (permutations + 1))
    else:
        p_value = float("nan")
    return MoranResult(
        statistic=observed,
        expected_under_randomization=expected,
        permutation_p_two_sided=p_value,
        permutations=permutations,
        observations=len(values),
        nonisolated_observations=int(nonisolated.sum()),
        directed_weight_sum=weight_sum,
    )


def within_group_morans_i(
    table: pd.DataFrame,
    neighbors: dict[str, tuple[str, ...]],
    *,
    value_column: str,
    group_column: str = "state_fips",
    county_column: str = "county_fips",
    minimum_counties: int = 10,
    permutations: int = 999,
    seed: int = 20260811,
) -> pd.DataFrame:
    """Calculate within-group Moran statistics where the graph is estimable."""

    rows: list[dict[str, object]] = []
    for group, subset in table.groupby(group_column, sort=True):
        subset = subset.dropna(subset=[value_column]).copy()
        counties = subset[county_column].astype(str).str.zfill(5).tolist()
        if len(counties) < minimum_counties:
            continue
        weights = row_standardized_weights(counties, neighbors)
        if int((weights.sum(axis=1) > 0).sum()) < minimum_counties:
            continue
        result = permutation_morans_i(
            subset[value_column].to_numpy(dtype=float),
            weights,
            permutations=permutations,
            seed=seed + int(str(group)),
        )
        rows.append({group_column: str(group), **result.to_dict()})
    return pd.DataFrame(rows)
