from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageChops


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUND2 = PROJECT_ROOT / "manuscript" / "editorial_revision_round2_ready"
OUT = PROJECT_ROOT / "manuscript" / "editorial_revision_round3_ready"
FIG_DIR = OUT / "figures"
TABLE_DIR = OUT / "tables"
REPORT_DIR = OUT / "reports"


SCENARIO_LABELS = {
    "observed_exact_positive_only": "Exact visible",
    "observed_exact_plus_zero": "Exact + zero",
    "suppressed_equals_1": "Suppressed = 1",
    "suppressed_equals_mean_4_06": "Uniform mean",
    "suppressed_equals_5": "Suppressed = 5",
    "suppressed_equals_9": "Suppressed = 9",
    "population_scaled_residual_allocation": "Population residual",
    "conservative_anti_rural_allocation": "Anti-rural residual",
    "pro_rural_allocation": "Pro-rural residual",
    "interval_likelihood": "Interval NB",
}

SCENARIO_ORDER = list(SCENARIO_LABELS)
TIER_COLORS = {
    "visible": "#4C78A8",
    "total_preserving": "#2A9D8F",
    "stress": "#F58518",
    "interval": "#6F4E7C",
}


def ensure_dirs() -> None:
    for path in [OUT, FIG_DIR, TABLE_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    for subdir in ["tables", "figures", "reports", "references", "supplement"]:
        src_dir = ROUND2 / subdir
        dest_dir = OUT / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        if src_dir.exists():
            for src in src_dir.glob("*"):
                if src.is_file():
                    shutil.copy2(src, dest_dir / src.name)


def crop_white_margin(src: Path, dest: Path, padding: int = 28) -> None:
    image = Image.open(src).convert("RGB")
    background = Image.new("RGB", image.size, (255, 255, 255))
    diff = ImageChops.difference(image, background)
    # Ignore tiny antialiasing differences from a white canvas.
    diff = diff.point(lambda p: 255 if p > 8 else 0)
    bbox = diff.getbbox()
    if bbox is None:
        shutil.copy2(src, dest)
        return
    left, top, right, bottom = bbox
    left = max(left - padding, 0)
    top = max(top - padding, 0)
    right = min(right + padding, image.width)
    bottom = min(bottom + padding, image.height)
    image.crop((left, top, right, bottom)).save(dest)


def classify_tier(scenario: str) -> str:
    if scenario in {"observed_exact_positive_only", "observed_exact_plus_zero"}:
        return "visible"
    if scenario in {
        "suppressed_equals_mean_4_06",
        "population_scaled_residual_allocation",
        "conservative_anti_rural_allocation",
        "pro_rural_allocation",
    }:
        return "total_preserving"
    if scenario == "interval_likelihood":
        return "interval"
    return "stress"


def model_rows_for(term: str) -> pd.DataFrame:
    full = pd.read_csv(TABLE_DIR / "table3_suppression_aware_models_revised_full.csv")
    direct = full[
        (full["model_family"] == "rurality_svi_composite")
        & (full["term"] == term)
        & (full["scenario"] != "interval_likelihood")
    ].copy()
    interval = full[
        (full["model_family"] == "interval_nb_rurality_svi")
        & (full["term"] == term)
        & (full["scenario"] == "interval_likelihood")
    ].copy()
    out = pd.concat([direct, interval], ignore_index=True)
    out["scenario_label"] = out["scenario"].map(SCENARIO_LABELS)
    out["scenario_order"] = out["scenario"].map({s: i for i, s in enumerate(SCENARIO_ORDER)})
    out["tier"] = out["scenario"].map(classify_tier)
    out = out.sort_values("scenario_order", ascending=False)
    return out


def draw_panel(ax, data: pd.DataFrame, title: str) -> None:
    y = np.arange(len(data))
    colors = [TIER_COLORS[t] for t in data["tier"]]
    x = data["irr"].astype(float).to_numpy()
    lo = data["ci_low"].astype(float).to_numpy()
    hi = data["ci_high"].astype(float).to_numpy()
    xerr = np.vstack([x - lo, hi - x])
    ax.errorbar(x, y, xerr=xerr, fmt="none", ecolor="#555555", elinewidth=1.2, capsize=3, zorder=1)
    ax.scatter(x, y, s=42, c=colors, edgecolor="black", linewidth=0.4, zorder=2)
    ax.axvline(1.0, color="#222222", linestyle="--", linewidth=1.0)
    ax.set_xscale("log")
    ax.set_xlim(0.55, 2.05)
    ax.set_xticks([0.6, 0.8, 1.0, 1.25, 1.6, 2.0])
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{value:g}"))
    ax.set_yticks(y)
    ax.set_yticklabels(data["scenario_label"], fontsize=9)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=8)
    ax.grid(axis="x", color="#D5D9DE", linewidth=0.8)
    ax.tick_params(axis="x", labelsize=9)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def make_figure2() -> None:
    rural = model_rows_for("primary_rurality_nonmetro_nonadjacent")
    svi = model_rows_for("svi_quartile_Q4_highest")
    fig, axes = plt.subplots(ncols=2, figsize=(11.2, 5.8), sharey=True)
    draw_panel(axes[0], rural, "A. Nonmetro nonadjacent IRR")
    draw_panel(axes[1], svi, "B. Highest SVI quartile IRR")
    axes[0].set_xlabel("Incidence rate ratio, log scale", fontsize=10)
    axes[1].set_xlabel("Incidence rate ratio, log scale", fontsize=10)
    axes[0].set_ylabel("Scenario", fontsize=10)
    handles = [
        plt.Line2D([0], [0], marker="o", color="w", label="Visible-only", markerfacecolor=TIER_COLORS["visible"], markeredgecolor="black", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", label="Total-preserving", markerfacecolor=TIER_COLORS["total_preserving"], markeredgecolor="black", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", label="Fixed-value stress", markerfacecolor=TIER_COLORS["stress"], markeredgecolor="black", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", label="Interval model", markerfacecolor=TIER_COLORS["interval"], markeredgecolor="black", markersize=7),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=9)
    fig.suptitle("Suppression-scenario model estimates", fontsize=14, fontweight="bold", y=0.98)
    fig.text(
        0.5,
        0.055,
        "Points show IRRs and whiskers show 95% confidence intervals from the rurality plus SVI specification.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=[0.02, 0.12, 1, 0.94], w_pad=2.4)
    fig.savefig(FIG_DIR / "figure2_two_panel_irrs_revised.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_report() -> None:
    rows = []
    for path in sorted(FIG_DIR.glob("*.png")):
        with Image.open(path) as image:
            rows.append({"file": path.name, "width_px": image.width, "height_px": image.height, "bytes": path.stat().st_size})
    pd.DataFrame(rows).to_csv(REPORT_DIR / "round3_figure_inventory.csv", index=False)
    report = """# Round 3 Figure Revision Report

Generated assets:

- `figure2_two_panel_irrs_revised.png`: two-panel publication figure separating nonmetro nonadjacent IRRs from highest-SVI-quartile IRRs with cleaner scenario labels.
- `figure1_county_suppression_status_tight.png`: whitespace-trimmed Figure 1 map for improved page fit.
- `figure3_suppression_aware_residual_rate_tight.png`: whitespace-trimmed Figure 3 map for improved page fit.

Figure 4 retains the corrected 2019-2024 temporal/COVID context figure from the Round 2 verified asset set.
"""
    (REPORT_DIR / "round3_figure_revision_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    crop_white_margin(
        ROUND2 / "figures" / "figure1_county_suppression_status_revised.png",
        FIG_DIR / "figure1_county_suppression_status_tight.png",
    )
    crop_white_margin(
        ROUND2 / "figures" / "figure3_suppression_aware_residual_rate.png",
        FIG_DIR / "figure3_suppression_aware_residual_rate_tight.png",
    )
    make_figure2()
    write_report()
    print(f"round3_figures={FIG_DIR}")


if __name__ == "__main__":
    main()
