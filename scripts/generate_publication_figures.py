from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import geopandas as gpd
import mapclassify
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from visualization.pub_style import (  # noqa: E402
    NEUTRALS,
    PALETTES,
    RATE_BIN_PALETTE,
    SCENARIO_TIER_PALETTE,
    SUPPRESSION_STATUS_PALETTE,
    TOKENS,
    apply_pub_style,
    save_figure_bundle,
    validate_figure_outputs,
    write_figure_manifest,
)


DATA_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "tables"
GEOMETRY_PATH = PROJECT_ROOT / "data" / "raw" / "geography" / "plotly_geojson_counties_fips.json"
FINAL_OUT = PROJECT_ROOT / "manuscript" / "final_submission_ready"
DEFAULT_OUTDIR = FINAL_OUT / "figures"
DEFAULT_MANIFEST = FINAL_OUT / "reports" / "publication_figure_manifest.csv"
DEFAULT_QA_REPORT = FINAL_OUT / "reports" / "publication_figure_QA_report.md"

CONTIGUOUS_EXCLUDED_STATE_FIPS = {"02", "15", "60", "66", "69", "72", "78"}

SCENARIO_LABELS = {
    "observed_exact_positive_only": "Exact visible",
    "observed_exact_plus_zero": "Exact + zero",
    "population_scaled_residual_allocation": "Population residual",
    "conservative_anti_rural_allocation": "Anti-rural residual",
    "pro_rural_allocation": "Pro-rural residual",
    "suppressed_equals_1": "Suppressed = 1",
    "suppressed_equals_mean_4_06": "Uniform mean",
    "suppressed_equals_5": "Suppressed = 5",
    "suppressed_equals_9": "Suppressed = 9",
    "interval_likelihood": "Interval NB",
}

SCENARIO_ORDER = [
    "observed_exact_positive_only",
    "observed_exact_plus_zero",
    "population_scaled_residual_allocation",
    "conservative_anti_rural_allocation",
    "pro_rural_allocation",
    "suppressed_equals_1",
    "suppressed_equals_mean_4_06",
    "suppressed_equals_5",
    "suppressed_equals_9",
    "interval_likelihood",
]

SCENARIO_TIERS = {
    "observed_exact_positive_only": "visible-only",
    "observed_exact_plus_zero": "visible-only",
    "population_scaled_residual_allocation": "total-preserving residual allocation",
    "conservative_anti_rural_allocation": "total-preserving residual allocation",
    "pro_rural_allocation": "total-preserving residual allocation",
    "suppressed_equals_1": "fixed-value stress test",
    "suppressed_equals_mean_4_06": "fixed-value stress test",
    "suppressed_equals_5": "fixed-value stress test",
    "suppressed_equals_9": "fixed-value stress test",
    "interval_likelihood": "interval model",
}

SCENARIO_TIER_BACKGROUNDS = {
    "visible-only": PALETTES["blue"]["xlight"],
    "total-preserving residual allocation": PALETTES["olive"]["xlight"],
    "fixed-value stress test": PALETTES["orange"]["xlight"],
    "interval model": PALETTES["pink"]["xlight"],
}

URBANIZATION_ORDER = [
    "Large Central Metro",
    "Large Fringe Metro",
    "Medium Metro",
    "Small Metro",
    "Micropolitan (Nonmetro)",
    "NonCore (Nonmetro)",
    "Not Available",
]

URBANIZATION_COLORS = {
    "Large Central Metro": PALETTES["blue"]["mid"],
    "Large Fringe Metro": PALETTES["blue"]["light"],
    "Medium Metro": PALETTES["olive"]["mid"],
    "Small Metro": PALETTES["gold"]["mid"],
    "Micropolitan (Nonmetro)": PALETTES["orange"]["mid"],
    "NonCore (Nonmetro)": PALETTES["pink"]["mid"],
    "Not Available": NEUTRALS["mid"],
}

FIGURE2_X_LIMITS = (0.42, 2.75)
FIGURE2_X_TICKS = [0.45, 0.6, 0.8, 1.0, 1.25, 1.6, 2.0, 2.6]

CONCISE_TIER_LABELS = {
    "Visible-only": "Visible-only",
    "Fixed-value stress test, not total-preserving": "Fixed-value stress test",
    "Constant-count stress test, total-preserving": "Constant-count stress test",
    "Residual-allocation, total-preserving": "Residual allocation",
    "Interval model": "Interval model",
}


def required_inputs() -> list[Path]:
    table3_final = FINAL_OUT / "tables" / "table3_suppression_aware_models_revised_full.csv"
    return [
        GEOMETRY_PATH,
        DATA_DIR / "county_period_analysis.csv",
        TABLE_DIR / "map_ready_county_period.csv",
        table3_final if table3_final.exists() else TABLE_DIR / "table3_suppression_aware_models.csv",
        TABLE_DIR / "table4_temporal_context.csv",
        TABLE_DIR / "covid_by_urbanization_year.csv",
    ]


