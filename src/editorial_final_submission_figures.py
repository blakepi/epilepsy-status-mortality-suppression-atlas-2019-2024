from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch, Polygon


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT_ROOT / "manuscript" / "final_submission_ready"
GEOMETRY_PATH = PROJECT_ROOT / "data" / "raw" / "geography" / "plotly_geojson_counties_fips.json"
COUNTY_PERIOD = PROJECT_ROOT / "data" / "processed" / "county_period_analysis.csv"
MAP_READY = PROJECT_ROOT / "tables" / "map_ready_county_period.csv"

X_LIM = (-125, -66)
Y_LIM = (24, 50)

STATUS_COLORS = {
    "exact": "#3B73B9",
    "suppressed_1_9": "#DDAA33",
    "zero": "#C9CED6",
    "missing_unmatched": "#F2F3F5",
}

RATE_COLORS = {
    "<2": "#EEF5F2",
    "2-3": "#CDE3DB",
    "3-4": "#93C7B6",
    "4-5": "#4F9E91",
    ">=5": "#1F6F78",
}


def load_features() -> list[dict]:
    data = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    features: list[dict] = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        fips = str(
            feat.get("id")
            or props.get("GEOID")
            or props.get("GEOID10")
            or props.get("FIPS")
            or props.get("GEO_ID", "")[-5:]
            or ""
        ).zfill(5)
        if fips:
            features.append({"fips": fips, "geometry": feat.get("geometry", {})})
    return features


def patches_for_geometry(geom: dict) -> list[Polygon]:
    patches: list[Polygon] = []
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        polys = [coords]
    elif gtype == "MultiPolygon":
        polys = coords
    else:
        return patches
    for poly in polys:
        if not poly:
            continue
        ring = poly[0]
        try:
            patches.append(Polygon(ring, closed=True))
        except Exception:
            continue
    return patches


def add_collection(
    ax,
    features: list[dict],
    color_by_fips: dict[str, str],
    default_color: str = "#F4F5F7",
    linewidth: float = 0.045,
) -> None:
    patches: list[Polygon] = []
    colors: list[str] = []
    for feat in features:
        color = color_by_fips.get(feat["fips"], default_color)
        for patch in patches_for_geometry(feat["geometry"]):
            patches.append(patch)
            colors.append(color)
    collection = PatchCollection(
        patches,
        facecolor=colors,
        edgecolor="#FFFFFF",
        linewidths=linewidth,
        zorder=2,
    )
    ax.add_collection(collection)


def add_missing_overlay(ax, features: list[dict], missing_fips: set[str]) -> None:
    patches: list[Polygon] = []
    for feat in features:
        if feat["fips"] not in missing_fips:
            continue
        patches.extend(patches_for_geometry(feat["geometry"]))
    if not patches:
        return
    overlay = PatchCollection(
        patches,
        facecolor="none",
        edgecolor="#222831",
        linewidths=0.34,
        hatch="///",
        zorder=5,
    )
    ax.add_collection(overlay)


def prep_axis(ax) -> None:
    ax.set_xlim(*X_LIM)
    ax.set_ylim(*Y_LIM)
    ax.set_aspect("equal")
    ax.axis("off")


def save_figure(fig, fig_dir: Path, stem: str) -> dict[str, str]:
    paths = {
        "png": fig_dir / f"{stem}.png",
        "svg": fig_dir / f"{stem}.svg",
        "pdf": fig_dir / f"{stem}.pdf",
    }
    fig.savefig(paths["png"], dpi=360, bbox_inches="tight", facecolor="white")
    fig.savefig(paths["svg"], bbox_inches="tight", facecolor="white")
    fig.savefig(paths["pdf"], bbox_inches="tight", facecolor="white")
    return {key: str(value) for key, value in paths.items()}


def load_county_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    county = pd.read_csv(COUNTY_PERIOD, dtype={"county_fips": str})
    map_ready = pd.read_csv(MAP_READY, dtype={"county_fips": str})
    county["county_fips"] = county["county_fips"].astype(str).str.zfill(5)
    map_ready["county_fips"] = map_ready["county_fips"].astype(str).str.zfill(5)
    return county, map_ready


def missing_covariate_fips(county: pd.DataFrame) -> set[str]:
    covariate_cols = [c for c in ["primary_rurality", "svi_quartile", "acs_pct_age_65_plus"] if c in county.columns]
    if not covariate_cols:
        return set()
    missing = county[covariate_cols].isna().any(axis=1)
    return set(county.loc[missing, "county_fips"])


