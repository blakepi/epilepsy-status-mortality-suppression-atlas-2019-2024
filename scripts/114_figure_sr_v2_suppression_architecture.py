#!/usr/bin/env python3
"""Build the suppression-and-constraint architecture figure.

Panel a shows how publication status varies across the rurality gradient, which
is why dropping suppressed cells is not a neutral analytic choice.  Panel b
works one real county end to end, using only quantities CDC WONDER already
publishes.  Panel c reports what the public equality system actually pins down.

Every value is recomputed here from the frozen model frame and the frozen
constraint-geometry artifact; nothing is transcribed by hand.  A sidecar records
each plotted number with the file it came from.
"""

from __future__ import annotations

import argparse
import itertools
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_FRAME = ROOT / "data/processed/bayes_constrained/model_frame.parquet"
GEOMETRY = ROOT / "outputs/scientific_reports_v2/constraint_geometry/constraint_geometry.json"
DESTINATION = ROOT / "outputs/scientific_reports_v2/figures"

# Documented categorical slots 1-3.  Validated all-pairs on a white print
# surface: worst CVD dE 9.2, worst normal-vision dE 24.0.  The aqua slot sits
# below 3:1 against white, so every segment carries a visible label.
EXACT_HUE = "#2a78d6"
SUPPRESSED_HUE = "#eb6834"
ZERO_HUE = "#1baf7a"
# One-hue ordinal pair inside panel b: the published bound versus what the
# published county total leaves feasible.
SUPPRESSED_TINT = "#f7c4ac"
FREE_FILL = "#c9c9c0"

INK = "#1a1a19"
INK_SOFT = "#55554e"
RULE = "#d5d5cd"

STATUS_ORDER = [
    ("exact", "Published exact count", EXACT_HUE),
    ("suppressed_1_9", "Suppressed (1–9)", SUPPRESSED_HUE),
    ("zero", "Published zero", ZERO_HUE),
]
RURALITY_ORDER = [
    ("metro_large", "Metropolitan, large"),
    ("metro_other", "Metropolitan, other"),
    ("nonmetro_adjacent", "Nonmetro, adjacent"),
    ("nonmetro_nonadjacent", "Nonmetro, nonadjacent"),
]
EXAMPLE_FIPS = "01025"


