from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import sparse


@dataclass(frozen=True)
class ConstraintGeometry:
    latent_variables: int
    nominal_state_year_equalities: int
    nominal_county_period_equalities: int
    nominal_national_year_equalities: int
    nominal_grand_total_equalities: int
    nonzero_reduced_equalities: int
    independent_equalities: int
    equality_nullity: int
    intrinsic_margin_dependencies: int
    algebraically_redundant_higher_level_equalities: int
    zero_information_equalities: int
    county_period_interval_constraints: int
    latent_cell_bound_constraints: int
    graph_components: int
    graph_components_without_interval_half_edge: int

    def to_dict(self) -> dict[str, int]:
        return {key: int(value) for key, value in asdict(self).items()}


class _DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.rank: dict[str, int] = {}

    def add(self, item: str) -> None:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        self.add(left)
        self.add(right)
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1


def _free_mask(frame: pd.DataFrame) -> np.ndarray:
    lower = pd.to_numeric(frame["q002_lower"], errors="raise").to_numpy(dtype=int)
    upper = pd.to_numeric(frame["q002_upper"], errors="raise").to_numpy(dtype=int)
    return upper > lower


def _county_period_is_equality(frame: pd.DataFrame) -> pd.Series:
    lower = pd.to_numeric(frame["q001_period_lower"], errors="raise")
    upper = pd.to_numeric(frame["q001_period_upper"], errors="raise")
    return lower.eq(upper)


def build_reduced_equality_matrix(
    frame: pd.DataFrame,
    *,
    include_redundant_higher_levels: bool = False,
) -> tuple[sparse.csr_matrix, pd.DataFrame, np.ndarray]:
    """Build equality constraints on free county-year latent cells only.

    Exact and zero county-year cells are subtracted from the right-hand sides;
    this function returns the coefficient matrix because rank and nullity do
    not depend on those residual targets. County-period rows are included only
    when their published lower and upper bounds are equal.
    """

    free_mask = _free_mask(frame)
    free_rows = np.flatnonzero(free_mask)
    free_column = {int(row): col for col, row in enumerate(free_rows)}
    row_entries: list[tuple[str, str, np.ndarray]] = []

    for (state, year), group in frame.groupby(["state_fips", "year"], sort=True):
        idx = np.asarray([free_column[int(i)] for i in group.index if int(i) in free_column], dtype=int)
        row_entries.append(("state_year", f"{state}:{year}", idx))

    period_equal = _county_period_is_equality(frame)
    for county, group in frame.groupby("county_fips", sort=True):
        first = int(group.index[0])
        if not bool(period_equal.loc[first]):
            continue
        idx = np.asarray([free_column[int(i)] for i in group.index if int(i) in free_column], dtype=int)
        row_entries.append(("county_period", str(county), idx))

    if include_redundant_higher_levels:
        for year, group in frame.groupby("year", sort=True):
            idx = np.asarray([free_column[int(i)] for i in group.index if int(i) in free_column], dtype=int)
            row_entries.append(("national_year", str(year), idx))
        row_entries.append(("grand_total", "all_years", np.arange(len(free_rows), dtype=int)))

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    metadata: list[dict[str, object]] = []
    for row_id, (kind, label, idx) in enumerate(row_entries):
        rows.extend([row_id] * len(idx))
        cols.extend(idx.tolist())
        data.extend([1.0] * len(idx))
        metadata.append({"row": row_id, "kind": kind, "label": label, "nonzero_columns": int(len(idx))})
    matrix = sparse.csr_matrix((data, (rows, cols)), shape=(len(row_entries), len(free_rows)))
    return matrix, pd.DataFrame(metadata), free_rows


