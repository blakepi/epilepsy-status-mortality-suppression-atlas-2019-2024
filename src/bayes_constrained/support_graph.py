from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StateSupportSummary:
    state_fips: str
    free_cells: int
    exact_margin_free_cells: int
    interval_margin_free_cells: int
    exact_margin_counties: int
    interval_margin_counties: int
    exact_support_components: int
    exact_support_cycle_rank: int
    exact_support_cycle_edges: int
    exact_support_four_cycle_edges: int
    exact_support_long_cycle_only_edges: int
    exact_support_four_cycle_span_rank_gf2: int
    exact_support_unspanned_cycle_dimension_gf2: int
    cyclic_components_without_four_cycle: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _bridges(adjacency: dict[str, set[str]]) -> set[frozenset[str]]:
    discovery: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    bridges: set[frozenset[str]] = set()
    time = 0

    def visit(node: str) -> None:
        nonlocal time
        time += 1
        discovery[node] = time
        low[node] = time
        for neighbor in adjacency.get(node, set()):
            if neighbor not in discovery:
                parent[neighbor] = node
                visit(neighbor)
                low[node] = min(low[node], low[neighbor])
                if low[neighbor] > discovery[node]:
                    bridges.add(frozenset((node, neighbor)))
            elif parent.get(node) != neighbor:
                low[node] = min(low[node], discovery[neighbor])

    for node in adjacency:
        if node not in discovery:
            parent[node] = None
            visit(node)
    return bridges