def _display(path: Path) -> str:
    """Report a repository-relative path when there is one, else the full path."""

    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def draw_status_by_rurality(ax, frame: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    counts = pd.crosstab(frame["primary_rurality"], frame["q002_count_status"])
    shares = counts.div(counts.sum(axis=1), axis=0) * 100.0

    positions = list(range(len(RURALITY_ORDER) - 1, -1, -1))
    for position, (key, label) in zip(positions, RURALITY_ORDER):
        left = 0.0
        for status, status_label, hue in STATUS_ORDER:
            width = float(shares.loc[key, status])
            # A 2px surface gap keeps adjacent segments from touching.
            ax.barh(position, width, left=left, height=0.62, color=hue,
                    edgecolor="white", linewidth=1.0, zorder=3)
            if width >= 6.0:
                ax.text(left + width / 2.0, position, f"{width:.1f}%", ha="center",
                        va="center", fontsize=6.8, color="white", zorder=4)
            elif status == "exact":
                # The vanishing category is the point of the panel: label it
                # outside the bar rather than dropping the label.
                ax.text(left + width + 0.8, position, f"{width:.1f}%", ha="left",
                        va="center", fontsize=6.8, color=INK, zorder=4)
            left += width
            rows.append({
                "panel": "a", "rurality": key, "rurality_label": label,
                "status": status, "status_label": status_label,
                "county_years": int(counts.loc[key, status]),
                "percent_of_county_years": round(width, 4),
            })

    ax.set_yticks(positions)
    ax.set_yticklabels([label for _key, label in RURALITY_ORDER])
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.65, len(RURALITY_ORDER) - 0.35)
    ax.set_xlabel("Percent of county-years, 2019–2024")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.xaxis.grid(True, color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("a   Publication status across the rurality gradient", loc="left",
                 fontweight="bold", pad=9)

    handles = [plt.Rectangle((0, 0), 1, 1, color=hue) for _s, _l, hue in STATUS_ORDER]
    ax.legend(handles, [label for _s, label, _h in STATUS_ORDER], loc="upper center",
              bbox_to_anchor=(0.5, -0.36), ncol=3, frameon=False, fontsize=7.2,
              handlelength=1.1, handleheight=1.1, columnspacing=1.6)
    return rows


def draw_worked_county(ax, frame: pd.DataFrame) -> tuple[list[dict], dict]:
    county = frame[frame["county_fips"] == EXAMPLE_FIPS].sort_values("year")
    total = int(county["q001_period_exact_count"].iloc[0])
    suppressed_years = county.loc[county["q002_count_status"] == "suppressed_1_9", "year"].tolist()

    # Enumerate every integer allocation the public data admits, so the counts
    # and the tightened per-year range are derived rather than asserted.
    feasible = [
        combo
        for combo in itertools.product(range(1, 10), repeat=len(suppressed_years))
        if sum(combo) == total
    ]
    feasible_array = np.array(feasible)
    tightened_low = int(feasible_array.min())
    tightened_high = int(feasible_array.max())
    unconstrained = 9 ** len(suppressed_years)
    # Given only the sum constraint the suppressed years are exchangeable, so
    # one column characterises the marginal for all of them.
    marginal = {
        int(value): int((feasible_array[:, 0] == value).sum())
        for value in range(tightened_low, tightened_high + 1)
    }

    rows: list[dict] = []
    positions = list(range(len(county) - 1, -1, -1))
    for position, (_index, record) in zip(positions, county.iterrows()):
        year = int(record["year"])
        status = str(record["q002_count_status"])
        if status == "suppressed_1_9":
            ax.barh(position, 9 - 1, left=1, height=0.5, color=SUPPRESSED_TINT,
                    edgecolor="white", linewidth=1.0, zorder=2)
            ax.barh(position, tightened_high - tightened_low, left=tightened_low,
                    height=0.5, color=SUPPRESSED_HUE, edgecolor="white",
                    linewidth=1.0, zorder=3)
            rows.append({
                "panel": "b", "year": year, "status": status,
                "published_lower": 1, "published_upper": 9,
                "feasible_lower": tightened_low, "feasible_upper": tightened_high,
            })
        else:
            ax.plot([0], [position], marker="o", markersize=6, color=ZERO_HUE,
                    markeredgecolor="white", markeredgewidth=1.0, zorder=3)
            ax.text(0.45, position, "0", ha="left", va="center", fontsize=7, color=INK)
            rows.append({
                "panel": "b", "year": year, "status": status,
                "published_lower": 0, "published_upper": 0,
                "feasible_lower": 0, "feasible_upper": 0,
            })

    ax.set_yticks(positions)
    ax.set_yticklabels([str(int(year)) for year in county["year"]])
    ax.set_xlim(-0.4, 10)
    ax.set_ylim(-0.75, len(county) - 0.25)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_xlabel("Deaths in the county-year")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.xaxis.grid(True, color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    name = f"{county['county_name'].iloc[0]}, {county['state_name'].iloc[0]}"
    ax.set_title(f"b   One county: {name}", loc="left", fontweight="bold", pad=9)

    caption = (
        f"The 1–9 bounds alone admit {unconstrained:,} integer allocations. The published "
        f"six-year total of {total} cuts that to {len(feasible)} ({unconstrained // len(feasible)}x "
        f"fewer) and tightens every suppressed year to {tightened_low}–{tightened_high} (solid, "
        f"against the pale published bound). Setting each suppressed year to 5 would imply "
        f"{5 * len(suppressed_years)} deaths; dropping them entirely would imply 0."
    )

    example = {
        "county_fips": EXAMPLE_FIPS, "county_name": name,
        "rurality": str(county["primary_rurality"].iloc[0]),
        "svi_quartile": str(county["svi_quartile"].iloc[0]),
        "published_period_total": total,
        "suppressed_years": [int(year) for year in suppressed_years],
        "feasible_allocations": len(feasible),
        "feasible_per_year_lower": tightened_low,
        "feasible_per_year_upper": tightened_high,
        "naive_suppressed_equals_5_total": 5 * len(suppressed_years),
        "naive_suppressed_equals_9_total": 9 * len(suppressed_years),
        "visible_only_total": 0,
        "allocations_under_bounds_only": unconstrained,
        "feasible_set_reduction_factor": unconstrained // len(feasible),
        "feasible_marginal_counts_per_suppressed_year": marginal,
    }
    return rows, example, caption


def draw_dimensionality(ax, geometry: dict) -> list[dict]:
    latent = int(geometry["latent_variables"])
    independent = int(geometry["independent_equalities"])
    nullity = int(geometry["equality_nullity"])
    assert latent - independent == nullity, "constraint geometry is internally inconsistent"

    ax.barh(0, independent, height=0.46, color=EXACT_HUE, edgecolor="white",
            linewidth=1.0, zorder=3)
    ax.barh(0, nullity, left=independent, height=0.46, color=FREE_FILL,
            edgecolor="white", linewidth=1.0, zorder=3)
    ax.text(independent / 2.0, 0, f"{independent:,}", ha="center", va="center",
            fontsize=6.8, color="white", zorder=4)
    ax.text(independent + nullity / 2.0, 0, f"{nullity:,} free dimensions",
            ha="center", va="center", fontsize=7.2, color=INK, zorder=4)

    ax.set_xlim(0, latent)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xticks([0, 2500, 5000, 7500, latent])
    ax.set_xticklabels(["0", "2,500", "5,000", "7,500", f"{latent:,}"])
    ax.set_xlabel("Suppressed county-year cells (latent variables)")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.xaxis.grid(True, color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("c   What the public equalities pin down", loc="left",
                 fontweight="bold", pad=9)

    nominal = (int(geometry["nominal_county_period_equalities"])
               + int(geometry["nominal_state_year_equalities"])
               + int(geometry["nominal_national_year_equalities"])
               + int(geometry["nominal_grand_total_equalities"]))
    dependent = nominal - independent - int(geometry["zero_information_equalities"])
    caption = (
        f"{nominal:,} nominal equalities reduce to {independent:,} independent rows: "
        f"{int(geometry['zero_information_equalities']):,} carry no information and {dependent} are "
        f"algebraically implied. They fix {independent / latent:.0%} of the latent dimensions, so the "
        f"public constraints bound the suppressed counts without identifying them."
    )

    return caption, [{
        "panel": "c", "latent_variables": latent, "nominal_equalities": nominal,
        "zero_information_equalities": int(geometry["zero_information_equalities"]),
        "algebraically_implied_equalities": dependent,
        "independent_equalities": independent, "equality_nullity": nullity,
        "fraction_of_latent_dimensions_fixed": round(independent / latent, 6),
    }]


def build(frame: pd.DataFrame, geometry: dict) -> tuple[plt.Figure, list[dict], dict]:
    style()
    figure = plt.figure(figsize=(7.2, 6.1))
    # The bottom band is reserved for the two panel captions, so neither can
    # collide with the other or run past the figure edge.
    grid = figure.add_gridspec(2, 2, height_ratios=[1.0, 1.0],
                               width_ratios=[1.0, 1.0], hspace=0.95, wspace=0.30,
                               left=0.155, right=0.985, top=0.93, bottom=0.235)
    top = figure.add_subplot(grid[0, :])
    lower_left = figure.add_subplot(grid[1, 0])
    lower_right = figure.add_subplot(grid[1, 1])

    rows = draw_status_by_rurality(top, frame)
    worked_rows, example, worked_caption = draw_worked_county(lower_left, frame)
    rows += worked_rows
    geometry_caption, geometry_rows = draw_dimensionality(lower_right, geometry)
    rows += geometry_rows

    for axes, caption in ((lower_left, worked_caption), (lower_right, geometry_caption)):
        box = axes.get_position()
        # Wrap to the panel's own width so long captions stay inside their column.
        characters = max(28, int(box.width * figure.get_figwidth() / 0.0455))
        figure.text(box.x0, 0.165, textwrap.fill(caption, characters), fontsize=6.6,
                    color=INK_SOFT, ha="left", va="top", linespacing=1.55)
    return figure, rows, example


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stem", default="figure_suppression_architecture")
    args = parser.parse_args(argv)

    frame = pd.read_parquet(MODEL_FRAME)
    geometry = json.loads(GEOMETRY.read_text(encoding="utf-8"))

    figure, rows, example = build(frame, geometry)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    pdf = DESTINATION / f"{args.stem}.pdf"
    png = DESTINATION / f"{args.stem}.png"
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(figure)

    sidecar = {
        "schema_id": "sr_v2_figure_suppression_architecture/v1",
        "sources": {
            "model_frame": "data/processed/bayes_constrained/model_frame.parquet",
            "constraint_geometry": "outputs/scientific_reports_v2/constraint_geometry/constraint_geometry.json",
        },
        "county_years": int(len(frame)),
        "counties": int(frame["county_fips"].nunique()),
        "worked_example": example,
        "disclosure_boundary": (
            "Panel b shows only quantities CDC WONDER already publishes: the suppression "
            "flag, its 1-9 bound, and the published county total. No model-derived estimate "
            "for a named county appears in this figure."
        ),
        "rows": rows,
    }
    (DESTINATION / f"{args.stem}.json").write_text(
        json.dumps(sidecar, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"figure_pdf={_display(pdf)}")
    print(f"figure_png={_display(png)}")
    print(f"plotted_rows={len(rows)}")
    print(f"feasible_allocations={example['feasible_allocations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