def figure1(features: list[dict], county: pd.DataFrame, fig_dir: Path) -> tuple[dict[str, str], dict[str, int]]:
    status_counts = county["death_status"].value_counts().to_dict()
    missing_fips = missing_covariate_fips(county)
    colors = county.set_index("county_fips")["death_status"].map(STATUS_COLORS).to_dict()

    fig, ax = plt.subplots(figsize=(11.6, 7.2))
    add_collection(ax, features, colors)
    add_missing_overlay(ax, features, missing_fips)
    prep_axis(ax)

    fig.text(
        0.055,
        0.955,
        "County data visibility for multiple-cause G40/G41 mortality, 2019-2024",
        ha="left",
        va="top",
        fontsize=15,
        fontweight="bold",
        color="#111827",
    )
    fig.text(
        0.055,
        0.925,
        "Suppressed counties are known positive deaths, not zero-death counties.",
        ha="left",
        va="top",
        fontsize=10.5,
        color="#374151",
    )
    handles = [
        Patch(facecolor=STATUS_COLORS["exact"], edgecolor="#FFFFFF", label=f"Exact count (n={status_counts.get('exact', 0):,})"),
        Patch(
            facecolor=STATUS_COLORS["suppressed_1_9"],
            edgecolor="#FFFFFF",
            label=f"Suppressed positive count, 1-9 deaths (n={status_counts.get('suppressed_1_9', 0):,})",
        ),
        Patch(facecolor=STATUS_COLORS["zero"], edgecolor="#FFFFFF", label=f"Explicit zero (n={status_counts.get('zero', 0):,})"),
        Patch(facecolor="white", edgecolor="#222831", hatch="///", label=f"Unmatched/missing covariates overlay (n={len(missing_fips):,})"),
    ]
    legend = ax.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.01, 0.02),
        frameon=True,
        framealpha=0.97,
        facecolor="white",
        edgecolor="#D1D5DB",
        fontsize=8.6,
    )
    legend.get_frame().set_linewidth(0.8)
    fig.text(
        0.055,
        0.06,
        "Contiguous U.S. shown; Alaska/Hawaii retained in analytic files where present but not shown.",
        ha="left",
        va="bottom",
        fontsize=8.6,
        color="#4B5563",
    )
    fig.subplots_adjust(left=0.02, right=0.99, top=0.89, bottom=0.02)
    paths = save_figure(fig, fig_dir, "figure1_county_data_visibility")
    save_figure(fig, fig_dir, "figure1_county_suppression_status_revised")
    plt.close(fig)
    counts = {
        "exact": int(status_counts.get("exact", 0)),
        "suppressed_1_9": int(status_counts.get("suppressed_1_9", 0)),
        "zero": int(status_counts.get("zero", 0)),
        "missing_covariates_overlay": int(len(missing_fips)),
    }
    return paths, counts


def rate_bin(rate: float) -> str | float:
    if pd.isna(rate):
        return np.nan
    if rate < 2:
        return "<2"
    if rate < 3:
        return "2-3"
    if rate < 4:
        return "3-4"
    if rate < 5:
        return "4-5"
    return ">=5"


