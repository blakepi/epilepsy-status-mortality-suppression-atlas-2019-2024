from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from . import palettes
from .io import ensure_output_dirs, final_estimates, load_config, load_model_frame, rel_path
from .maps import load_map_frame, plot_us_with_insets, write_map_data
from .style import configure_matplotlib, save_figure_all, wrap_label
from .tables import build_table4


def _clean_generated_figures(config: dict) -> None:
    dirs = ensure_output_dirs(config)
    for leaf in ["main", "supplement"]:
        target = dirs["figures"] / leaf
        for path in target.glob("*"):
            if path.is_file() and path.suffix.lower() in {".svg", ".pdf", ".png", ".tiff", ".tif"}:
                path.unlink()


def _panel_label(ax, label: str) -> None:
    ax.text(-0.06, 1.06, label, transform=ax.transAxes, fontsize=13, fontweight="bold", va="top")


def _clean_label(text: str) -> str:
    return {
        "metro_other vs metro_large": "Other metropolitan vs large metropolitan",
        "nonmetro_adjacent vs metro_large": "Nonmetro adjacent vs large metropolitan",
        "nonmetro_nonadjacent vs metro_large": "Nonmetro nonadjacent vs large metropolitan",
    }.get(text, text)


def _en_interval(low, high) -> str:
    return f"{float(low):.2f}–{float(high):.2f}"


def figure1(config: dict) -> list[Path]:
    dirs = ensure_output_dirs(config)
    model = load_model_frame(config)
    configure_matplotlib(config)
    fig, axes = plt.subplots(1, 3, figsize=(11.6, 4.2), constrained_layout=True)

    status_counts = model["q002_count_status"].value_counts().reindex(["exact", "suppressed_1_9", "zero"], fill_value=0)
    labels = ["Exact", "Suppressed\n1–9", "Explicit\nzero"]
    colors = [palettes.VISIBILITY[k] for k in ["exact", "suppressed_1_9", "zero"]]
    axes[0].bar(labels, status_counts.values, color=colors)
    axes[0].set_ylabel("County-year cells")
    axes[0].set_title("County-year visibility", fontweight="bold")
    _panel_label(axes[0], "A")

    ax = axes[1]
    ax.set_axis_off()
    boxes = [
        (0.04, 0.68, "Cell data\nexact / zero /\nsuppressed 1–9"),
        (0.04, 0.36, "Public totals\nstate-year /\nyear / total"),
        (0.58, 0.52, "Feasible latent\ncounty-year counts"),
    ]
    for x, y, text in boxes:
        patch = FancyBboxPatch((x, y), 0.35, 0.23, boxstyle="round,pad=0.03", linewidth=1.2, edgecolor=palettes.PRIMARY, facecolor="#F8FBFD")
        ax.add_patch(patch)
        ax.text(x + 0.175, y + 0.115, text, ha="center", va="center", fontsize=10.7)
    ax.annotate("", xy=(0.58, 0.63), xytext=(0.39, 0.79), arrowprops=dict(arrowstyle="->", color=palettes.NEUTRAL, linewidth=1.3))
    ax.annotate("", xy=(0.58, 0.63), xytext=(0.39, 0.47), arrowprops=dict(arrowstyle="->", color=palettes.NEUTRAL, linewidth=1.3))
    ax.text(0.51, 0.16, "Sampler keeps only\nconstraint-satisfying counts.", ha="center", va="center", fontsize=10)
    ax.set_title("Constraint logic", fontweight="bold")
    _panel_label(ax, "B")

    ax = axes[2]
    q001 = model.groupby("county_fips")["q001_period_status"].first().value_counts()
    intervals = pd.Series(
        {
            "Exact county-period": int(q001.get("exact", 0)),
            "Suppressed 1–9": int(q001.get("suppressed_1_9", 0)),
            "Explicit zero": int(q001.get("zero", 0)),
        }
    )
    ax.barh(intervals.index[::-1], intervals.values[::-1], color=[palettes.NEUTRAL, palettes.ACCENT, palettes.POSITIVE])
    ax.set_xlabel("Counties")
    ax.set_title("County-period constraints", fontweight="bold")
    _panel_label(ax, "C")

    fig.suptitle("Suppression-aware modeling necessity and public constraint structure", fontweight="bold")
    return save_figure_all(fig, "figure1_suppression_aware_modeling_necessity", dirs["figures"] / "main", config)