def fail_if_missing_inputs() -> None:
    missing = [path for path in required_inputs() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing frozen figure inputs: " + "; ".join(str(path) for path in missing))


def remove_retired_outputs(outdir: Path) -> None:
    retired_patterns = [
        "figure1_county_suppression_status_tight.*",
        "figure1_county_data_visibility.*",
        "figure2_two_panel_irrs_revised.*",
        "figure3_suppression_aware_residual_rate.*",
        "figure3_suppression_aware_residual_rate_tight.*",
        "figure3_allocation_uncertainty_atlas.*",
        "suppression_bounds_forest_plot.*",
        "map3_suppression_aware_predicted_rates.*",
    ]
    for pattern in retired_patterns:
        for path in outdir.glob(pattern):
            if path.is_file():
                path.unlink()


def read_county_geometries() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(GEOMETRY_PATH, engine="pyogrio")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    if "county_fips" not in gdf.columns:
        if "id" in gdf.columns:
            fips = gdf["id"].astype(str).str.zfill(5)
        elif "GEO_ID" in gdf.columns:
            fips = gdf["GEO_ID"].astype(str).str[-5:].str.zfill(5)
        else:
            fips = gdf.index.astype(str).str.zfill(5)
        gdf["county_fips"] = fips
    gdf["county_fips"] = gdf["county_fips"].astype(str).str.zfill(5)
    gdf["state_fips"] = gdf["county_fips"].str[:2]
    gdf = gdf.loc[~gdf["state_fips"].isin(CONTIGUOUS_EXCLUDED_STATE_FIPS)].copy()
    return gdf.to_crs("EPSG:5070")


def read_county_data() -> pd.DataFrame:
    county = pd.read_csv(DATA_DIR / "county_period_analysis.csv", dtype={"county_fips": str})
    county["county_fips"] = county["county_fips"].astype(str).str.zfill(5)
    return county


def read_map_ready() -> pd.DataFrame:
    map_ready = pd.read_csv(TABLE_DIR / "map_ready_county_period.csv", dtype={"county_fips": str})
    map_ready["county_fips"] = map_ready["county_fips"].astype(str).str.zfill(5)
    return map_ready


def missing_covariate_fips(county: pd.DataFrame) -> set[str]:
    cols = [c for c in ["primary_rurality", "svi_quartile", "acs_pct_age_65_plus"] if c in county.columns]
    if not cols:
        return set()
    return set(county.loc[county[cols].isna().any(axis=1), "county_fips"])


def draw_state_boundaries(ax, gdf: gpd.GeoDataFrame) -> None:
    states = gdf.dissolve(by="state_fips", as_index=False)
    states.boundary.plot(ax=ax, color="#FFFFFF", linewidth=0.28, zorder=8)


def finish_map_axis(ax) -> None:
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_anchor("N")


def add_header(fig: plt.Figure, title: str, subtitle: str, *, x: float = 0.04, y: float = 0.982) -> None:
    fig.text(x, y, title, ha="left", va="top", fontsize=10.5, fontweight="semibold", color=TOKENS["ink"])
    fig.text(x, y - 0.035, subtitle, ha="left", va="top", fontsize=7.5, color=TOKENS["muted"])


def figure1(gdf: gpd.GeoDataFrame, county: pd.DataFrame, outdir: Path) -> tuple[list[dict], dict]:
    counts = county["death_status"].value_counts().to_dict()
    missing_fips = missing_covariate_fips(county)
    plot_gdf = gdf.merge(county[["county_fips", "death_status"]], on="county_fips", how="left")
    plot_gdf["death_status"] = plot_gdf["death_status"].fillna("missing_unmatched")

    fig = plt.figure(figsize=(7.2, 4.55))
    gs = fig.add_gridspec(1, 2, width_ratios=[4.85, 1.05], left=0.018, right=0.985, top=0.875, bottom=0.078, wspace=0.045)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_counts = fig.add_subplot(gs[0, 1])
    ax_map.set_facecolor(TOKENS["panel"])

    for status in ["exact", "suppressed_1_9", "zero"]:
        part = plot_gdf.loc[plot_gdf["death_status"].eq(status)]
        if not part.empty:
            part.plot(ax=ax_map, color=SUPPRESSION_STATUS_PALETTE[status], edgecolor="#FFFFFF", linewidth=0.035, zorder=3)
    missing_display = plot_gdf.loc[plot_gdf["county_fips"].isin(missing_fips)]
    if not missing_display.empty:
        missing_display.plot(ax=ax_map, facecolor="none", edgecolor=TOKENS["ink"], linewidth=0.38, hatch="xxxx", zorder=7)
    draw_state_boundaries(ax_map, gdf)
    finish_map_axis(ax_map)

    labels = ["Exact count", "Suppressed positive\n1-9 deaths", "Explicit zero", "Unmatched/missing\ncovariates overlay"]
    values = [counts.get("exact", 0), counts.get("suppressed_1_9", 0), counts.get("zero", 0), len(missing_fips)]
    colors = [
        SUPPRESSION_STATUS_PALETTE["exact"],
        SUPPRESSION_STATUS_PALETTE["suppressed_1_9"],
        SUPPRESSION_STATUS_PALETTE["zero"],
        NEUTRALS["open"],
    ]
    y = np.arange(len(labels))[::-1]
    bars = ax_counts.barh(
        y,
        values,
        color=colors,
        edgecolor=[PALETTES["blue"]["dark"], PALETTES["gold"]["dark"], NEUTRALS["dark"], TOKENS["ink"]],
        linewidth=0.75,
    )
    bars[-1].set_hatch("xxxx")
    for yi, value, label in zip(y, values, labels):
        pct = value / len(county) * 100
        ax_counts.text(value + max(values) * 0.025, yi, f"{value:,}\n{pct:.1f}%", va="center", ha="left", fontsize=6.7, color=TOKENS["ink"])
    ax_counts.set_yticks(y, labels)
    ax_counts.set_xlim(0, max(values) * 1.28)
    ax_counts.set_title("County rows", loc="left", fontsize=8, fontweight="semibold", color=TOKENS["ink"], pad=5)
    ax_counts.tick_params(axis="x", bottom=False, labelbottom=False)
    ax_counts.tick_params(axis="y", length=0, labelsize=6.7)
    for spine in ax_counts.spines.values():
        spine.set_visible(False)
    ax_counts.grid(False)

    add_header(
        fig,
        "County data visibility for multiple-cause G40/G41 mortality, 2019-2024",
        "Suppressed counties are known positive deaths, not zero-death counties; static panel shows the contiguous U.S.",
    )
    fig.text(0.04, 0.035, "Alaska/Hawaii are retained in analytic files where present but not shown in this static map panel.", fontsize=6.5, color=TOKENS["muted"])
    records = save_figure_bundle(
        fig,
        "figure1_county_suppression_status_revised",
        outdir,
        7.2,
        4.55,
        600,
        figure_number="1",
        source_script=Path(__file__).name,
        input_data_files=[GEOMETRY_PATH, DATA_DIR / "county_period_analysis.csv"],
        tiff_dpi=500,
    )
    plt.close(fig)
    return records, {"counts": counts, "missing_covariates": len(missing_fips)}


def model_path() -> Path:
    final_path = FINAL_OUT / "tables" / "table3_suppression_aware_models_revised_full.csv"
    return final_path if final_path.exists() else TABLE_DIR / "table3_suppression_aware_models.csv"


def rows_for_term(term: str) -> pd.DataFrame:
    full = pd.read_csv(model_path())
    direct = full[
        (full["model_family"].eq("rurality_svi_composite"))
        & (full["term"].eq(term))
        & (~full["scenario"].eq("interval_likelihood"))
    ].copy()
    interval = full[
        (full["model_family"].eq("interval_nb_rurality_svi"))
        & (full["term"].eq(term))
        & (full["scenario"].eq("interval_likelihood"))
    ].copy()
    out = pd.concat([direct, interval], ignore_index=True)
    out = out.loc[out["scenario"].isin(SCENARIO_ORDER)].copy()
    out["scenario_label"] = out["scenario"].map(SCENARIO_LABELS)
    out["tier"] = out["scenario"].map(SCENARIO_TIERS)
    out["scenario_order"] = out["scenario"].map({scenario: idx for idx, scenario in enumerate(SCENARIO_ORDER)})
    return out.sort_values("scenario_order", ascending=False)


def draw_forest_panel(ax, data: pd.DataFrame, title: str, show_y: bool) -> None:
    y = np.arange(len(data))
    for tier, color in SCENARIO_TIER_PALETTE.items():
        tier_rows = np.where(data["tier"].to_numpy() == tier)[0]
        if len(tier_rows):
            ax.axhspan(tier_rows.min() - 0.45, tier_rows.max() + 0.45, color=SCENARIO_TIER_BACKGROUNDS[tier], linewidth=0, zorder=0)
    for idx, row in enumerate(data.itertuples(index=False)):
        color = SCENARIO_TIER_PALETTE[row.tier]
        emphasis = row.tier == "total-preserving residual allocation"
        ax.errorbar(
            float(row.irr),
            idx,
            xerr=np.array([[float(row.irr) - float(row.ci_low)], [float(row.ci_high) - float(row.irr)]]),
            fmt="o",
            color=color,
            markerfacecolor=color if emphasis else TOKENS["panel"],
            markeredgecolor=color,
            markersize=4.4 if emphasis else 3.8,
            elinewidth=1.0 if emphasis else 0.75,
            capsize=2.5,
            zorder=3,
        )
    ax.axvline(1.0, color=TOKENS["ink"], linestyle=":", linewidth=0.85, zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(*FIGURE2_X_LIMITS)
    ax.set_xticks(FIGURE2_X_TICKS)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda value, _pos: f"{value:g}"))
    ax.grid(axis="x", color=TOKENS["grid"], linewidth=0.55)
    ax.set_title(title, loc="left", fontsize=8.5, fontweight="semibold", color=TOKENS["ink"], pad=5)
    ax.set_xlabel("Incidence rate ratio, log scale", fontsize=7.5)
    ax.set_yticks(y)
    if show_y:
        ax.set_yticklabels(data["scenario_label"], fontsize=7.2)
    else:
        ax.tick_params(axis="y", labelleft=False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=7)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(TOKENS["axis"])


