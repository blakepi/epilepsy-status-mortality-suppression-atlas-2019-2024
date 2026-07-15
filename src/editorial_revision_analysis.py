from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE14 = PROJECT_ROOT / "manuscript" / "phase14_targeted_cleanup"
OUT = PROJECT_ROOT / "manuscript" / "editorial_revision_ready"
OUT_TABLES = OUT / "tables"
OUT_FIGURES = OUT / "figures"
OUT_REPORTS = OUT / "reports"


TOTAL_MCOD = 58380.0
TOTAL_UCD = 22306.0


def load_module(path: Path, name: str):
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_dirs() -> None:
    for path in [OUT, OUT_TABLES, OUT_FIGURES, OUT_REPORTS]:
        path.mkdir(parents=True, exist_ok=True)


def fmt_ci(row: pd.Series, low_col: str = "ci_low", high_col: str = "ci_high") -> str:
    return f"{row[low_col]:.2f}-{row[high_col]:.2f}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scenario_label(name: str) -> str:
    labels = {
        "observed_exact_positive_only": "Observed exact-positive only",
        "observed_exact_plus_zero": "Observed exact plus explicit zero",
        "suppressed_equals_1": "Suppressed = 1",
        "suppressed_equals_mean_4_06": "Suppressed = 4.06 (constant mean)",
        "suppressed_equals_4": "Suppressed = 4",
        "suppressed_equals_5": "Suppressed = 5",
        "suppressed_equals_9": "Suppressed = 9",
        "population_scaled_residual_allocation": "Population-scaled residual allocation",
        "conservative_anti_rural_allocation": "Conservative anti-rural residual allocation",
        "pro_rural_allocation": "Pro-rural residual allocation",
        "interval_likelihood": "Interval-likelihood negative binomial",
    }
    return labels.get(name, name.replace("_", " "))


def scenario_tier(name: str) -> str:
    if name.startswith("observed"):
        return "Visible-only"
    if name in {
        "population_scaled_residual_allocation",
        "conservative_anti_rural_allocation",
        "pro_rural_allocation",
    }:
        return "Residual-allocation, total-preserving"
    if name.startswith("interval"):
        return "Interval model"
    if name == "suppressed_equals_mean_4_06":
        return "Constant-count stress test, total-preserving"
    return "Fixed-value stress test, not total-preserving"


