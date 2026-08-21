#!/usr/bin/env python3
"""Build the truth-known calibration and method-performance figure.

Panel a reports interval coverage for each primary contrast under the
constrained Bayesian model across the 20-replicate truth-known program, with
exact binomial Monte Carlo intervals.  Panel b puts the same coverage metric
beside every prespecified alternative way of handling suppressed cells.

Interval coverage is the only quantity on either axis.  Bias travels as a
labelled column rather than a second axis, because one comparator's estimates
diverge and no shared bias axis could carry it honestly.

The script refuses to run unless the calibration program reports a passed
computational gate, and writes a sidecar recording every plotted number.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import beta  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "outputs/scientific_reports_v2/calibration_program"
DESTINATION = ROOT / "outputs/scientific_reports_v2/figures"

# Documented categorical slots 1, 3 and 2.  Validated all-pairs on a white print
# surface: worst CVD dE 9.2 (deutan) / 9.6 (tritan), worst normal-vision dE 24.0.
# Slot 3 sits at 2.82:1 against white, so the relief rule applies and every mark
# carries a visible label -- identity is never colour alone.
STUDY_HUE = "#2a78d6"
BENCHMARK_HUE = "#1baf7a"
NAIVE_HUE = "#eb6834"

INK = "#1a1a19"
INK_SOFT = "#55554e"
RULE = "#d5d5cd"

NOMINAL = 0.95

CONTRASTS = [
    ("primary_rurality_metro_other", "Metropolitan, other"),
    ("primary_rurality_nonmetro_adjacent", "Nonmetro, adjacent"),
    ("primary_rurality_nonmetro_nonadjacent", "Nonmetro, nonadjacent"),
    ("svi_quartile_Q2", "SVI quartile 2"),
    ("svi_quartile_Q3", "SVI quartile 3"),
    ("svi_quartile_Q4_highest", "SVI quartile 4, highest"),
]

# Grouped by what the method actually is, not by how well it scores.
BENCHMARKS = [
    ("oracle_complete_counts", "Oracle, true counts"),
    ("population_favoring_feasible_allocation", "Population-favoring"),
]
NAIVE = [
    ("visible_exact_and_zero_only", "Visible cells only"),
    ("suppressed_equals_1", "Suppressed = 1"),
    ("suppressed_equals_5", "Suppressed = 5"),
    ("suppressed_equals_9", "Suppressed = 9"),
]

DIVERGENCE_THRESHOLD = 1_000.0


def clopper_pearson(successes: int, trials: int) -> tuple[float, float]:
    lower = 0.0 if successes == 0 else float(beta.ppf(0.025, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(0.975, successes + 1, trials - successes))
    return lower, upper


def require_passed_program() -> dict:
    summary = json.loads((PROGRAM / "calibration_program_summary.json").read_text(encoding="utf-8"))
    if summary.get("computational_gate_pass") is not True:
        raise SystemExit("Refusing to plot: the calibration program gate has not passed")
    if summary.get("descriptive_calibration_reporting_authorized") is not True:
        raise SystemExit("Refusing to plot: descriptive calibration reporting is not authorized")
    return summary


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 7.5,
            "axes.labelsize": 8,
            "axes.titlesize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "axes.edgecolor": RULE,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK_SOFT,
            "ytick.color": INK_SOFT,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.0,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def coverage_axis(ax) -> None:
    ax.axvline(NOMINAL, color=INK_SOFT, linewidth=0.7, linestyle=(0, (3, 3)), zorder=1)
    ax.set_xlim(0, 1.045)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25", "50", "75", "100"])
    ax.set_xlabel("Interval coverage (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(True, color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


def marker(ax, position: float, fraction: float, lower: float, upper: float, hue: str) -> None:
    ax.plot([lower, upper], [position, position], color=hue, linewidth=2.0,
            solid_capstyle="round", zorder=2)
    ax.plot([fraction], [position], marker="o", markersize=5.5, color=hue,
            markeredgecolor="white", markeredgewidth=1.0, zorder=3)


def draw_contrasts(ax, coefficients: pd.DataFrame, summary: dict) -> list[dict]:
    rows: list[dict] = []
    positions, labels = [], []
    total = len(CONTRASTS) + 1

    for index, (name, label) in enumerate(CONTRASTS):
        position = total - index
        record = coefficients.loc[name]
        successes = int(record["coverage_successes"])
        trials = int(record["replicates"])
        fraction = float(record["coverage_fraction"])
        lower = float(record["coverage_exact_95_lower"])
        upper = float(record["coverage_exact_95_upper"])
        marker(ax, position, fraction, lower, upper, STUDY_HUE)
        ax.text(1.04, position, f"{successes}/{trials}", transform=ax.get_yaxis_transform(),
                clip_on=False, va="center", ha="left", fontsize=7, color=INK)
        positions.append(position)
        labels.append(label)
        rows.append({
            "panel": "a", "contrast": name, "label": label,
            "coverage_successes": successes, "replicates": trials,
            "coverage_fraction": fraction,
            "coverage_exact_95_lower": lower, "coverage_exact_95_upper": upper,
        })

    pooled_successes = int(summary["coefficient_interval_coverage_successes"])
    pooled_trials = int(summary["coefficient_interval_coverage_trials"])
    pooled = float(summary["coefficient_interval_coverage_fraction"])
    pooled_lower = float(summary["coefficient_interval_coverage_exact_95_lower"])
    pooled_upper = float(summary["coefficient_interval_coverage_exact_95_upper"])
    marker(ax, 0.0, pooled, pooled_lower, pooled_upper, STUDY_HUE)
    ax.text(1.04, 0.0, f"{pooled_successes}/{pooled_trials}",
            transform=ax.get_yaxis_transform(), clip_on=False,
            va="center", ha="left", fontsize=7, color=INK, fontweight="bold")
    positions.append(0.0)
    labels.append("All contrasts pooled")
    rows.append({
        "panel": "a", "contrast": "pooled", "label": "All contrasts pooled",
        "coverage_successes": pooled_successes, "replicates": pooled_trials,
        "coverage_fraction": pooled,
        "coverage_exact_95_lower": pooled_lower, "coverage_exact_95_upper": pooled_upper,
    })

    coverage_axis(ax)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.set_ylim(-0.75, total + 0.6)
    ax.set_title("a   Coverage by contrast", loc="left", fontweight="bold", pad=9)
    ax.annotate("right column: replicates whose interval covered the truth",
                xy=(0, -0.245), xycoords="axes fraction", fontsize=6.5,
                color=INK_SOFT, ha="left", va="top", annotation_clip=False)
    return rows


def draw_methods(ax, comparators: pd.DataFrame, results: pd.DataFrame,
                 primary: pd.DataFrame, summary: dict) -> list[dict]:
    rows: list[dict] = []
    entries: list[tuple[str, str, str, str]] = [
        ("constrained_bayesian", "Constrained Bayesian", STUDY_HUE, "This study")
    ]
    entries += [(key, label, BENCHMARK_HUE, "Benchmark") for key, label in BENCHMARKS]
    entries += [(key, label, NAIVE_HUE, "Naive handling") for key, label in NAIVE]

    positions, labels = [], []
    for index, (key, label, hue, group) in enumerate(entries):
        # Two blank half-slots separate the three method groups.
        offset = (0.0 if index == 0 else 0.7 if index <= len(BENCHMARKS) else 1.4)
        position = len(entries) - index - offset

        if key == "constrained_bayesian":
            successes = int(summary["coefficient_interval_coverage_successes"])
            trials = int(summary["coefficient_interval_coverage_trials"])
            fraction = float(summary["coefficient_interval_coverage_fraction"])
            lower = float(summary["coefficient_interval_coverage_exact_95_lower"])
            upper = float(summary["coefficient_interval_coverage_exact_95_upper"])
            bias = float(primary["relative_bias_percent"].median())
            diverged = 0
        else:
            block = comparators.loc[comparators["handling_scenario"] == key]
            successes = int(block["coverage_successes"].sum())
            trials = int(block["replicates"].sum())
            fraction = successes / trials
            lower, upper = clopper_pearson(successes, trials)
            raw = results.loc[results["scenario"] == key]
            relative = (raw["irr"] - raw["truth_irr"]) / raw["truth_irr"] * 100.0
            bias = float(relative.median())
            diverged = int((raw["irr"] > DIVERGENCE_THRESHOLD).sum())

        marker(ax, position, fraction, lower, upper, hue)
        note = f"{bias:+.1f}%" + ("†" if diverged else "")
        ax.text(1.04, position, note, transform=ax.get_yaxis_transform(), clip_on=False,
                va="center", ha="left", fontsize=7, color=INK)
        positions.append(position)
        labels.append(label)
        rows.append({
            "panel": "b", "method": key, "label": label, "group": group,
            "coverage_successes": successes, "replicates": trials,
            "coverage_fraction": fraction,
            "coverage_exact_95_lower": lower, "coverage_exact_95_upper": upper,
            "median_relative_bias_percent": bias,
            "estimates_exceeding_1000": diverged,
        })

    coverage_axis(ax)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.set_ylim(min(positions) - 0.75, max(positions) + 0.6)
    ax.set_title("b   Coverage by suppression handling", loc="left",
                 fontweight="bold", pad=9)
    ax.annotate("right column: median relative bias   † 7 of 120 fits diverged",
                xy=(0, -0.245), xycoords="axes fraction", fontsize=6.5,
                color=INK_SOFT, ha="left", va="top", annotation_clip=False)
    return rows


def build(coefficients, comparators, results, primary, summary):
    style()
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.7))
    rows = draw_contrasts(left, coefficients, summary)
    rows += draw_methods(right, comparators, results, primary, summary)

    handles = [
        plt.Line2D([], [], color=STUDY_HUE, linewidth=2.4, label="This study"),
        plt.Line2D([], [], color=BENCHMARK_HUE, linewidth=2.4, label="Benchmark"),
        plt.Line2D([], [], color=NAIVE_HUE, linewidth=2.4, label="Naive handling"),
    ]
    figure.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
                  fontsize=7.5, bbox_to_anchor=(0.5, 0.028))
    figure.text(0.5, -0.005,
                "bars: exact binomial 95% Monte Carlo interval    dashed line: nominal 95% coverage",
                ha="center", va="bottom", fontsize=6.5, color=INK_SOFT)
    figure.subplots_adjust(left=0.155, right=0.905, top=0.90, bottom=0.30, wspace=1.28)
    return figure, rows


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stem", default="figure_calibration_performance")
    args = parser.parse_args(argv)

    summary = require_passed_program()
    coefficients = pd.read_csv(PROGRAM / "coefficient_calibration_summary.csv").set_index("parameter")
    comparators = pd.read_csv(PROGRAM / "comparator_calibration_summary.csv")
    results = pd.read_csv(PROGRAM / "comparator_results.csv")
    primary = pd.read_csv(PROGRAM / "primary_recovery.csv")

    figure, rows = build(coefficients, comparators, results, primary, summary)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    pdf = DESTINATION / f"{args.stem}.pdf"
    png = DESTINATION / f"{args.stem}.png"
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(figure)

    sidecar = {
        "schema_id": "sr_v2_figure_calibration_performance/v1",
        "sources": {
            "calibration_program_summary": "calibration_program/calibration_program_summary.json",
            "coefficient_calibration_summary": "calibration_program/coefficient_calibration_summary.csv",
            "comparator_calibration_summary": "calibration_program/comparator_calibration_summary.csv",
            "comparator_results": "calibration_program/comparator_results.csv",
            "primary_recovery": "calibration_program/primary_recovery.csv",
        },
        "replicates": int(summary["replicates"]),
        "truth_scenarios": sorted(summary["replicates_by_truth_scenario"]),
        "suppressed_cells_total": int(summary["suppressed_cells_total"]),
        "suppressed_cell_weighted_coverage_95": float(summary["suppressed_cell_weighted_coverage_95"]),
        "suppressed_cell_pooled_rmse": float(summary["suppressed_cell_pooled_rmse"]),
        "divergence_threshold_irr": DIVERGENCE_THRESHOLD,
        "interpretation_boundary": summary["interpretation_boundary"],
        "precise_nominal_coverage_claim_authorized": bool(
            summary["precise_nominal_coverage_claim_authorized"]
        ),
        "rows": rows,
    }
    (DESTINATION / f"{args.stem}.json").write_text(
        json.dumps(sidecar, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"figure_pdf={_display(pdf)}")
    print(f"figure_png={_display(png)}")
    print(f"plotted_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