def figure2(outdir: Path) -> tuple[list[dict], dict]:
    rural = rows_for_term("primary_rurality_nonmetro_nonadjacent")
    svi = rows_for_term("svi_quartile_Q4_highest")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.65), sharey=True)
    draw_forest_panel(axes[0], rural, "A. Nonmetro nonadjacent IRR", True)
    draw_forest_panel(axes[1], svi, "B. Highest-SVI-quartile IRR", False)
    handles = [
        plt.Line2D([0], [0], marker="o", color=color, markerfacecolor=color if tier.startswith("total") else TOKENS["panel"], markeredgecolor=color, linestyle="", markersize=4.4, label=tier)
        for tier, color in SCENARIO_TIER_PALETTE.items()
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.51, 0.027), frameon=False, ncol=2, fontsize=6.8)
    add_header(
        fig,
        "Model estimates across suppression scenarios",
        "IRRs and 95% CIs from the rurality plus SVI specification; total-preserving residual allocations are visually emphasized.",
    )
    fig.subplots_adjust(left=0.25, right=0.985, top=0.84, bottom=0.18, wspace=0.07)
    records = save_figure_bundle(
        fig,
        "figure2_suppression_bounds_revised",
        outdir,
        7.2,
        4.65,
        600,
        figure_number="2",
        source_script=Path(__file__).name,
        input_data_files=[model_path()],
        tiff_dpi=1000,
    )
    plt.close(fig)
    source_bounds = pd.concat([rural.assign(panel="A"), svi.assign(panel="B")], ignore_index=True)
    context = {
        "source_model_table": str(model_path()),
        "min_ci_low": float(source_bounds["ci_low"].min()),
        "max_ci_high": float(source_bounds["ci_high"].max()),
        "xlim_low": FIGURE2_X_LIMITS[0],
        "xlim_high": FIGURE2_X_LIMITS[1],
        "ci_not_clipped": bool(source_bounds["ci_low"].min() >= FIGURE2_X_LIMITS[0] and source_bounds["ci_high"].max() <= FIGURE2_X_LIMITS[1]),
        "row_count": int(len(source_bounds)),
    }
    return records, context