def _graph_rank(frame: pd.DataFrame) -> tuple[int, int, int, int]:
    """Exact rank of the reduced state-year/county-period incidence matrix.

    Each free county-year cell is an edge between a state-year row and an
    exact county-period row. A cell belonging to an interval-constrained
    county is a half-edge incident only to its state-year row. Multiplying one
    bipartite row partition by -1 converts the two-ended columns to an oriented
    incidence matrix. A component without a half-edge contributes one linear
    dependency; a component with a half-edge has full row rank.
    """

    free_mask = _free_mask(frame)
    period_equal = _county_period_is_equality(frame)
    dsu = _DisjointSet()
    half_edge_nodes: set[str] = set()
    active_nodes: set[str] = set()

    for row_index in np.flatnonzero(free_mask):
        row = frame.iloc[int(row_index)]
        sy_node = f"state_year:{row['state_fips']}:{row['year']}"
        dsu.add(sy_node)
        active_nodes.add(sy_node)
        if bool(period_equal.iloc[int(row_index)]):
            county_node = f"county_period:{row['county_fips']}"
            dsu.add(county_node)
            active_nodes.add(county_node)
            dsu.union(sy_node, county_node)
        else:
            half_edge_nodes.add(sy_node)

    components: dict[str, set[str]] = {}
    for node in active_nodes:
        root = dsu.find(node)
        components.setdefault(root, set()).add(node)

    components_with_half_edge = 0
    components_without_half_edge = 0
    rank = 0
    for nodes in components.values():
        has_half_edge = any(node in half_edge_nodes for node in nodes)
        if has_half_edge:
            components_with_half_edge += 1
            rank += len(nodes)
        else:
            components_without_half_edge += 1
            rank += max(len(nodes) - 1, 0)
    return rank, len(components), components_with_half_edge, components_without_half_edge


def analyze_constraint_geometry(frame: pd.DataFrame) -> ConstraintGeometry:
    free_mask = _free_mask(frame)
    latent_variables = int(free_mask.sum())
    county_first = frame.drop_duplicates("county_fips")
    period_equal = pd.to_numeric(county_first["q001_period_lower"], errors="raise").eq(
        pd.to_numeric(county_first["q001_period_upper"], errors="raise")
    )

    state_year_count = int(frame[["state_fips", "year"]].drop_duplicates().shape[0])
    county_equality_count = int(period_equal.sum())
    national_year_count = int(frame["year"].nunique())
    grand_total_count = 1

    _, metadata, _ = build_reduced_equality_matrix(frame, include_redundant_higher_levels=False)
    nonzero_rows = int((metadata["nonzero_columns"] > 0).sum()) if not metadata.empty else 0
    zero_rows = int(len(metadata) - nonzero_rows)
    rank, components, _, components_without_half_edge = _graph_rank(frame)

    # National-year rows are sums of state-year rows over the same modeled
    # universe; the grand total is their sum. They are retained as validation
    # checks but add no rank to the reduced latent-cell system.
    higher_level_redundant = national_year_count + grand_total_count
    intrinsic_dependencies = max(nonzero_rows - rank, 0)

    interval_counties = int((~period_equal).sum())
    return ConstraintGeometry(
        latent_variables=latent_variables,
        nominal_state_year_equalities=state_year_count,
        nominal_county_period_equalities=county_equality_count,
        nominal_national_year_equalities=national_year_count,
        nominal_grand_total_equalities=grand_total_count,
        nonzero_reduced_equalities=nonzero_rows,
        independent_equalities=int(rank),
        equality_nullity=int(latent_variables - rank),
        intrinsic_margin_dependencies=int(intrinsic_dependencies),
        algebraically_redundant_higher_level_equalities=int(higher_level_redundant),
        zero_information_equalities=int(zero_rows),
        county_period_interval_constraints=interval_counties,
        latent_cell_bound_constraints=latent_variables,
        graph_components=int(components),
        graph_components_without_interval_half_edge=int(components_without_half_edge),
    )


def geometry_markdown(geometry: ConstraintGeometry) -> str:
    rows: Iterable[tuple[str, int]] = geometry.to_dict().items()
    lines = [
        "# Constraint geometry and identifiability",
        "",
        "The rank is computed on free county-year latent cells after fixed exact and zero cells are removed. National-year and grand-total rows are treated as reconciliation checks because they are algebraic sums of the state-year rows over the same modeled universe.",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
    ]
    for key, value in rows:
        lines.append(f"| {key.replace('_', ' ')} | {value:,} |")
    lines.extend(
        [
            "",
            "The equality nullity is the affine dimension before cell bounds and county-period interval inequalities are applied. It therefore measures residual freedom under independent public equalities, not the number of posterior-identifiable individual counts.",
        ]
    )
    return "\n".join(lines) + "\n"
