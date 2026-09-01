from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


Node = tuple[str, int]


@dataclass(frozen=True)
class IntervalPathSupport:
    endpoint_groups: list[np.ndarray]
    exact_path_rows: dict[tuple[int, int, int], np.ndarray]


def _components(adjacency: dict[Node, set[Node]]) -> tuple[dict[Node, int], list[set[Node]]]:
    component_by_node: dict[Node, int] = {}
    components: list[set[Node]] = []
    for root in sorted(adjacency):
        if root in component_by_node:
            continue
        component_id = len(components)
        members = {root}
        component_by_node[root] = component_id
        queue = deque([root])
        while queue:
            node = queue.popleft()
            for neighbor in sorted(adjacency.get(node, set())):
                if neighbor not in component_by_node:
                    component_by_node[neighbor] = component_id
                    members.add(neighbor)
                    queue.append(neighbor)
        components.append(members)
    return component_by_node, components


def _shortest_path(adjacency: dict[Node, set[Node]], start: Node, target: Node) -> list[Node] | None:
    if start == target:
        return [start]
    parent: dict[Node, Node | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in sorted(adjacency.get(node, set())):
            if neighbor in parent:
                continue
            parent[neighbor] = node
            if neighbor == target:
                path = [target]
                while path[-1] != start:
                    predecessor = parent[path[-1]]
                    if predecessor is None:
                        raise AssertionError("Broken shortest-path predecessor chain.")
                    path.append(predecessor)
                return list(reversed(path))
            queue.append(neighbor)
    return None


def build_interval_path_support(
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    county_code: np.ndarray,
    state_code: np.ndarray,
    year_code: np.ndarray,
    interval_counties: set[int],
    county_year_to_row: dict[tuple[int, int], int],
) -> IntervalPathSupport:
    """Build static alternating paths between interval-margin endpoints.

    Exact county-period rows are graph nodes connected to state-year nodes by
    free county-year cells. Interval-margin county cells act as half-edge
    endpoints. The reduced constraint matrix has both cycle circuits and path
    circuits joining pairs of interval endpoints in the same exact-support
    component. Same-year endpoint pairs are length-zero paths.
    """

    free = np.asarray(upper > lower, dtype=bool)
    endpoint_groups: list[np.ndarray] = []
    exact_path_rows: dict[tuple[int, int, int], np.ndarray] = {}

    for state in sorted(int(value) for value in np.unique(state_code)):
        state_rows = np.where(state_code == state)[0]
        interval_rows = np.asarray(
            [row for row in state_rows if free[row] and int(county_code[row]) in interval_counties],
            dtype=int,
        )
        if len(interval_rows) < 2:
            continue

        adjacency: dict[Node, set[Node]] = {}
        for row in interval_rows:
            adjacency.setdefault(("y", int(year_code[row])), set())
        exact_rows = np.asarray(
            [row for row in state_rows if free[row] and int(county_code[row]) not in interval_counties],
            dtype=int,
        )
        for row in exact_rows:
            county_node = ("c", int(county_code[row]))
            year_node = ("y", int(year_code[row]))
            adjacency.setdefault(county_node, set()).add(year_node)
            adjacency.setdefault(year_node, set()).add(county_node)

        component_by_node, components = _components(adjacency)
        rows_by_component: dict[int, list[int]] = {}
        for row in interval_rows:
            component_id = component_by_node[("y", int(year_code[row]))]
            rows_by_component.setdefault(component_id, []).append(int(row))
        for component_id, rows in sorted(rows_by_component.items()):
            if len(rows) >= 2:
                endpoint_groups.append(np.asarray(sorted(rows), dtype=int))

            endpoint_years = sorted({int(year_code[row]) for row in rows})
            component = components[component_id]
            for start_year in endpoint_years:
                for end_year in endpoint_years:
                    if start_year == end_year:
                        continue
                    node_path = _shortest_path(
                        adjacency,
                        ("y", start_year),
                        ("y", end_year),
                    )
                    if node_path is None:
                        continue
                    if node_path[0][0] != "y" or node_path[-1][0] != "y" or len(node_path) % 2 == 0:
                        raise AssertionError("Interval endpoint path must alternate year/county and end at a year.")
                    path_rows: list[int] = []
                    for left, right in zip(node_path[:-1], node_path[1:]):
                        county = left[1] if left[0] == "c" else right[1]
                        year = left[1] if left[0] == "y" else right[1]
                        row = county_year_to_row[(int(county), int(year))]
                        if not free[row] or int(county_code[row]) in interval_counties:
                            raise AssertionError("Canonical endpoint paths must use free exact-margin cells only.")
                        path_rows.append(int(row))
                    exact_path_rows[(state, start_year, end_year)] = np.asarray(path_rows, dtype=int)

    return IntervalPathSupport(
        endpoint_groups=endpoint_groups,
        exact_path_rows=exact_path_rows,
    )


def interval_path_direction(
    endpoint_a: int,
    endpoint_b: int,
    *,
    state_code: np.ndarray,
    year_code: np.ndarray,
    support: IntervalPathSupport,
) -> tuple[np.ndarray, np.ndarray] | None:
    state_a = int(state_code[endpoint_a])
    state_b = int(state_code[endpoint_b])
    if state_a != state_b:
        return None
    year_a = int(year_code[endpoint_a])
    year_b = int(year_code[endpoint_b])
    if year_a == year_b:
        return np.asarray([endpoint_a, endpoint_b], dtype=int), np.asarray([1, -1], dtype=int)
    path = support.exact_path_rows.get((state_a, year_a, year_b))
    if path is None or len(path) % 2 != 0:
        return None
    path_direction = np.where(np.arange(len(path)) % 2 == 0, -1, 1).astype(int)
    indices = np.concatenate(
        [
            np.asarray([endpoint_a], dtype=int),
            path,
            np.asarray([endpoint_b], dtype=int),
        ]
    )
    direction = np.concatenate(
        [
            np.asarray([1], dtype=int),
            path_direction,
            np.asarray([-1], dtype=int),
        ]
    )
    return indices, direction