def _components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    remaining = set(adjacency)
    groups: list[set[str]] = []
    while remaining:
        root = remaining.pop()
        group = {root}
        stack = [root]
        while stack:
            node = stack.pop()
            for neighbor in adjacency.get(node, set()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    group.add(neighbor)
                    stack.append(neighbor)
        groups.append(group)
    return groups


def _gf2_insert(vector: int, pivots: dict[int, int]) -> None:
    value = int(vector)
    while value:
        pivot = value.bit_length() - 1
        if pivot in pivots:
            value ^= pivots[pivot]
        else:
            pivots[pivot] = value
            return


def _four_cycle_span_rank_gf2(
    county_years: dict[str, set[str]],
    edge_positions: dict[tuple[str, str], int],
) -> int:
    """Rank of all supported 2x2 cycles over GF(2).

    Equality with the graph cycle rank shows that length-four cycles span the
    real/binary support-cycle space. It does not by itself prove connectivity
    of every bounded integer fiber, so exact finite-state and empirical
    movement diagnostics remain necessary.
    """

    pivots: dict[int, int] = {}
    counties = sorted(county_years)
    for left, right in combinations(counties, 2):
        shared = sorted(county_years[left] & county_years[right])
        for year_a, year_b in combinations(shared, 2):
            vector = 0
            for edge in [
                (left, year_a),
                (left, year_b),
                (right, year_a),
                (right, year_b),
            ]:
                vector ^= 1 << edge_positions[edge]
            _gf2_insert(vector, pivots)
    return len(pivots)


def _county_exact_flags(frame: pd.DataFrame) -> dict[str, bool]:
    county = frame.drop_duplicates("county_fips").copy()
    lower = pd.to_numeric(county["q001_period_lower"], errors="raise")
    upper = pd.to_numeric(county["q001_period_upper"], errors="raise")
    return dict(zip(county["county_fips"].astype(str), lower.eq(upper)))


def analyze_state_support(frame: pd.DataFrame) -> pd.DataFrame:
    lower = pd.to_numeric(frame["q002_lower"], errors="raise").to_numpy(dtype=int)
    upper = pd.to_numeric(frame["q002_upper"], errors="raise").to_numpy(dtype=int)
    free_mask = upper > lower
    exact_by_county = _county_exact_flags(frame)
    rows: list[dict[str, object]] = []

    for state_fips, state_frame in frame.groupby("state_fips", sort=True):
        state_indices = state_frame.index.to_numpy(dtype=int)
        free_indices = state_indices[free_mask[state_indices]]
        exact_indices = np.asarray(
            [index for index in free_indices if exact_by_county[str(frame.loc[index, "county_fips"])]],
            dtype=int,
        )
        interval_indices = np.asarray(
            [index for index in free_indices if not exact_by_county[str(frame.loc[index, "county_fips"])]],
            dtype=int,
        )

        adjacency: dict[str, set[str]] = {}
        edge_lookup: dict[frozenset[str], tuple[str, str]] = {}
        county_years: dict[str, set[str]] = {}
        for index in exact_indices:
            county = str(frame.loc[index, "county_fips"])
            year = str(frame.loc[index, "year"])
            county_node = f"c:{county}"
            year_node = f"y:{year}"
            adjacency.setdefault(county_node, set()).add(year_node)
            adjacency.setdefault(year_node, set()).add(county_node)
            edge_lookup[frozenset((county_node, year_node))] = (county, year)
            county_years.setdefault(county, set()).add(year)

        components = _components(adjacency) if adjacency else []
        edges = len(edge_lookup)
        vertices = len(adjacency)
        cycle_rank = max(edges - vertices + len(components), 0)
        bridge_set = _bridges(adjacency) if adjacency else set()
        cycle_edge_keys = set(edge_lookup) - bridge_set

        four_cycle_pairs: set[tuple[str, str]] = set()
        counties = sorted(county_years)
        for left, right in combinations(counties, 2):
            shared = county_years[left] & county_years[right]
            if len(shared) >= 2:
                for year in shared:
                    four_cycle_pairs.add((left, year))
                    four_cycle_pairs.add((right, year))
        four_cycle_keys = {key for key, pair in edge_lookup.items() if pair in four_cycle_pairs}
        long_cycle_keys = cycle_edge_keys - four_cycle_keys

        edge_positions = {pair: position for position, pair in enumerate(sorted(edge_lookup.values()))}
        four_cycle_span_rank = _four_cycle_span_rank_gf2(county_years, edge_positions) if edge_positions else 0
        unspanned_cycle_dimension = max(cycle_rank - four_cycle_span_rank, 0)

        cyclic_without_four = 0
        for component in components:
            component_edges = {key for key in edge_lookup if all(node in component for node in key)}
            component_rank = len(component_edges) - len(component) + 1
            if component_rank > 0 and not (component_edges & four_cycle_keys):
                cyclic_without_four += 1

        exact_counties = {str(frame.loc[index, "county_fips"]) for index in exact_indices}
        interval_counties = {str(frame.loc[index, "county_fips"]) for index in interval_indices}
        summary = StateSupportSummary(
            state_fips=str(state_fips),
            free_cells=int(len(free_indices)),
            exact_margin_free_cells=int(len(exact_indices)),
            interval_margin_free_cells=int(len(interval_indices)),
            exact_margin_counties=int(len(exact_counties)),
            interval_margin_counties=int(len(interval_counties)),
            exact_support_components=int(len(components)),
            exact_support_cycle_rank=int(cycle_rank),
            exact_support_cycle_edges=int(len(cycle_edge_keys)),
            exact_support_four_cycle_edges=int(len(four_cycle_keys)),
            exact_support_long_cycle_only_edges=int(len(long_cycle_keys)),
            exact_support_four_cycle_span_rank_gf2=int(four_cycle_span_rank),
            exact_support_unspanned_cycle_dimension_gf2=int(unspanned_cycle_dimension),
            cyclic_components_without_four_cycle=int(cyclic_without_four),
        )
        rows.append(summary.to_dict())
    return pd.DataFrame(rows)


def overall_support_summary(state_summary: pd.DataFrame) -> dict[str, int]:
    additive = [
        "free_cells",
        "exact_margin_free_cells",
        "interval_margin_free_cells",
        "exact_margin_counties",
        "interval_margin_counties",
        "exact_support_components",
        "exact_support_cycle_rank",
        "exact_support_cycle_edges",
        "exact_support_four_cycle_edges",
        "exact_support_long_cycle_only_edges",
        "exact_support_four_cycle_span_rank_gf2",
        "exact_support_unspanned_cycle_dimension_gf2",
        "cyclic_components_without_four_cycle",
    ]
    payload = {column: int(pd.to_numeric(state_summary[column], errors="raise").sum()) for column in additive}
    payload.update(
        {
            "states": int(len(state_summary)),
            "states_with_exact_support_cycles": int((state_summary["exact_support_cycle_rank"] > 0).sum()),
            "states_with_long_cycle_only_edges": int((state_summary["exact_support_long_cycle_only_edges"] > 0).sum()),
            "states_with_unspanned_four_cycle_dimension_gf2": int(
                (state_summary["exact_support_unspanned_cycle_dimension_gf2"] > 0).sum()
            ),
            "states_with_cyclic_component_without_four_cycle": int(
                (state_summary["cyclic_components_without_four_cycle"] > 0).sum()
            ),
        }
    )
    return payload
