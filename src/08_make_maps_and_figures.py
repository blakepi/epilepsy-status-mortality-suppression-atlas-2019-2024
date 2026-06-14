from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch
from matplotlib.patches import Polygon

from utils import (
    MAP_DIR,
    PROCESSED_DIR,
    RAW_GEOGRAPHY_DIR,
    REPORT_DIR,
    TABLE_DIR,
    constrained_allocation,
    load_wonder,
    numeric,
    rel,
    safe_rate,
    write_text,
)


STATUS_COLORS = {
    "exact": "#1f4e79",
    "suppressed_1_9": "#d39c2f",
    "zero": "#b8bec6",
    "missing_unmatched": "#eeeeee",
    "priority_high": "#8c2d04",
    "not_priority": "#c9d7c5",
}


def load_features() -> list[dict]:
    path = RAW_GEOGRAPHY_DIR / "plotly_geojson_counties_fips.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    feats = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        fips = str(feat.get("id") or props.get("GEOID") or props.get("GEOID10") or props.get("FIPS") or "").zfill(5)
        if fips:
            feats.append({"fips": fips, "geometry": feat.get("geometry", {})})
    return feats


def patches_for_geometry(geom: dict) -> list[Polygon]:
    out = []
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        polys = [coords]
    elif gtype == "MultiPolygon":
        polys = coords
    else:
        return out
    for poly in polys:
        if not poly:
            continue
        ring = poly[0]
        try:
            out.append(Polygon(ring, closed=True))
        except Exception:
            continue
    return out