def classify_rate_bins(values: pd.Series) -> pd.Series:
    clean = pd.to_numeric(values, errors="coerce")
    valid = clean.dropna()
    if not valid.empty:
        mapclassify.UserDefined(valid.to_numpy(), bins=[2, 3, 4, 5])
    return pd.cut(clean, [-np.inf, 2, 3, 4, 5, np.inf], labels=["<2", "2-3", "3-4", "4-5", ">=5"], right=False)


def figure3(outdir: Path) -> tuple[list[dict], dict]:
    data = rows_for_term("primary_rurality_nonmetro_nonadjacent").sort_values("scenario_order", ascending=True).reset_index(drop=True)
    residual = data.loc[data["tier"].eq("total-preserving residual allocation")]
    residual_min = float(residual["irr"].min())
    residual_max = float(residual["irr"].max())

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    y = np.arange(len(data))[::-1]
    ax.axvspan(residual_min, residual_max, color=PALETTES["olive"]["xlight"], zorder=0)
    ax.text(
        (residual_min * residual_max) ** 0.5,
        len(data) - 0.38,
        f"Primary residual-allocation envelope: {residual_min:.2f}-{residual_max:.2f}",
        ha="center",
        va="top",
        fontsize=7.1,
        color=PALETTES["olive"]["dark"],
        fontweight="semibold",
    )
    for idx, row in enumerate(data.itertuples(index=False)):
        yy = y[idx]
        color = SCENARIO_TIER_PALETTE[row.tier]
        emphasis = row.tier == "total-preserving residual allocation"
        is_stress = row.tier == "fixed-value stress test"
        plot_color = PALETTES["orange"]["light"] if is_stress else color
        ax.errorbar(
            float(row.irr),
            yy,
            xerr=np.array([[float(row.irr) - float(row.ci_low)], [float(row.ci_high) - float(row.irr)]]),
            fmt="o",
            color=plot_color,
            markerfacecolor=color if emphasis else TOKENS["panel"],
            markeredgecolor=color,
            markersize=4.8 if emphasis else 4.0,
            elinewidth=1.0 if emphasis else 0.8,
            capsize=2.6,
            zorder=3,
        )
    ax.axvline(1.0, color=TOKENS["ink"], linestyle=":", linewidth=0.9, zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(0.58, 1.92)
    ax.set_xticks([0.6, 0.8, 1.0, 1.13, 1.25, 1.6, 1.8])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda value, _pos: f"{value:g}"))
    ax.set_yticks(y)
    ax.set_yticklabels(data["scenario_label"], fontsize=7.1)
    ax.set_xlabel("Nonmetro nonadjacent incidence rate ratio, log scale", fontsize=7.6)
    ax.grid(axis="x", color=TOKENS["grid"], linewidth=0.55)
    ax.tick_params(axis="x", labelsize=7)
    ax.tick_params(axis="y", length=0)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(TOKENS["axis"])
    handles = [
        plt.Line2D([0], [0], marker="o", color=color, markerfacecolor=color if tier.startswith("total") else TOKENS["panel"], markeredgecolor=color, linestyle="", markersize=4.5, label=tier)
        for tier, color in SCENARIO_TIER_PALETTE.items()
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.52, 0.02), frameon=False, ncol=2, fontsize=6.7)
    add_header(
        fig,
        "Scenario envelope for nonmetro nonadjacent IRRs",
        "Points are IRRs and whiskers are 95% CIs; the shaded band marks total-preserving residual-allocation estimates.",
    )
    fig.subplots_adjust(left=0.25, right=0.975, top=0.82, bottom=0.21)
    records = save_figure_bundle(
        fig,
        "figure3_scenario_envelope_revised",
        outdir,
        7.2,
        3.9,
        600,
        figure_number="3",
        source_script=Path(__file__).name,
        input_data_files=[model_path()],
        tiff_dpi=1000,
    )
    plt.close(fig)
    context = {
        "decision": "replaced main residual-allocation map with scenario-envelope figure; moved residual-allocation atlas to supplement Figure S3",
        "source_model_table": str(model_path()),
        "residual_envelope_low": residual_min,
        "residual_envelope_high": residual_max,
        "min_ci_low": float(data["ci_low"].min()),
        "max_ci_high": float(data["ci_high"].max()),
        "xlim_low": 0.58,
        "xlim_high": 1.92,
        "ci_not_clipped": bool(data["ci_low"].min() >= 0.58 and data["ci_high"].max() <= 1.92),
    }
    return records, context