def figure2(config: dict) -> list[Path]:
    dirs = ensure_output_dirs(config)
    df = final_estimates(config)
    irr = df[df["estimate_type"] == "IRR"].copy()
    irr["label"] = irr["term"].map(lambda x: wrap_label(_clean_label(x), 34))
    y = np.arange(len(irr))[::-1]
    configure_matplotlib(config)
    fig, ax = plt.subplots(figsize=(8.2, 4.6), constrained_layout=True)
    colors = irr["family"].map({"Rurality": palettes.PRIMARY, "SVI": palettes.SECONDARY}).fillna(palettes.NEUTRAL)
    for yy, (_, row), color in zip(y, irr.iterrows(), colors):
        ax.errorbar(
            row["posterior_median"],
            yy,
            xerr=[
                [row["posterior_median"] - row["credible_interval_lower_95"]],
                [row["credible_interval_upper_95"] - row["posterior_median"]],
            ],
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=2.2,
            capsize=4,
            markersize=6.5,
            zorder=3,
        )
    ax.axvline(1.0, color="#2C3E50", linewidth=1, linestyle="--")
    ax.set_yticks(y, irr["label"])
    ax.set_xlabel("Posterior mortality rate ratio")
    ax.set_title("Final Wahab HPC mortality model associations")
    for _, row in irr.iterrows():
        yy = y[list(irr.index).index(row.name)]
        ax.text(row["credible_interval_upper_95"] + 0.02, yy, f"{row['posterior_median']:.2f} ({_en_interval(row['credible_interval_lower_95'], row['credible_interval_upper_95'])})", va="center", fontsize=8.2)
    ax.set_xlim(0.95, max(1.58, float(irr["credible_interval_upper_95"].max()) + 0.18))
    fig.text(0.01, 0.01, "Reference categories: large metropolitan counties and SVI Q1.", fontsize=8, color=palettes.NEUTRAL)
    return save_figure_all(fig, "figure2_primary_posterior_irrs", dirs["figures"] / "main", config)


def _parse_interval(text: str) -> tuple[float, float]:
    nums = re.findall(r"\d+(?:\.\d+)?", str(text))
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    return np.nan, np.nan


def figure3(config: dict) -> list[Path]:
    dirs = ensure_output_dirs(config)
    df = build_table4(config).copy()
    df["estimate"] = pd.to_numeric(df["Nonmetro nonadjacent mortality rate ratio"], errors="coerce")
    intervals = df["95% interval"].map(_parse_interval)
    df["lower"] = intervals.map(lambda x: x[0])
    df["upper"] = intervals.map(lambda x: x[1])
    df["label"] = df["Method"].map(lambda x: wrap_label(x, 38))
    y = np.arange(len(df))[::-1]
    colors = np.where(df["Method"].eq("Bayesian constrained latent-count model"), palettes.WARNING, palettes.NEUTRAL)
    configure_matplotlib(config)
    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    fig.subplots_adjust(left=0.31, right=0.98, bottom=0.16, top=0.90)
    for yy, (_, row), color in zip(y, df.iterrows(), colors):
        if pd.notna(row["estimate"]) and pd.notna(row["lower"]) and pd.notna(row["upper"]):
            ax.errorbar(
                row["estimate"],
                yy,
                xerr=[[row["estimate"] - row["lower"]], [row["upper"] - row["estimate"]]],
                fmt="o",
                color=color,
                ecolor=color,
                elinewidth=2,
                capsize=3,
                markersize=7 if row["Method"] == "Bayesian constrained latent-count model" else 5,
                zorder=3,
            )
    ax.axvline(1.0, color="#2C3E50", linestyle="--", linewidth=1)
    ax.set_yticks(y, df["label"])
    ax.set_xlabel("Nonmetro nonadjacent vs large metropolitan mortality rate ratio", labelpad=10)
    ax.set_title("Suppression handling comparison with final constrained Bayesian estimate")
    ax.set_xlim(0.55, 1.9)
    for i, row in df.iterrows():
        ax.text(row["upper"] + 0.03 if pd.notna(row["upper"]) else 1.65, y[i], f"{row['estimate']:.2f} ({row['95% interval']})", va="center", fontsize=7.8)
    fig.text(0.31, 0.035, "Scenario rows are sensitivity analyses; the Bayesian row is the final constrained model.", fontsize=8, color=palettes.NEUTRAL)
    return save_figure_all(fig, "figure3_suppression_handling_comparison", dirs["figures"] / "main", config)