def figure3(features: list[dict], county: pd.DataFrame, map_ready: pd.DataFrame, fig_dir: Path) -> tuple[dict[str, str], dict[str, int]]:
    merged = county[["county_fips", "death_status"]].merge(
        map_ready[["county_fips", "residual_allocated_rate_per_100k"]],
        on="county_fips",
        how="left",
    )
    merged["rate_bin"] = merged["residual_allocated_rate_per_100k"].map(rate_bin)
    rate_colors = merged.set_index("county_fips")["rate_bin"].map(RATE_COLORS).to_dict()
    status_colors = merged.set_index("county_fips")["death_status"].map(STATUS_COLORS).to_dict()

    fig, axes = plt.subplots(1, 2, figsize=(14.4, 6.7))
    add_collection(axes[0], features, rate_colors)
    prep_axis(axes[0])
    axes[0].text(0.0, 1.015, "A. Population-scaled residual allocation", transform=axes[0].transAxes, fontsize=11, fontweight="bold")
    axes[0].text(0.0, 0.975, "Deaths per 100,000 person-years, binned", transform=axes[0].transAxes, fontsize=9, color="#4B5563")

    add_collection(axes[1], features, status_colors)
    add_missing_overlay(axes[1], features, missing_covariate_fips(county))
    prep_axis(axes[1])
    axes[1].text(0.0, 1.015, "B. Data visibility behind the allocation", transform=axes[1].transAxes, fontsize=11, fontweight="bold")
    axes[1].text(0.0, 0.975, "Exact, suppressed positive, and explicit-zero counties", transform=axes[1].transAxes, fontsize=9, color="#4B5563")

    fig.text(
        0.045,
        0.965,
        "Illustrative residual allocation and county data visibility",
        ha="left",
        va="top",
        fontsize=15,
        fontweight="bold",
        color="#111827",
    )
    fig.text(
        0.045,
        0.93,
        "Panel A maps one total-preserving allocation scenario; Panel B shows where county counts were visible or hidden.",
        ha="left",
        va="top",
        fontsize=10.5,
        color="#374151",
    )

    rate_handles = [Patch(facecolor=RATE_COLORS[label], edgecolor="#FFFFFF", label=label) for label in ["<2", "2-3", "3-4", "4-5", ">=5"]]
    axes[0].legend(
        handles=rate_handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 0.01),
        frameon=True,
        framealpha=0.97,
        facecolor="white",
        edgecolor="#D1D5DB",
        fontsize=8.5,
        title="Rate bin",
        title_fontsize=9,
    )
    status_handles = [
        Patch(facecolor=STATUS_COLORS["exact"], edgecolor="#FFFFFF", label="Exact"),
        Patch(facecolor=STATUS_COLORS["suppressed_1_9"], edgecolor="#FFFFFF", label="Suppressed positive 1-9"),
        Patch(facecolor=STATUS_COLORS["zero"], edgecolor="#FFFFFF", label="Explicit zero"),
        Patch(facecolor="white", edgecolor="#222831", hatch="///", label="Missing covariates overlay"),
    ]
    axes[1].legend(
        handles=status_handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 0.01),
        frameon=True,
        framealpha=0.97,
        facecolor="white",
        edgecolor="#D1D5DB",
        fontsize=8.5,
    )
    fig.text(
        0.045,
        0.045,
        "This map shows one total-preserving allocation scenario and should not be interpreted as recovered true county rates.",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#374151",
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.025, right=0.99, top=0.88, bottom=0.09, wspace=0.03)
    paths = save_figure(fig, fig_dir, "figure3_allocation_uncertainty_atlas")
    save_figure(fig, fig_dir, "figure3_suppression_aware_residual_rate")
    plt.close(fig)
    bin_counts = {label: int((merged["rate_bin"] == label).sum()) for label in ["<2", "2-3", "3-4", "4-5", ">=5"]}
    return paths, bin_counts


def write_report(report_dir: Path, counts: dict[str, int], bins: dict[str, int], figure_paths: dict[str, dict[str, str]], feature_count: int) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    report = f"""# Final Map Figure Report

## Geometry

- Local geometry file: `{GEOMETRY_PATH}`
- Feature count: {feature_count:,}
- Geometry note: the repository stores a local Plotly county GeoJSON with county FIPS-compatible identifiers. It does not retain a separate TIGER/Line or cartographic-boundary vintage identifier for this copied geometry source.

## Figure 1 Counts

- Exact count: {counts['exact']:,}
- Suppressed positive count, 1-9 deaths: {counts['suppressed_1_9']:,}
- Explicit zero: {counts['zero']:,}
- Unmatched/missing covariates overlay: {counts['missing_covariates_overlay']:,}

These match the Table 1 death-status counts for exact, suppressed, and explicit-zero counties; the unmatched/missing covariate count is shown as a hatch overlay rather than a mutually exclusive death-status category.

## Figure 3 Rate Bins

- <2 deaths per 100,000 person-years: {bins['<2']:,}
- 2-3 deaths per 100,000 person-years: {bins['2-3']:,}
- 3-4 deaths per 100,000 person-years: {bins['3-4']:,}
- 4-5 deaths per 100,000 person-years: {bins['4-5']:,}
- >=5 deaths per 100,000 person-years: {bins['>=5']:,}

Figure 3 uses a discrete, calm colorblind-safe palette and pairs the population-scaled residual-allocation rate panel with the underlying data-visibility panel. It is explicitly labeled as illustrative, not a recovered true county-rate map.

## Outputs

"""
    for label, paths in figure_paths.items():
        report += f"### {label}\n\n"
        for fmt, path in paths.items():
            report += f"- {fmt.upper()}: `{path}`\n"
        report += "\n"
    (report_dir / "final_map_figure_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    fig_dir = out_dir / "figures"
    report_dir = out_dir / "reports"
    fig_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    features = load_features()
    county, map_ready = load_county_data()
    fig1_paths, fig1_counts = figure1(features, county, fig_dir)
    fig3_paths, fig3_bins = figure3(features, county, map_ready, fig_dir)
    write_report(
        report_dir,
        fig1_counts,
        fig3_bins,
        {"Figure 1 data visibility": fig1_paths, "Figure 3 allocation atlas": fig3_paths},
        len(features),
    )
    print(f"figure_dir={fig_dir}")
    print(f"figure1_counts={json.dumps(fig1_counts, sort_keys=True)}")
    print(f"figure3_bins={json.dumps(fig3_bins, sort_keys=True)}")


if __name__ == "__main__":
    main()