def build_revised_model_outputs() -> dict:
    m04 = load_module(PROJECT_ROOT / "src" / "04_suppression_bounds_models.py", "phase04_models")
    county = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "county_period_analysis.csv", dtype={"county_fips": str})
    base = county[~county["aggregate_total_indicator"]].copy()
    exact_sum = pd.to_numeric(base.loc[base["death_status"].eq("exact"), "deaths_exact"], errors="coerce").sum()
    suppressed_mask = base["death_status"].eq("suppressed_1_9")
    suppressed_rows = int(suppressed_mask.sum())
    residual = TOTAL_MCOD - exact_sum
    residual_mean = residual / suppressed_rows

    scenarios = m04.make_scenarios(county)
    mean_scenario = base.copy()
    mean_scenario["modeled_deaths"] = np.where(
        mean_scenario["death_status"].eq("suppressed_1_9"),
        residual_mean,
        mean_scenario["death_lower"],
    )
    scenarios["suppressed_equals_mean_4_06"] = mean_scenario

    result_frames = []
    fit_rows = []
    for scenario in [
        "observed_exact_positive_only",
        "observed_exact_plus_zero",
        "suppressed_equals_1",
        "suppressed_equals_mean_4_06",
        "suppressed_equals_5",
        "suppressed_equals_9",
        "population_scaled_residual_allocation",
        "conservative_anti_rural_allocation",
        "pro_rural_allocation",
    ]:
        sdf = scenarios[scenario]
        for family_name, include_svi, include_components in [
            ("rurality_only", False, False),
            ("rurality_svi_composite", True, False),
            ("acs_component_family", False, True),
        ]:
            res, fit = m04.fit_model(
                sdf,
                scenario,
                family_name,
                include_svi=include_svi,
                include_components=include_components,
            )
            result_frames.append(res)
            fit_rows.append(fit)

    results = pd.concat(result_frames, ignore_index=True)
    fits = pd.DataFrame(fit_rows)

    original_results = pd.read_csv(PHASE14 / "tables" / "suppression_bounds_model_results.csv")
    interval = pd.read_csv(PHASE14 / "tables" / "interval_model_results.csv")
    interval_focus = interval[
        interval["term"].isin(
            [
                "primary_rurality_metro_other",
                "primary_rurality_nonmetro_adjacent",
                "primary_rurality_nonmetro_nonadjacent",
                "svi_quartile_Q4_highest",
            ]
        )
    ].copy()
    interval_focus["scenario"] = "interval_likelihood"
    interval_focus["model_family"] = interval_focus["model_family"].str.replace("interval_nb_", "interval_nb_", regex=False)
    interval_focus["model_type"] = "interval_likelihood_negative_binomial"
    interval_focus["ci_low"] = interval_focus["ci_low_approx"]
    interval_focus["ci_high"] = interval_focus["ci_high_approx"]
    interval_focus["se"] = interval_focus["se_approx"]
    interval_focus["p_value"] = np.nan
    interval_focus["events"] = np.nan
    interval_focus = interval_focus.reindex(columns=results.columns)

    revised_full = pd.concat([results, interval_focus], ignore_index=True)
    revised_full.to_csv(OUT_TABLES / "table3_suppression_aware_models_revised_full.csv", index=False)
    fits.to_csv(OUT_TABLES / "model_fit_summary_revised.csv", index=False)

    assignment_rows = []
    for name in [
        "observed_exact_positive_only",
        "observed_exact_plus_zero",
        "suppressed_equals_1",
        "suppressed_equals_mean_4_06",
        "suppressed_equals_5",
        "suppressed_equals_9",
        "population_scaled_residual_allocation",
        "conservative_anti_rural_allocation",
        "pro_rural_allocation",
    ]:
        sdf = scenarios[name]
        total = float(pd.to_numeric(sdf["modeled_deaths"], errors="coerce").sum())
        assignment_rows.append(
            {
                "scenario": name,
                "label": scenario_label(name),
                "tier": scenario_tier(name),
                "assigned_deaths_all_counties": round(total, 6),
                "difference_from_reconciled_total": round(total - TOTAL_MCOD, 6),
                "suppressed_rows_included": int(sdf["death_status"].eq("suppressed_1_9").sum()),
                "notes": "",
            }
        )
    pd.DataFrame(assignment_rows).to_csv(OUT_TABLES / "suppression_scenario_death_assignments_revised.csv", index=False)

    focus = revised_full[
        revised_full["term"].eq("primary_rurality_nonmetro_nonadjacent")
        & (
            revised_full["model_family"].eq("rurality_svi_composite")
            | revised_full["model_family"].eq("interval_nb_rurality_svi")
        )
    ].copy()
    order = [
        "observed_exact_positive_only",
        "observed_exact_plus_zero",
        "suppressed_equals_1",
        "suppressed_equals_mean_4_06",
        "suppressed_equals_5",
        "suppressed_equals_9",
        "population_scaled_residual_allocation",
        "conservative_anti_rural_allocation",
        "pro_rural_allocation",
        "interval_likelihood",
    ]
    focus["scenario_order"] = focus["scenario"].map({name: i for i, name in enumerate(order)})
    focus = focus.sort_values("scenario_order")
    assignment_map = {r["scenario"]: r for r in assignment_rows}
    main_rows = []
    for _, row in focus.iterrows():
        scen = row["scenario"]
        assigned = assignment_map.get(scen, {}).get("assigned_deaths_all_counties", "")
        diff = assignment_map.get(scen, {}).get("difference_from_reconciled_total", "")
        if scen == "interval_likelihood":
            assigned_text = "Not assigned"
            notes = "Uses interval likelihood; known suppressed-cell total not imposed."
        elif scen == "suppressed_equals_mean_4_06":
            assigned_text = f"{assigned:,.0f}"
            notes = "Preserves total as a constant-count stress test; equal assignment concentrates rate influence in lower-population suppressed counties."
        elif isinstance(assigned, (float, int)):
            assigned_text = f"{assigned:,.0f}"
            if abs(float(diff)) < 1e-6:
                notes = "Preserves the reconciled national total."
            elif float(diff) > 0:
                notes = f"Exceeds reconciled total by {float(diff):,.0f} deaths."
            else:
                notes = f"Falls short of reconciled total by {abs(float(diff)):,.0f} deaths."
        else:
            assigned_text = ""
            notes = ""
        main_rows.append(
            {
                "tier": scenario_tier(scen),
                "scenario": scenario_label(scen),
                "assigned_deaths": assigned_text,
                "nonmetro_nonadjacent_irr": f"{row['irr']:.2f}",
                "ci_95": fmt_ci(row),
                "notes": notes,
            }
        )
    write_csv(
        OUT_TABLES / "table3_suppression_aware_models_revised_main.csv",
        main_rows,
        ["tier", "scenario", "assigned_deaths", "nonmetro_nonadjacent_irr", "ci_95", "notes"],
    )

    audit = {
        "total_mcod": TOTAL_MCOD,
        "exact_county_deaths": exact_sum,
        "suppressed_rows": suppressed_rows,
        "suppressed_residual": residual,
        "mean_deaths_per_suppressed_row": residual_mean,
        "population_scaled_total": assignment_map["population_scaled_residual_allocation"]["assigned_deaths_all_counties"],
        "conservative_total": assignment_map["conservative_anti_rural_allocation"]["assigned_deaths_all_counties"],
        "pro_rural_total": assignment_map["pro_rural_allocation"]["assigned_deaths_all_counties"],
    }
    (OUT_REPORTS / "suppression_reconciliation_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def build_main_tables() -> None:
    src = PHASE14 / "tables"
    t1 = pd.read_csv(src / "table1_county_characteristics.csv")
    t1_out = t1.copy()
    t1_out["death_status"] = t1_out["death_status"].map(
        {"exact": "Exact", "suppressed_1_9": "Suppressed 1-9", "zero": "Explicit zero"}
    ).fillna(t1_out["death_status"])
    t1_out["person_years_millions"] = t1_out["person_years"] / 1_000_000
    t1_main = t1_out[
        [
            "death_status",
            "counties",
            "person_years_millions",
            "exact_deaths",
            "lower",
            "upper",
            "pct_nonmetro",
            "mean_svi",
            "mean_poverty",
            "mean_uninsured",
            "mean_age65",
        ]
    ].copy()
    t1_main.to_csv(OUT_TABLES / "table1_county_characteristics_revised.csv", index=False)

    t2 = pd.read_csv(src / "table2_mortality_by_rurality_svi.csv")
    t2["primary_rurality"] = t2["primary_rurality"].fillna("Unmatched covariates")
    t2["svi_quartile"] = t2["svi_quartile"].fillna("Unmatched")
    t2_main = t2[
        [
            "primary_rurality",
            "svi_quartile",
            "counties",
            "lower",
            "midpoint",
            "upper",
            "suppressed",
            "zero",
            "rate_lower_per_100k",
            "rate_midpoint_per_100k",
            "rate_upper_per_100k",
        ]
    ].copy()
    t2_main.to_csv(OUT_TABLES / "table2_mortality_by_rurality_svi_revised.csv", index=False)

    t4 = pd.read_csv(src / "table4_temporal_context.csv")
    national = t4[t4["source"].eq("national_year")].copy()
    covid = pd.read_csv(src / "covid_by_urbanization_year.csv")
    covid_year = covid.groupby("year", as_index=False).agg(covid_lower=("lower", "sum"), covid_upper=("upper", "sum"))
    t4_main = national.merge(covid_year, on="year", how="left")
    t4_main["covid_midpoint"] = (t4_main["covid_lower"] + t4_main["covid_upper"]) / 2
    t4_main["covid_pct_of_mcod"] = np.where(t4_main["deaths"] > 0, t4_main["covid_midpoint"] / t4_main["deaths"] * 100, np.nan)
    t4_main[["year", "deaths", "population", "rate_per_100k", "covid_lower", "covid_upper", "covid_pct_of_mcod"]].to_csv(
        OUT_TABLES / "table4_temporal_covid_context_revised.csv", index=False
    )

    ucd = pd.read_csv(src / "table5_ucd_sensitivity.csv")
    status = ucd[ucd["section"].eq("ucd_county_suppression_profile")][["death_count_status", "rows"]].copy()
    status_map = dict(zip(status["death_count_status"], status["rows"]))
    t5_rows = [
        {
            "measure": "National aggregate deaths",
            "mcod_g40_g41": "58,380",
            "ucd_g40_g41": "22,306",
            "interpretation": "MCOD is the broader death-certificate mention construct.",
        },
        {
            "measure": "Exact county deaths",
            "mcod_g40_g41": "51,388",
            "ucd_g40_g41": "16,650",
            "interpretation": "Visible exact deaths are lower in UCD sensitivity.",
        },
        {
            "measure": "Exact county rows",
            "mcod_g40_g41": "1,085",
            "ucd_g40_g41": f"{int(status_map.get('exact', 0)):,}",
            "interpretation": "Rows are county-period rows.",
        },
        {
            "measure": "Suppressed county rows",
            "mcod_g40_g41": "1,722",
            "ucd_g40_g41": f"{int(status_map.get('suppressed_1_9', 0)):,}",
            "interpretation": "Suppressed rows remain 1-9 intervals, not zero.",
        },
        {
            "measure": "Explicit-zero county rows",
            "mcod_g40_g41": "335",
            "ucd_g40_g41": f"{int(status_map.get('zero', 0)):,}",
            "interpretation": "Explicit zeros are distinct from suppression.",
        },
    ]
    write_csv(OUT_TABLES / "table5_ucd_sensitivity_revised.csv", t5_rows, ["measure", "mcod_g40_g41", "ucd_g40_g41", "interpretation"])


def plot_revised_forest() -> None:
    focus = pd.read_csv(OUT_TABLES / "table3_suppression_aware_models_revised_full.csv")
    focus = focus[
        focus["term"].eq("primary_rurality_nonmetro_nonadjacent")
        & (
            focus["model_family"].eq("rurality_svi_composite")
            | focus["model_family"].eq("interval_nb_rurality_svi")
        )
    ].copy()
    order = [
        "observed_exact_positive_only",
        "observed_exact_plus_zero",
        "suppressed_equals_1",
        "suppressed_equals_mean_4_06",
        "suppressed_equals_5",
        "suppressed_equals_9",
        "population_scaled_residual_allocation",
        "conservative_anti_rural_allocation",
        "pro_rural_allocation",
        "interval_likelihood",
    ]
    focus["order"] = focus["scenario"].map({s: i for i, s in enumerate(order)})
    focus = focus.sort_values("order", ascending=False)
    colors = {
        "Visible-only": "#6b7280",
        "Fixed-value stress test, not total-preserving": "#b45309",
        "Constant-count stress test, total-preserving": "#d97706",
        "Residual-allocation, total-preserving": "#1f4e79",
        "Interval model": "#047857",
    }
    labels = [scenario_label(s) for s in focus["scenario"]]
    tiers = [scenario_tier(s) for s in focus["scenario"]]
    y = np.arange(len(focus))
    fig, ax = plt.subplots(figsize=(8.2, 5.8))
    for idx, (_, row) in enumerate(focus.iterrows()):
        tier = scenario_tier(row["scenario"])
        ax.errorbar(
            row["irr"],
            idx,
            xerr=[[row["irr"] - row["ci_low"]], [row["ci_high"] - row["irr"]]],
            fmt="o",
            color=colors[tier],
            ecolor=colors[tier],
            capsize=3,
            markersize=5,
        )
    ax.axvline(1.0, color="#111827", linestyle="--", linewidth=1)
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Nonmetro nonadjacent incidence rate ratio (95% CI), log scale")
    ax.set_title("Suppression-scenario sensitivity, rurality + SVI model")
    handles = [Patch(facecolor=color, label=tier) for tier, color in colors.items()]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=7, frameon=True, ncol=2)
    ax.grid(axis="x", color="#e5e7eb", linewidth=0.8)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(OUT_FIGURES / "figure2_suppression_bounds_revised.png", dpi=240)
    plt.close(fig)