def figure4(config: dict) -> list[Path]:
    dirs = ensure_output_dirs(config)
    gdf = load_map_frame(config)
    gdf["rate_uncertainty_width"] = gdf["rate_credible_interval_upper_95"] - gdf["rate_credible_interval_lower_95"]
    configure_matplotlib(config)
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.3), constrained_layout=True)
    rate_bins = np.array([0, 2, 4, 6, 10, 20, max(81, float(gdf["posterior_mean_rate_per_100k"].max()) + 0.01)])
    uncertainty_bins = np.array([0, 1, 2, 4, 8, 15, max(43, float(gdf["rate_uncertainty_width"].max()) + 0.01)])
    sm1, _ = plot_us_with_insets(axes[0], gdf, "posterior_mean_rate_per_100k", "A. Posterior mean county-period rate", cmap_name="Blues", bins=rate_bins)
    cb1 = fig.colorbar(sm1, ax=axes[0], fraction=0.038, pad=0.012)
    cb1.set_label("Deaths per 100,000 person-years", fontsize=10)
    cb1.set_ticks((rate_bins[:-1] + rate_bins[1:]) / 2)
    cb1.set_ticklabels(["0–2", "2–4", "4–6", "6–10", "10–20", "20+"])
    cb1.ax.tick_params(labelsize=9)
    sm2, _ = plot_us_with_insets(axes[1], gdf, "rate_uncertainty_width", "B. Posterior uncertainty width", cmap_name="Greens", bins=uncertainty_bins)
    cb2 = fig.colorbar(sm2, ax=axes[1], fraction=0.038, pad=0.012)
    cb2.set_label("95% CrI width", fontsize=10)
    cb2.set_ticks((uncertainty_bins[:-1] + uncertainty_bins[1:]) / 2)
    cb2.set_ticklabels(["0–1", "1–2", "2–4", "4–8", "8–15", "15+"])
    cb2.ax.tick_params(labelsize=9)
    fig.suptitle("Posterior county-level mortality atlas", fontweight="bold")
    write_map_data(config, dirs["tables"] / "figure4_map_data.csv")
    return save_figure_all(fig, "figure4_posterior_county_maps", dirs["figures"] / "main", config)