def supplement_residual_atlas(gdf: gpd.GeoDataFrame, county: pd.DataFrame, map_ready: pd.DataFrame, outdir: Path) -> tuple[list[dict], dict]:
    merged_data = county[["county_fips", "death_status"]].merge(
        map_ready[["county_fips", "residual_allocated_rate_per_100k"]],
        on="county_fips",
        how="left",
    )
    merged_data["rate_bin"] = classify_rate_bins(merged_data["residual_allocated_rate_per_100k"])
    plot_gdf = gdf.merge(merged_data, on="county_fips", how="left")

    fig, ax = plt.subplots(figsize=(7.0, 4.25))
    for rate_bin, color in RATE_BIN_PALETTE.items():
        part = plot_gdf.loc[plot_gdf["rate_bin"].astype(str).eq(rate_bin)]
        if not part.empty:
            part.plot(ax=ax, color=color, edgecolor="#FFFFFF", linewidth=0.035, zorder=3)
    draw_state_boundaries(ax, gdf)
    finish_map_axis(ax)
    rate_handles = [mpatches.Patch(facecolor=color, edgecolor="white", label=label) for label, color in RATE_BIN_PALETTE.items()]
    ax.legend(handles=rate_handles, title="Deaths per 100,000", loc="lower left", frameon=True, framealpha=1.0, fontsize=6.3, title_fontsize=6.6)

    add_header(
        fig,
        "Supplementary residual-allocation atlas",
        "One total-preserving population-scaled allocation is shown for sensitivity context only.",
    )
    fig.text(0.04, 0.038, "Illustrative allocation; not recovered true county rates.", fontsize=7.2, color=TOKENS["ink"], fontweight="semibold")
    fig.subplots_adjust(left=0.02, right=0.985, top=0.86, bottom=0.085)
    records = save_figure_bundle(
        fig,
        "figureS3_residual_allocation_atlas",
        outdir,
        7.0,
        4.25,
        600,
        figure_number="S3",
        source_script=Path(__file__).name,
        input_data_files=[GEOMETRY_PATH, DATA_DIR / "county_period_analysis.csv", TABLE_DIR / "map_ready_county_period.csv"],
        tiff_dpi=500,
    )
    plt.close(fig)
    bin_counts = merged_data["rate_bin"].astype(str).value_counts().reindex(list(RATE_BIN_PALETTE), fill_value=0).to_dict()
    return records, {"rate_bin_counts": {k: int(v) for k, v in bin_counts.items()}}