def plot_temporal_covid() -> None:
    src = PHASE14 / "tables"
    temporal = pd.read_csv(src / "table4_temporal_context.csv")
    urban = temporal[temporal["source"].eq("urbanization_year")].copy()
    covid = pd.read_csv(src / "covid_by_urbanization_year.csv")
    covid_year = covid.groupby("year", as_index=False).agg(lower=("lower", "sum"), upper=("upper", "sum"))
    covid_year["mid"] = (covid_year["lower"] + covid_year["upper"]) / 2
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 7.0), sharex=True, gridspec_kw={"height_ratios": [2.1, 1]})
    ax = axes[0]
    palette = {
        "Large Central Metro": "#1f4e79",
        "Large Fringe Metro": "#2c7fb8",
        "Medium Metro": "#41b6c4",
        "Small Metro": "#7fcdbb",
        "Micropolitan (Nonmetro)": "#f59e0b",
        "NonCore (Nonmetro)": "#b45309",
        "Not Available": "#9ca3af",
    }
    for name, group in urban.groupby("urbanization"):
        group = group.sort_values("year")
        style = "--" if name == "Not Available" else "-"
        alpha = 0.6 if name == "Not Available" else 0.95
        ax.plot(group["year"], group["deaths"], marker="o", linewidth=1.8, linestyle=style, alpha=alpha, label=name, color=palette.get(name, None))
    ax.set_ylabel("MCOD G40/G41 deaths")
    ax.set_title("Urbanization-year MCOD deaths and COVID-19 co-mention context, 2019-2024")
    ax.grid(axis="y", color="#e5e7eb")
    ax.legend(fontsize=7, ncol=2, frameon=True)
    ax2 = axes[1]
    ax2.bar(covid_year["year"], covid_year["mid"], color="#7c3aed", alpha=0.85, label="COVID co-mention midpoint")
    yerr = np.vstack([covid_year["mid"] - covid_year["lower"], covid_year["upper"] - covid_year["mid"]])
    ax2.errorbar(covid_year["year"], covid_year["mid"], yerr=yerr, fmt="none", ecolor="#4c1d95", capsize=3)
    ax2.set_ylabel("COVID co-mention deaths")
    ax2.set_xlabel("Year")
    ax2.set_xticks([2019, 2020, 2021, 2022, 2023, 2024])
    ax2.grid(axis="y", color="#e5e7eb")
    ax2.legend(fontsize=8, frameon=True)
    fig.text(0.01, 0.01, "Panel A uses death counts because urbanization-year denominators were unavailable for 2022-2024 in the staged table; national rates are reported in Table 4.", fontsize=7)
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    fig.savefig(OUT_FIGURES / "figure4_temporal_covid_context_revised.png", dpi=240)
    plt.close(fig)