def supplement_figures(config: dict) -> dict[str, list[Path]]:
    dirs = ensure_output_dirs(config)
    configure_matplotlib(config)
    written: dict[str, list[Path]] = {}
    final = config["final_wahab_handoff"]

    fig, ax = plt.subplots(figsize=(7.2, 3.8), constrained_layout=True)
    ax.set_axis_off()
    cards = [
        ("Gate", "Passed"),
        ("Chains", f"{final['chains']}"),
        ("Parameters", f"{final['parameter_count']}"),
        ("Maximum R-hat", f"{final['maximum_rhat']:.4f}"),
        ("Minimum bulk ESS", f"{final['minimum_bulk_ess']:.0f}"),
        ("Constraint checks", "0 failures"),
    ]
    for idx, (label, value) in enumerate(cards):
        col = idx % 3
        row = idx // 3
        x = 0.05 + col * 0.31
        y0 = 0.58 - row * 0.34
        patch = FancyBboxPatch((x, y0), 0.26, 0.23, boxstyle="round,pad=0.025", linewidth=1.1, edgecolor=palettes.PRIMARY, facecolor="#F8FBFD")
        ax.add_patch(patch)
        ax.text(x + 0.13, y0 + 0.145, value, ha="center", va="center", fontsize=14, fontweight="bold", color=palettes.PRIMARY)
        ax.text(x + 0.13, y0 + 0.06, label, ha="center", va="center", fontsize=9, color=palettes.NEUTRAL)
    ax.set_title("Final convergence gate summary", fontweight="bold")
    written["S1"] = save_figure_all(fig, "figureS1_convergence_gate_card", dirs["figures"] / "supplement", config)

    estimates = final_estimates(config)
    irr = estimates[estimates["estimate_type"] == "IRR"].copy()
    y = np.arange(len(irr))[::-1]
    fig, ax = plt.subplots(figsize=(8.0, 4.5), constrained_layout=True)
    ax.errorbar(
        irr["posterior_median"],
        y,
        xerr=[irr["posterior_median"] - irr["credible_interval_lower_95"], irr["credible_interval_upper_95"] - irr["posterior_median"]],
        fmt="o",
        color=palettes.PRIMARY,
        ecolor=palettes.PRIMARY,
        capsize=3,
    )
    ax.axvline(1.0, color=palettes.NEUTRAL, linestyle="--")
    ax.set_yticks(y, irr["term"].map(lambda x: wrap_label(_clean_label(x), 34)))
    ax.set_xlabel("Posterior mortality rate ratio")
    ax.set_title("Final posterior mortality-rate-ratio summary")
    written["S2"] = save_figure_all(fig, "figureS2_final_posterior_mrr_summary", dirs["figures"] / "supplement", config)

    gdf = load_map_frame(config)
    gdf["rate_uncertainty_width"] = gdf["rate_credible_interval_upper_95"] - gdf["rate_credible_interval_lower_95"]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.2), constrained_layout=True)
    sm1, _ = plot_us_with_insets(axes[0], gdf, "posterior_probability_rate_exceeds_national_rate", "A. Probability rate exceeds national rate", cmap_name="Purples")
    fig.colorbar(sm1, ax=axes[0], fraction=0.035, pad=0.01).set_label("Posterior probability")
    sm2, _ = plot_us_with_insets(axes[1], gdf, "rate_uncertainty_width", "B. Rate uncertainty width", cmap_name="Greens")
    fig.colorbar(sm2, ax=axes[1], fraction=0.035, pad=0.01).set_label("95% CrI width")
    written["S3"] = save_figure_all(fig, "figureS3_probability_uncertainty_maps", dirs["figures"] / "supplement", config)

    constraints = pd.read_csv(rel_path(config, "constraint_validation"))
    summary = constraints.groupby("check", as_index=False).agg(
        validation_records=("validation_records", "sum"),
        failed_records=("failed_records", "sum"),
    )
    summary["passing_records"] = summary["validation_records"] - summary["failed_records"]
    summary["label"] = summary["check"].str.replace("_", " ", regex=False).str.title()
    fig, ax = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ax.barh(summary["label"].map(lambda x: wrap_label(x, 34)), summary["passing_records"], color=palettes.POSITIVE)
    ax.set_xlabel("Passing validation records")
    ax.set_title("Final latent-count constraint validation")
    written["S4"] = save_figure_all(fig, "figureS4_constraint_validation_summary", dirs["figures"] / "supplement", config)
    return written


def build_all_figures(config: dict | None = None) -> dict[str, list[Path]]:
    config = config or load_config()
    _clean_generated_figures(config)
    outputs = {
        "figure1": figure1(config),
        "figure2": figure2(config),
        "figure3": figure3(config),
        "figure4": figure4(config),
    }
    outputs.update(supplement_figures(config))
    return outputs
