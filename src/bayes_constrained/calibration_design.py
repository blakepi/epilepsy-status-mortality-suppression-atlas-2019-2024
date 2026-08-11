from __future__ import annotations

import numpy as np
import pandas as pd

from .data import RURAL_ORDER


def _evenly_spaced_rows(frame: pd.DataFrame, n: int) -> pd.DataFrame:
    if n <= 0 or frame.empty:
        return frame.iloc[0:0].copy()
    if len(frame) <= n:
        return frame.copy()
    positions = np.unique(np.rint(np.linspace(0, len(frame) - 1, n)).astype(int))
    return frame.iloc[positions].copy()


def select_state_clustered_panel(
    frame: pd.DataFrame,
    *,
    max_states: int = 6,
    counties_per_state: int = 12,
) -> pd.DataFrame:
    """Build a small complete panel without making state totals cell-identifying.

    States are ranked by rurality coverage and county count. Within each selected
    state, at least one county from every available rurality category is retained,
    and the remaining slots span the state population distribution. This keeps
    multiple counties in every selected state-year margin while preserving broad
    rurality and population variation.
    """

    required = {
        "county_fips",
        "state_fips",
        "year",
        "population",
        "primary_rurality",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Frame is missing calibration-design columns: {sorted(missing)}")

    county = (
        frame.groupby("county_fips", as_index=False)
        .agg(
            state_fips=("state_fips", "first"),
            primary_rurality=("primary_rurality", "first"),
            population=("population", "sum"),
        )
        .sort_values(["state_fips", "population", "county_fips"])
    )
    state_summary = (
        county.groupby("state_fips", as_index=False)
        .agg(
            county_count=("county_fips", "nunique"),
            rurality_count=("primary_rurality", "nunique"),
        )
        .sort_values(
            ["rurality_count", "county_count", "state_fips"],
            ascending=[False, False, True],
        )
    )
    eligible = state_summary[state_summary["county_count"] >= max(4, counties_per_state)].copy()
    if len(eligible) < max_states:
        raise ValueError(
            f"Only {len(eligible)} states contain at least {counties_per_state} counties."
        )
    selected_states = eligible.head(max_states)["state_fips"].astype(str).tolist()

    selected_counties: list[str] = []
    per_state_rows: list[dict[str, object]] = []
    for state in selected_states:
        group = county[county["state_fips"].astype(str).eq(state)].copy()
        group = group.sort_values(["population", "county_fips"]).reset_index(drop=True)
        chosen: list[str] = []
        for rurality in RURAL_ORDER:
            stratum = group[group["primary_rurality"].eq(rurality)].reset_index(drop=True)
            if stratum.empty:
                continue
            median_row = stratum.iloc[len(stratum) // 2]
            chosen.append(str(median_row["county_fips"]))
        remaining_slots = max(0, int(counties_per_state) - len(set(chosen)))
        remaining = group[~group["county_fips"].astype(str).isin(set(chosen))].copy()
        fill = _evenly_spaced_rows(remaining, remaining_slots)
        chosen.extend(fill["county_fips"].astype(str).tolist())
        chosen = list(dict.fromkeys(chosen))[:counties_per_state]
        if len(chosen) < counties_per_state:
            extras = group[~group["county_fips"].astype(str).isin(chosen)]
            chosen.extend(extras.head(counties_per_state - len(chosen))["county_fips"].astype(str))
        selected_counties.extend(chosen)
        state_selected = group[group["county_fips"].astype(str).isin(chosen)]
        per_state_rows.append(
            {
                "state_fips": state,
                "counties": int(state_selected["county_fips"].nunique()),
                "rurality_categories": int(state_selected["primary_rurality"].nunique()),
            }
        )

    out = frame[frame["county_fips"].astype(str).isin(selected_counties)].copy()
    out = out.sort_values(["state_fips", "county_fips", "year"]).reset_index(drop=True)
    expected_years = frame["year"].astype(str).nunique()
    if len(out) != out["county_fips"].nunique() * expected_years:
        raise ValueError("State-clustered calibration panel is not complete by county-year.")
    state_counts = out.drop_duplicates("county_fips").groupby("state_fips")["county_fips"].nunique()
    if (state_counts < 2).any():
        raise AssertionError("A selected state contains fewer than two calibration counties.")
    missing_ruralities = set(RURAL_ORDER) - set(out["primary_rurality"].astype(str).unique())
    if missing_ruralities:
        raise ValueError(f"Calibration panel lacks rurality categories: {sorted(missing_ruralities)}")
    out.attrs["calibration_selection"] = {
        "max_states": int(max_states),
        "counties_per_state": int(counties_per_state),
        "states": selected_states,
        "counties": int(out["county_fips"].nunique()),
        "county_year_rows": int(len(out)),
        "per_state": per_state_rows,
    }
    return out
