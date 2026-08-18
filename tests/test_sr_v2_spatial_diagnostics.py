from __future__ import annotations

import hashlib
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.spatial_diagnostics import (  # noqa: E402
    download_county_adjacency,
    morans_i,
    neighbor_map,
    permutation_morans_i,
    read_county_adjacency,
    row_standardized_weights,
    within_group_morans_i,
)


COUNTIES = ["01001", "01003", "01005", "01007"]


def load_spatial_runner():
    script = ROOT / "scripts" / "90_run_sr_v2_spatial_residual_diagnostics.py"
    spec = importlib.util.spec_from_file_location("sr_v2_spatial_runner", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference_dense_permutation(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    permutations: int,
    seed: int,
) -> dict[str, float | int]:
    nonisolated = weights.sum(axis=1) > 0
    x = np.asarray(values, dtype=float)[nonisolated]
    w = np.asarray(weights, dtype=float)[np.ix_(nonisolated, nonisolated)]
    centered = x - x.mean()
    denominator = float(centered @ centered)
    weight_sum = float(w.sum())
    observed = float(len(x) / weight_sum * float(centered @ w @ centered) / denominator)
    expected = -1.0 / (len(x) - 1)
    rng = np.random.default_rng(seed)
    simulated = np.empty(permutations, dtype=float)
    for index in range(permutations):
        permuted = rng.permutation(x)
        permuted_centered = permuted - permuted.mean()
        numerator = float(permuted_centered @ w @ permuted_centered)
        simulated[index] = float(len(x) / weight_sum * numerator / denominator)
    observed_distance = abs(observed - expected)
    simulated_distance = np.abs(simulated - expected)
    p_value = float(
        (1 + np.count_nonzero(simulated_distance >= observed_distance))
        / (permutations + 1)
    )
    return {
        "statistic": observed,
        "expected_under_randomization": expected,
        "permutation_p_two_sided": p_value,
        "permutations": permutations,
        "observations": len(values),
        "nonisolated_observations": int(nonisolated.sum()),
        "directed_weight_sum": weight_sum,
    }


def adjacency_bytes() -> bytes:
    return (
        "County Name|County GEOID|Neighbor Name|Neighbor GEOID\n"
        "A|01001|A|01001\n"
        "A|01001|B|01003\n"
        "B|01003|A|01001\n"
        "B|01003|B|01003\n"
        "B|01003|C|01005\n"
        "C|01005|B|01003\n"
        "C|01005|C|01005\n"
        "C|01005|D|01007\n"
        "D|01007|C|01005\n"
        "D|01007|D|01007\n"
    ).encode("utf-8")


def test_adjacency_parser_and_neighbor_map_remove_self_links() -> None:
    adjacency = read_county_adjacency(adjacency_bytes())
    neighbors = neighbor_map(adjacency, ["01001", "01003", "01005", "01007"])
    assert neighbors["01001"] == ("01003",)
    assert neighbors["01003"] == ("01001", "01005")
    assert neighbors["01005"] == ("01003", "01007")
    assert neighbors["01007"] == ("01005",)


def test_morans_i_matches_known_path_graph_value() -> None:
    adjacency = read_county_adjacency(adjacency_bytes())
    counties = ["01001", "01003", "01005", "01007"]
    weights = row_standardized_weights(counties, neighbor_map(adjacency, counties))
    values = np.array([1.0, 1.0, -1.0, -1.0])
    assert morans_i(values, weights) == 0.5


def test_permutation_morans_i_is_reproducible() -> None:
    adjacency = read_county_adjacency(adjacency_bytes())
    counties = ["01001", "01003", "01005", "01007"]
    weights = row_standardized_weights(counties, neighbor_map(adjacency, counties))
    values = np.array([1.0, 1.0, -1.0, -1.0])
    first = permutation_morans_i(values, weights, permutations=199, seed=42)
    second = permutation_morans_i(values, weights, permutations=199, seed=42)
    assert first.to_dict() == second.to_dict()
    assert first.statistic == 0.5
    assert 0 < first.permutation_p_two_sided <= 1


def test_sparse_permutation_matches_reference_dense_algorithm() -> None:
    values = np.array([1.0, 1.0, -1.0, -1.0])
    adjacency = read_county_adjacency(adjacency_bytes())
    weights = row_standardized_weights(COUNTIES, neighbor_map(adjacency, COUNTIES))
    expected = reference_dense_permutation(values, weights, permutations=199, seed=42)
    assert (
        permutation_morans_i(values, weights, permutations=199, seed=42).to_dict()
        == expected
    )


def test_sparse_permutation_preserves_constant_value_behavior() -> None:
    adjacency = read_county_adjacency(adjacency_bytes())
    weights = row_standardized_weights(COUNTIES, neighbor_map(adjacency, COUNTIES))
    result = permutation_morans_i(
        np.ones(len(COUNTIES)),
        weights,
        permutations=199,
        seed=42,
    )
    assert np.isnan(result.statistic)
    assert result.permutation_p_two_sided == 1 / 200


def test_spatial_runner_rejects_changed_production_input(tmp_path: Path) -> None:
    runner = load_spatial_runner()
    relative_path = Path("posterior_primary_summary.csv")
    input_path = tmp_path / relative_path
    input_path.write_text("original\n", encoding="utf-8")
    manifest = runner.build_input_manifest(tmp_path, (relative_path,))
    input_path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256"):
        runner.verify_input_manifest(tmp_path, manifest)


def test_spatial_runner_publishes_no_derived_outputs_after_integrity_failure(
    tmp_path: Path,
) -> None:
    runner = load_spatial_runner()
    protected_path = Path("protected-input.txt")
    (tmp_path / protected_path).write_text("original\n", encoding="utf-8")
    manifest = runner.build_input_manifest(tmp_path, (protected_path,))
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    derived_names = (
        "global_morans_i.csv",
        "within_state_morans_i.csv",
        "county_spatial_residuals.csv",
    )
    tables = {
        name: pd.DataFrame({"value": [index]})
        for index, name in enumerate(derived_names)
    }

    (tmp_path / protected_path).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256"):
        runner.publish_derived_outputs(
            output_root=output_root,
            input_root=tmp_path,
            input_manifest=manifest,
            tables=tables,
            text_outputs={},
        )

    assert all(not (output_root / name).exists() for name in derived_names)


def test_adjacency_download_manifest_includes_utc_retrieval_time(
    tmp_path: Path,
) -> None:
    payload = adjacency_bytes()
    source = tmp_path / "source.txt"
    source.write_bytes(payload)
    destination = tmp_path / "downloaded.txt"
    manifest = download_county_adjacency(destination, url=source.as_uri())
    retrieved = datetime.fromisoformat(str(manifest["retrieved_utc"]))
    assert retrieved.tzinfo == timezone.utc
    assert manifest == {
        "url": source.as_uri(),
        "retrieved_utc": manifest["retrieved_utc"],
        "path": str(destination),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_within_group_diagnostic_skips_small_or_isolated_groups() -> None:
    adjacency = read_county_adjacency(adjacency_bytes())
    counties = ["01001", "01003", "01005", "01007"]
    table = pd.DataFrame(
        {
            "county_fips": counties,
            "state_fips": ["01"] * 4,
            "residual": [1.0, 1.0, -1.0, -1.0],
        }
    )
    result = within_group_morans_i(
        table,
        neighbor_map(adjacency, counties),
        value_column="residual",
        minimum_counties=4,
        permutations=99,
        seed=10,
    )
    assert len(result) == 1
    assert result.iloc[0]["state_fips"] == "01"
    assert result.iloc[0]["statistic"] == 0.5