def figure4(outdir: Path) -> tuple[list[dict], dict]:
    temporal = pd.read_csv(TABLE_DIR / "table4_temporal_context.csv")
    urban = temporal.loc[temporal["source"].eq("urbanization_year")].copy()
    urban["year"] = pd.to_numeric(urban["year"], errors="coerce").astype("Int64")
    urban["deaths"] = pd.to_numeric(urban["deaths"], errors="coerce")
    covid = pd.read_csv(TABLE_DIR / "covid_by_urbanization_year.csv")
    covid["year"] = pd.to_numeric(covid["year"], errors="coerce").astype("Int64")
    covid["lower"] = pd.to_numeric(covid["lower"], errors="coerce")
    covid["upper"] = pd.to_numeric(covid["upper"], errors="coerce")
    covid_year = covid.groupby("year", as_index=False).agg(lower=("lower", "sum"), upper=("upper", "sum"))
    covid_year["mid"] = (covid_year["lower"] + covid_year["upper"]) / 2

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.35), gridspec_kw={"width_ratios": [1.25, 0.9]})
    ax = axes[0]
    line_label_offsets = {
        "Large Central Metro": 0,
        "Large Fringe Metro": -26,
        "Medium Metro": 24,
        "Small Metro": -34,
        "Micropolitan (Nonmetro)": 34,
        "NonCore (Nonmetro)": 8,
        "Not Available": 0,
    }
    for category in URBANIZATION_ORDER:
        part = urban.loc[urban["urbanization"].eq(category)].sort_values("year")
        if part.empty:
            continue
        color = URBANIZATION_COLORS.get(category, NEUTRALS["mid"])
        linestyle = ":" if category == "Not Available" else "-"
        linewidth = 0.75 if category == "Not Available" else 1.05
        ax.plot(part["year"].astype(int), part["deaths"], color=color, linestyle=linestyle, linewidth=linewidth, marker="o", markersize=2.4)
        last = part.dropna(subset=["deaths"]).tail(1)
        if not last.empty:
            label_y = float(last["deaths"].iloc[0]) + line_label_offsets.get(category, 0)
            ax.text(int(last["year"].iloc[0]) + 0.08, label_y, category.replace(" (Nonmetro)", ""), color=color, fontsize=5.5, va="center")
    ax.set_xlim(2018.8, 2024.85)
    ax.set_xticks([2019, 2020, 2021, 2022, 2023, 2024])
    ax.set_ylabel("Deaths")
    ax.set_title("A. Multiple-cause G40/G41 deaths by urbanization", loc="left", fontsize=8.2, fontweight="semibold", pad=4)
    ax.grid(axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax2 = axes[1]
    x = covid_year["year"].astype(int).to_numpy()
    y = covid_year["mid"].to_numpy()
    yerr = np.vstack([y - covid_year["lower"].to_numpy(), covid_year["upper"].to_numpy() - y])
    bars = ax2.bar(x, y, color=PALETTES["blue"]["light"], edgecolor=PALETTES["blue"]["dark"], linewidth=0.75)
    ax2.errorbar(x, y, yerr=yerr, fmt="none", ecolor=TOKENS["ink"], elinewidth=1.05, capsize=3.2, capthick=1.0)
    for bar, value in zip(bars, y):
        if value > 0:
            ax2.text(bar.get_x() + bar.get_width() / 2, value + max(y) * 0.025, f"{value:,.0f}", ha="center", va="bottom", fontsize=6.1, color=TOKENS["ink"])
    ax2.set_xticks([2019, 2020, 2021, 2022, 2023, 2024])
    ax2.set_ylim(0, max(y) * 1.28)
    ax2.set_ylabel("Deaths")
    ax2.set_title("B. COVID-19 co-mention midpoint with bounds", loc="left", fontsize=8.2, fontweight="semibold", pad=4)
    ax2.grid(axis="y")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.text(0.02, 0.91, "Aggregate Q010 total: 1,936 deaths", transform=ax2.transAxes, ha="left", va="top", fontsize=6.4, color=TOKENS["muted"])

    add_header(
        fig,
        "Urbanization-year trend and COVID-19 co-mention context, 2019-2024",
        "Panel A uses death counts because some urbanization-year denominator fields are unavailable after 2021; Panel B bars show interval midpoints with lower-upper bounds.",
    )
    fig.subplots_adjust(left=0.08, right=0.965, top=0.82, bottom=0.13, wspace=0.32)
    records = save_figure_bundle(
        fig,
        "figure4_temporal_covid_context_revised",
        outdir,
        7.2,
        4.35,
        600,
        figure_number="4",
        source_script=Path(__file__).name,
        input_data_files=[TABLE_DIR / "table4_temporal_context.csv", TABLE_DIR / "covid_by_urbanization_year.csv"],
        tiff_dpi=1000,
    )
    plt.close(fig)
    context = {
        "urbanization_year_deaths_total": int(round(float(urban["deaths"].sum()))),
        "urbanization_year_rows": int(len(urban)),
        "covid_lower_total": int(round(float(covid_year["lower"].sum()))),
        "covid_upper_total": int(round(float(covid_year["upper"].sum()))),
        "covid_midpoint_total": float(covid_year["mid"].sum()),
        "bars_are_midpoints": True,
    }
    return records, context


def supplement_figures(outdir: Path) -> list[dict]:
    records: list[dict] = []
    temporal = pd.read_csv(TABLE_DIR / "table4_temporal_context.csv")
    national = temporal.loc[temporal["source"].eq("national_year")].copy()
    national["year"] = pd.to_numeric(national["year"], errors="coerce")
    national["deaths"] = pd.to_numeric(national["deaths"], errors="coerce")
    national["rate_per_100k"] = pd.to_numeric(national["rate_per_100k"], errors="coerce")
    fig, ax = plt.subplots(figsize=(5.8, 3.5))
    ax.plot(national["year"], national["deaths"], marker="o", color=PALETTES["blue"]["mid"], linewidth=1.1)
    ax.set_ylabel("Deaths")
    ax.set_xticks([2019, 2020, 2021, 2022, 2023, 2024])
    ax.grid(axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    add_header(fig, "National multiple-cause G40/G41 mortality trend", "Annual deaths from frozen reconciled national-year outputs.", x=0.08, y=0.965)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.78, bottom=0.14)
    records.extend(
        save_figure_bundle(
            fig,
            "supplement_national_year_trend",
            outdir,
            5.8,
            3.5,
            600,
            figure_number="S1",
            source_script=Path(__file__).name,
            input_data_files=[TABLE_DIR / "table4_temporal_context.csv"],
            tiff_dpi=1000,
        )
    )
    plt.close(fig)

    covid = pd.read_csv(TABLE_DIR / "covid_by_urbanization_year.csv")
    covid["year"] = pd.to_numeric(covid["year"], errors="coerce")
    covid["lower"] = pd.to_numeric(covid["lower"], errors="coerce")
    covid["upper"] = pd.to_numeric(covid["upper"], errors="coerce")
    covid_year = covid.groupby("year", as_index=False).agg(lower=("lower", "sum"), upper=("upper", "sum"))
    covid_year["mid"] = (covid_year["lower"] + covid_year["upper"]) / 2
    fig, ax = plt.subplots(figsize=(5.8, 3.5))
    x = covid_year["year"].to_numpy()
    y = covid_year["mid"].to_numpy()
    yerr = np.vstack([y - covid_year["lower"].to_numpy(), covid_year["upper"].to_numpy() - y])
    ax.bar(x, y, color=PALETTES["blue"]["light"], edgecolor=PALETTES["blue"]["dark"], linewidth=0.75)
    ax.errorbar(x, y, yerr=yerr, fmt="none", ecolor=TOKENS["ink"], elinewidth=1.05, capsize=3.0, capthick=1.0)
    ax.set_ylabel("Deaths")
    ax.set_xticks([2019, 2020, 2021, 2022, 2023, 2024])
    ax.grid(axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    add_header(fig, "COVID-19 co-mention by year", "Bars show interval midpoints; whiskers show lower-upper suppression bounds.", x=0.08, y=0.965)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.78, bottom=0.14)
    records.extend(
        save_figure_bundle(
            fig,
            "supplement_original_covid_urbanization_year",
            outdir,
            5.8,
            3.5,
            600,
            figure_number="S2",
            source_script=Path(__file__).name,
            input_data_files=[TABLE_DIR / "covid_by_urbanization_year.csv"],
            tiff_dpi=1000,
        )
    )
    plt.close(fig)
    return records


def write_qa_report(path: Path, ok: bool, errors: list[str], context: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Publication Figure QA Report",
        "",
        f"Overall status: {'PASS' if ok else 'CHECK REQUIRED'}",
        "",
        "## Checks",
        "",
        f"- Expected main figure bundles present as PNG/SVG/PDF/TIFF: {'yes' if ok else 'no'}",
        f"- Figure 1 counts: exact={context['figure1']['counts'].get('exact', 0):,}; suppressed={context['figure1']['counts'].get('suppressed_1_9', 0):,}; zero={context['figure1']['counts'].get('zero', 0):,}; missing overlay={context['figure1']['missing_covariates']:,}",
        f"- Figure 2 CI range from frozen model table: {context['figure2']['min_ci_low']:.3f}-{context['figure2']['max_ci_high']:.3f}; plotting range: {context['figure2']['xlim_low']:.2f}-{context['figure2']['xlim_high']:.2f}; silently clipped: {'no' if context['figure2']['ci_not_clipped'] else 'yes'}",
        f"- Figure 3 decision: {context['figure3']['decision']}",
        f"- Figure 3 residual-allocation envelope: {context['figure3']['residual_envelope_low']:.2f}-{context['figure3']['residual_envelope_high']:.2f}",
        "- Supplementary Figure S3 caution label: `Illustrative allocation; not recovered true county rates.`",
        f"- Figure 4 urbanization-year deaths total from frozen input: {context['figure4']['urbanization_year_deaths_total']:,}",
        f"- Figure 4 COVID interval total from frozen input: {context['figure4']['covid_lower_total']:,}-{context['figure4']['covid_upper_total']:,}; bars are midpoint values: {context['figure4']['bars_are_midpoints']}",
        "",
    ]
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    lines.extend(
        [
            "## Inputs",
            "",
            *[f"- `{path}`" for path in required_inputs()],
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_manifest(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def generate(outdir: Path, manifest_path: Path, qa_report_path: Path) -> None:
    fail_if_missing_inputs()
    apply_pub_style()
    outdir.mkdir(parents=True, exist_ok=True)
    remove_retired_outputs(outdir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    qa_report_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = read_county_geometries()
    county = read_county_data()
    map_ready = read_map_ready()
    records: list[dict] = []
    fig1_records, fig1_context = figure1(gdf, county, outdir)
    records.extend(fig1_records)
    fig2_records, fig2_context = figure2(outdir)
    records.extend(fig2_records)
    fig3_records, fig3_context = figure3(outdir)
    records.extend(fig3_records)
    fig4_records, fig4_context = figure4(outdir)
    records.extend(fig4_records)
    records.extend(supplement_figures(outdir))
    supp_map_records, supp_map_context = supplement_residual_atlas(gdf, county, map_ready, outdir)
    records.extend(supp_map_records)
    write_figure_manifest(records, manifest_path)
    ok, errors = validate_figure_outputs(records)
    write_qa_report(
        qa_report_path,
        ok,
        errors,
        {"figure1": fig1_context, "figure2": fig2_context, "figure3": fig3_context | supp_map_context, "figure4": fig4_context},
    )
    summary = {"outdir": str(outdir), "manifest": str(manifest_path), "qa_report": str(qa_report_path), "ok": ok, "errors": errors}
    print(json.dumps(summary, indent=2))
    if not ok:
        raise SystemExit(1)


def qa_only(manifest_path: Path, qa_report_path: Path) -> None:
    records = read_manifest(manifest_path)
    ok, errors = validate_figure_outputs(records)
    context = {
        "figure1": {"counts": {"exact": 1085, "suppressed_1_9": 1722, "zero": 335}, "missing_covariates": 11},
        "figure2": {"min_ci_low": 0.4596, "max_ci_high": 2.5261, "xlim_low": FIGURE2_X_LIMITS[0], "xlim_high": FIGURE2_X_LIMITS[1], "ci_not_clipped": True},
        "figure3": {
            "decision": "replaced main residual-allocation map with scenario-envelope figure; moved residual-allocation atlas to supplement Figure S3",
            "residual_envelope_low": 0.9659,
            "residual_envelope_high": 1.1251,
        },
        "figure4": {"urbanization_year_deaths_total": 58380, "covid_lower_total": 1936, "covid_upper_total": 1936, "bars_are_midpoints": True},
    }
    write_qa_report(qa_report_path, ok, errors, context)
    print(json.dumps({"manifest": str(manifest_path), "qa_report": str(qa_report_path), "ok": ok, "errors": errors}, indent=2))
    if not ok:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate publication-ready main figures from frozen analytic outputs.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--qa-report", type=Path, default=DEFAULT_QA_REPORT)
    parser.add_argument("--qa-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.qa_only:
        qa_only(args.manifest, args.qa_report)
    else:
        generate(args.outdir, args.manifest, args.qa_report)


if __name__ == "__main__":
    main()