def plot_revised_status_map() -> None:
    m08 = load_module(PROJECT_ROOT / "src" / "08_make_maps_and_figures.py", "phase08_figures")
    features = m08.load_features()
    county = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "county_period_analysis.csv", dtype={"county_fips": str})
    values = county.set_index("county_fips")["death_status"].to_dict()
    colors = {
        "exact": "#1f4e79",
        "suppressed_1_9": "#d97706",
        "zero": "#4b5563",
        "missing_unmatched": "#f3f4f6",
    }
    hatches = {"zero": "///", "missing_unmatched": "..."}
    fig, ax = plt.subplots(figsize=(10.8, 6.8))
    for status in ["exact", "suppressed_1_9", "zero", "missing_unmatched"]:
        patches = []
        for feat in features:
            if values.get(feat["fips"], "missing_unmatched") != status:
                continue
            patches.extend(m08.patches_for_geometry(feat["geometry"]))
        if not patches:
            continue
        coll = PatchCollection(
            patches,
            facecolor=colors[status],
            edgecolor="#ffffff",
            linewidths=0.05,
            hatch=hatches.get(status, None),
        )
        ax.add_collection(coll)
    ax.set_xlim(-125, -66)
    ax.set_ylim(24, 50)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("County MCOD G40/G41 death-count status, 2019-2024")
    handles = [
        Patch(facecolor=colors["exact"], label="Exact"),
        Patch(facecolor=colors["suppressed_1_9"], label="Suppressed 1-9"),
        Patch(facecolor=colors["zero"], hatch=hatches["zero"], label="Explicit zero"),
        Patch(facecolor=colors["missing_unmatched"], hatch=hatches["missing_unmatched"], label="Missing/unmatched"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=True)
    fig.tight_layout()
    fig.savefig(OUT_FIGURES / "figure1_county_suppression_status_revised.png", dpi=240)
    plt.close(fig)


def copy_supporting_figures() -> None:
    mapping = {
        "map3_suppression_aware_predicted_rates.png": "figure3_suppression_aware_residual_rate.png",
        "national_year_trend.png": "supplement_national_year_trend.png",
        "covid_comention_urbanization_year.png": "supplement_original_covid_urbanization_year.png",
    }
    for src_name, dst_name in mapping.items():
        src = PHASE14 / "figures" / src_name
        if src.exists():
            (OUT_FIGURES / dst_name).write_bytes(src.read_bytes())


def editorial_response_matrix() -> None:
    rows = [
        {"issue": "M1", "action": "Reframed suppression scenarios into visible-only, residual-allocation total-preserving, constant-count stress-test, fixed-value stress-test, and interval-model tiers; added residual mean and constant mean scenario; revised abstract/results/discussion.", "status": "addressed"},
        {"issue": "M2", "action": "Embedded populated Tables 1-5 in the main manuscript DOCX and supplied CSV/XLSX copies.", "status": "addressed"},
        {"issue": "M3", "action": "Replaced Figure 4 with a 2019-2024 temporal/COVID context figure and corrected legend.", "status": "addressed"},
        {"issue": "M4", "action": "Added Introduction and Discussion comparison to Quick 2019, distinguishing Bayesian smoothing from reconciliation/bounding/interval methods.", "status": "addressed"},
        {"issue": "m1/m2", "action": "Removed the orphan county-year exact-death abstract statistic and separated death counts from row counts.", "status": "addressed"},
        {"issue": "m3", "action": "Rebuilt Figure 2 with publication labels and legend stating 95% CIs on a log scale.", "status": "addressed"},
        {"issue": "m4/m5/m10", "action": "Added methods limitations for alpha=1 working variance, interval model non-conditioning on the known marginal total, and unadjusted p-values/multiplicity.", "status": "addressed"},
        {"issue": "m6/m9", "action": "Clarified map viewport/model inclusion and color-scale handling; regenerated Figure 1 with higher zero/missing contrast and hatching.", "status": "addressed"},
        {"issue": "m7", "action": "Audited residual allocation totals after [1,9] clipping; all residual allocation scenarios preserve 58,380 deaths.", "status": "addressed"},
        {"issue": "m8", "action": "Replaced vague VIF statement with maximum 2.92 for median household income/poverty component diagnostics.", "status": "addressed"},
        {"issue": "m11", "action": "Harmonized the corresponding author block to the full affiliation name.", "status": "addressed"},
        {"issue": "m12", "action": "Confirmed repository README and CITATION metadata identify Gregory Pierpoint; data/code statement names repository and DOI.", "status": "addressed"},
        {"issue": "Author question 8", "action": "Added Connecticut geography limitation statement noting no crosswalk correction and possible period comparability limitation.", "status": "addressed"},
    ]
    write_csv(OUT_REPORTS / "editorial_issue_response_matrix.csv", rows, ["issue", "action", "status"])


def main() -> None:
    ensure_dirs()
    audit = build_revised_model_outputs()
    build_main_tables()
    plot_revised_forest()
    plot_temporal_covid()
    plot_revised_status_map()
    copy_supporting_figures()
    editorial_response_matrix()
    summary = {
        "phase": "editorial_revision_ready_package_analysis",
        "total_mcod": TOTAL_MCOD,
        "total_ucd": TOTAL_UCD,
        "suppressed_residual": audit["suppressed_residual"],
        "mean_deaths_per_suppressed_row": audit["mean_deaths_per_suppressed_row"],
        "residual_allocation_totals_preserved": all(
            abs(audit[key] - TOTAL_MCOD) < 1e-6
            for key in ["population_scaled_total", "conservative_total", "pro_rural_total"]
        ),
    }
    (OUT_REPORTS / "editorial_revision_analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"editorial_revision_analysis_outputs={OUT}")


if __name__ == "__main__":
    main()
