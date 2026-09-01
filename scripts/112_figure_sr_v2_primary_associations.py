#!/usr/bin/env python3
"""Build the corrected primary-association figure from frozen production evidence.

Panel a shows the posterior rate ratios and 95% credible intervals for the two
prespecified exposures.  Panel b puts the same comparison on an interpretable
absolute scale, using the distribution across counties of posterior mean
mortality rates -- which also shows the two reference categories that a ratio
plot necessarily hides at 1.

The script refuses to run unless the corrected production gate records
``passed: true``, reads only frozen artifacts, and writes a machine-readable
sidecar so every plotted number is traceable to its source file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "outputs/scientific_reports_v2/production_8chain"
DESTINATION = ROOT / "outputs/scientific_reports_v2/figures"

# Categorical slots 1 and 2 of the documented palette.  Validated all-pairs on a
# white print surface: CVD dE 24.7 (protan), normal-vision dE 33.6, both >= 3:1
# against the surface.  Identity is never carried by color alone -- every
# estimate is directly labelled and every category is named on the axis.
RURALITY_HUE = "#2a78d6"
SVI_HUE = "#eb6834"

INK = "#1a1a19"
INK_SOFT = "#55554e"
RULE = "#d5d5cd"

RURALITY_CONTRASTS = [
    ("primary_rurality_metro_other", "Metropolitan, other"),
    ("primary_rurality_nonmetro_adjacent", "Nonmetro, adjacent"),
    ("primary_rurality_nonmetro_nonadjacent", "Nonmetro, nonadjacent"),
]
SVI_CONTRASTS = [
    ("svi_quartile_Q2", "SVI quartile 2"),
    ("svi_quartile_Q3", "SVI quartile 3"),
    ("svi_quartile_Q4_highest", "SVI quartile 4, highest"),
]

RURALITY_LEVELS = [
    ("metro_large", "Metropolitan, large"),
    ("metro_other", "Metropolitan, other"),
    ("nonmetro_adjacent", "Nonmetro, adjacent"),
    ("nonmetro_nonadjacent", "Nonmetro, nonadjacent"),
]
SVI_LEVELS = [
    ("Q1_lowest", "SVI quartile 1, lowest"),
    ("Q2", "SVI quartile 2"),
    ("Q3", "SVI quartile 3"),
    ("Q4_highest", "SVI quartile 4, highest"),
]


def _display(path: Path) -> str:
    """Report a repository-relative path when there is one, else the full path."""

    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require_passed_gate() -> dict:
    gate = json.loads((PRODUCTION / "production_gate.json").read_text(encoding="utf-8"))
    if gate.get("passed") is not True:
        raise SystemExit("Refusing to plot: the corrected production gate has not passed")
    return gate


def style() -> None:
    plt.rcParams.update(
        {
            # Scientific Reports asks for a sans-serif face; fall back cleanly.
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


def draw_forest(ax, summary: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    entries = [(name, label, RURALITY_HUE, "Rurality") for name, label in RURALITY_CONTRASTS]
    entries += [(name, label, SVI_HUE, "Social vulnerability") for name, label in SVI_CONTRASTS]

    positions = []
    for index, (name, label, hue, family) in enumerate(entries):
        # A blank slot between the two families keeps the groups legible.
        position = len(entries) - index - (1 if index >= len(RURALITY_CONTRASTS) else 0)
        positions.append(position)
        row = summary.loc[name]
        mean = float(row["posterior_mean"])
        lower = float(row["credible_interval_lower_95"])
        upper = float(row["credible_interval_upper_95"])
        ax.plot([lower, upper], [position, position], color=hue, linewidth=2.0,
                solid_capstyle="round", zorder=2)
        ax.plot([mean], [position], marker="o", markersize=5.5, color=hue,
                markeredgecolor="white", markeredgewidth=1.0, zorder=3)
        # The value column sits outside the data area so it can never collide
        # with an interval, however wide the interval turns out to be.
        ax.text(1.04, position, f"{mean:.2f}  ({lower:.2f}–{upper:.2f})",
                transform=ax.get_yaxis_transform(), clip_on=False,
                va="center", ha="left", fontsize=7, color=INK)
        rows.append({
            "panel": "a", "family": family, "contrast": name, "label": label,
            "irr_posterior_mean": mean,
            "credible_interval_lower_95": lower,
            "credible_interval_upper_95": upper,
        })

    ax.axvline(1.0, color=INK_SOFT, linewidth=0.7, linestyle=(0, (3, 3)), zorder=1)
    ax.set_yticks(positions)
    ax.set_yticklabels([label for _n, label, _h, _f in entries])
    ax.set_xscale("log")
    ticks = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{value:.1f}" for value in ticks])
    # A log axis otherwise emits minor ticks and a "x 10^0" offset label.
    ax.xaxis.set_minor_locator(ticker.NullLocator())
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.set_xlim(0.975, 1.55)
    ax.set_ylim(-0.6, len(entries) + 0.2)
    ax.set_xlabel("Mortality rate ratio (log scale)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(True, color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("a   Posterior rate ratios", loc="left", fontweight="bold", pad=9)
    ax.annotate("dashed line: no difference from the reference category",
                xy=(0, -0.255), xycoords="axes fraction", fontsize=6.5,
                color=INK_SOFT, ha="left", va="top", annotation_clip=False)
    return rows


def draw_absolute(ax, counties: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    entries = [("primary_rurality", key, label, RURALITY_HUE, "Rurality", key == "metro_large")
               for key, label in RURALITY_LEVELS]
    entries += [("svi_quartile", key, label, SVI_HUE, "Social vulnerability", key == "Q1_lowest")
                for key, label in SVI_LEVELS]

    positions, labels, ceiling = [], [], 0.0
    for index, (column, key, label, hue, family, is_reference) in enumerate(entries):
        position = len(entries) - index - (1 if index >= len(RURALITY_LEVELS) else 0)
        positions.append(position)
        labels.append(label + ("  (ref.)" if is_reference else ""))
        values = counties.loc[counties[column] == key, "posterior_mean_rate_per_100k"]
        p5, q1, median, q3, p95 = np.percentile(values, [5, 25, 50, 75, 95])
        ceiling = max(ceiling, float(p95))
        ax.plot([p5, p95], [position, position], color=hue, linewidth=0.9,
                solid_capstyle="butt", zorder=2)
        # A white edge keeps adjacent fills from touching.
        ax.add_patch(plt.Rectangle((q1, position - 0.26), q3 - q1, 0.52,
                                   facecolor=hue, edgecolor="white", linewidth=1.0,
                                   alpha=0.5 if is_reference else 0.9, zorder=3))
        ax.plot([median, median], [position - 0.26, position + 0.26], color=INK,
                linewidth=1.2, zorder=4)
        rows.append({
            "panel": "b", "family": family, "category": key, "label": label,
            "counties": int(values.size), "is_reference": bool(is_reference),
            "rate_per_100k_p5": float(p5), "rate_per_100k_q1": float(q1),
            "rate_per_100k_median": float(median), "rate_per_100k_q3": float(q3),
            "rate_per_100k_p95": float(p95),
        })

    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", pad=6)
    ax.set_xlim(0, ceiling * 1.06)
    ax.set_ylim(-0.6, len(entries) + 0.2)
    ax.set_xlabel("County posterior mean rate per 100,000")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(True, color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("b   Absolute scale across counties", loc="left", fontweight="bold", pad=9)
    ax.annotate("box: interquartile range   line: median   whisker: 5th–95th percentile",
                xy=(0, -0.255), xycoords="axes fraction", fontsize=6.5,
                color=INK_SOFT, ha="left", va="top", annotation_clip=False)
    return rows


def build(counties: pd.DataFrame, summary: pd.DataFrame) -> tuple[plt.Figure, list[dict]]:
    style()
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.6))
    rows = draw_forest(left, summary) + draw_absolute(right, counties)

    handles = [
        plt.Line2D([], [], color=RURALITY_HUE, linewidth=2.4, label="Rurality"),
        plt.Line2D([], [], color=SVI_HUE, linewidth=2.4, label="Social vulnerability"),
    ]
    figure.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
                  fontsize=7.5, bbox_to_anchor=(0.5, -0.012))
    # Panel a owns the centre gutter for its value column; panel b's category
    # labels are mirrored to the outer right edge.
    figure.subplots_adjust(left=0.155, right=0.80, top=0.90, bottom=0.27, wspace=0.92)
    return figure, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stem", default="figure_primary_associations")
    args = parser.parse_args(argv)

    gate = require_passed_gate()
    summary = pd.read_csv(PRODUCTION / "posterior_primary_summary.csv").set_index("parameter")
    counties = pd.read_csv(
        PRODUCTION / "county_posterior_summary.csv",
        dtype={"county_fips": str, "state_fips": str},
    )

    figure, rows = build(counties, summary)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    pdf = DESTINATION / f"{args.stem}.pdf"
    png = DESTINATION / f"{args.stem}.png"
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(figure)

    sidecar = {
        "schema_id": "sr_v2_figure_primary_associations/v1",
        "sources": {
            "posterior_primary_summary": "production_8chain/posterior_primary_summary.csv",
            "county_posterior_summary": "production_8chain/county_posterior_summary.csv",
            "production_gate": "production_8chain/production_gate.json",
        },
        "production_gate_generated_utc": gate["generated_utc"],
        "counties": int(len(counties)),
        "panel_b_interval": "box spans the interquartile range; whiskers span the 5th to 95th percentile across counties",
        "interpretation_boundary": (
            "County posterior rates are model-derived ecological estimates, not observed or "
            "recovered suppressed counts."
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
