from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.spatial_diagnostics import (  # noqa: E402
    morans_i,
    neighbor_map,
    permutation_morans_i,
    read_county_adjacency,
    row_standardized_weights,
    within_group_morans_i,
)


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