def draw_categorical(features: list[dict], values: dict[str, str], title: str, path: Path, legend_labels: dict[str, str]) -> None:
    patches = []
    colors = []
    for feat in features:
        status = values.get(feat["fips"], "missing_unmatched")
        for patch in patches_for_geometry(feat["geometry"]):
            patches.append(patch)
            colors.append(STATUS_COLORS.get(status, "#eeeeee"))
    fig, ax = plt.subplots(figsize=(11, 7))
    coll = PatchCollection(patches, facecolor=colors, edgecolor="#ffffff", linewidths=0.05)
    ax.add_collection(coll)
    ax.set_xlim(-125, -66)
    ax.set_ylim(24, 50)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)
    handles = [Patch(facecolor=STATUS_COLORS.get(k, "#eeeeee"), label=v) for k, v in legend_labels.items()]
    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=True)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def draw_continuous(features: list[dict], values: dict[str, float], title: str, path: Path, label: str, missing_color: str = "#e5e7eb") -> None:
    vals = pd.Series(values).dropna().astype(float)
    patches = []
    colors = []
    cmap = plt.get_cmap("YlOrRd")
    vmin = float(vals.quantile(0.05)) if len(vals) else 0.0
    vmax = float(vals.quantile(0.95)) if len(vals) else 1.0
    if vmin == vmax:
        vmax = vmin + 1
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    for feat in features:
        val = values.get(feat["fips"], np.nan)
        color = missing_color if pd.isna(val) else cmap(norm(float(val)))
        for patch in patches_for_geometry(feat["geometry"]):
            patches.append(patch)
            colors.append(color)
    fig, ax = plt.subplots(figsize=(11, 7))
    coll = PatchCollection(patches, facecolor=colors, edgecolor="#ffffff", linewidths=0.05)
    ax.add_collection(coll)
    ax.set_xlim(-125, -66)
    ax.set_ylim(24, 50)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.55, label=label)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main() -> None:
    features = load_features()
    county = pd.read_csv(PROCESSED_DIR / "county_period_analysis.csv", dtype={"county_fips": str})
    q014 = load_wonder("Q014")
    q015 = load_wonder("Q015")

    if not features:
        write_text(
            REPORT_DIR / "atlas_figure_report.md",
            "# Atlas Figure Report\n\nNo county geometry was available. Map-ready CSVs were produced where possible.",
        )
        return

    county["ct_geography_warning"] = county["county_fips"].str.startswith("09")
    county["observed_exact_rate_per_100k"] = np.where(
        county["death_status"].eq("exact"),
        safe_rate(county["deaths_exact"], county["model_exposure_person_years"]),
        np.nan,
    )
    exact_sum = pd.to_numeric(county.loc[county["death_status"].eq("exact"), "deaths_exact"], errors="coerce").sum()
    residual = 58380.0 - exact_sum
    supp = county["death_status"].eq("suppressed_1_9")
    allocation = constrained_allocation(
        pd.to_numeric(county.loc[supp, "model_exposure_person_years"], errors="coerce").fillna(1),
        residual,
        1,
        9,
    )
    county["residual_allocated_deaths"] = county["death_lower"]
    county.loc[supp, "residual_allocated_deaths"] = allocation
    county["residual_allocated_rate_per_100k"] = safe_rate(
        county["residual_allocated_deaths"], county["model_exposure_person_years"]
    )
    threshold = pd.to_numeric(county["residual_allocated_rate_per_100k"], errors="coerce").quantile(0.75)
    county["priority_status"] = np.where(
        county["primary_rurality"].astype(str).str.startswith("nonmetro")
        & county["svi_quartile"].eq("Q4_highest")
        & (pd.to_numeric(county["residual_allocated_rate_per_100k"], errors="coerce") >= threshold),
        "priority_high",
        "not_priority",
    )
    county.to_csv(TABLE_DIR / "map_ready_county_period.csv", index=False)

    status_map = county.set_index("county_fips")["death_status"].to_dict()
    draw_categorical(
        features,
        status_map,
        "County MCOD G40/G41 death-count status, 2019-2024",
        MAP_DIR / "map1_county_suppression_status.png",
        {"exact": "Exact", "suppressed_1_9": "Suppressed 1-9", "zero": "Explicit zero", "missing_unmatched": "Missing/unmatched"},
    )
    draw_continuous(
        features,
        county.set_index("county_fips")["observed_exact_rate_per_100k"].to_dict(),
        "Observed exact-county MCOD G40/G41 rate",
        MAP_DIR / "map2_observed_exact_county_rates.png",
        "Deaths per 100,000 person-years",
    )
    draw_continuous(
        features,
        county.set_index("county_fips")["residual_allocated_rate_per_100k"].to_dict(),
        "Suppression-aware residual-allocation county rate",
        MAP_DIR / "map3_suppression_aware_predicted_rates.png",
        "Deaths per 100,000 person-years",
    )
    draw_categorical(
        features,
        county.set_index("county_fips")["priority_status"].to_dict(),
        "Rural/high-SVI priority counties under residual allocation",
        MAP_DIR / "map4_rural_svi_priority.png",
        {"priority_high": "High priority", "not_priority": "Other", "missing_unmatched": "Missing/unmatched"},
    )

    q015_state = q015[q015["row_type"].eq("state")].copy()
    q015_state["state_fips"] = q015_state["state_fips"].astype(str).str.zfill(2)
    q015_state["deaths"] = numeric(q015_state["deaths"])
    q015_state["population"] = numeric(q015_state["population"])
    q015_state["state_rate"] = q015_state["deaths"] / q015_state["population"] * 100000
    state_rate = q015_state.set_index("state_fips")["state_rate"].to_dict()
    county["state_rate"] = county["county_fips"].str[:2].map(state_rate)
    draw_continuous(
        features,
        county.set_index("county_fips")["state_rate"].to_dict(),
        "State-period MCOD G40/G41 rate",
        MAP_DIR / "map5_state_period_rates.png",
        "Deaths per 100,000 person-years",
    )

    q014_county = q014[q014["row_type"].eq("county")].copy()
    q014_county["county_fips"] = q014_county["county_fips"].astype(str).str.zfill(5)
    draw_categorical(
        features,
        q014_county.set_index("county_fips")["death_count_status"].to_dict(),
        "County UCD G40/G41 death-count status, 2019-2024",
        MAP_DIR / "map6_ucd_suppression_status.png",
        {"exact": "Exact", "suppressed_1_9": "Suppressed 1-9", "zero": "Explicit zero", "missing_unmatched": "Missing/unmatched"},
    )

    q014_county.to_csv(TABLE_DIR / "map_ready_ucd_county_period.csv", index=False)

    report = f"""# Atlas Figure Report

Generated: 2026-06-13

## Maps Produced

- Map 1: `{rel(MAP_DIR / "map1_county_suppression_status.png")}`
- Map 2: `{rel(MAP_DIR / "map2_observed_exact_county_rates.png")}`
- Map 3: `{rel(MAP_DIR / "map3_suppression_aware_predicted_rates.png")}`
- Map 4: `{rel(MAP_DIR / "map4_rural_svi_priority.png")}`
- Map 5: `{rel(MAP_DIR / "map5_state_period_rates.png")}`
- Map 6: `{rel(MAP_DIR / "map6_ucd_suppression_status.png")}`

## Map-Ready Data

- County-period MCOD map data: `{rel(TABLE_DIR / "map_ready_county_period.csv")}`
- County-period UCD map data: `{rel(TABLE_DIR / "map_ready_ucd_county_period.csv")}`

## Geometry Source

Local Plotly county GeoJSON copied from the prior feasibility project:
`{rel(RAW_GEOGRAPHY_DIR / "plotly_geojson_counties_fips.json")}`.

## Caveats

- The static PNG viewport emphasizes the contiguous United States for legibility.
- Map-ready CSVs retain all copied county rows.
- Connecticut county/county-equivalent warnings from CDC WONDER are flagged in the map-ready data and not crosswalked away.
- Suppressed counties are explicitly marked or represented by interval-aware/residual-allocation values rather than omitted silently.
"""
    write_text(REPORT_DIR / "atlas_figure_report.md", report)
    print("Completed atlas maps.")


if __name__ == "__main__":
    main()
