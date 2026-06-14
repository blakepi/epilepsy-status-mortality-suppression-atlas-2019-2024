from __future__ import annotations

import pandas as pd

from utils import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, md_table, rel, safe_rate, write_text


def main() -> None:
    county = pd.read_csv(PROCESSED_DIR / "county_period_analysis.csv", dtype={"county_fips": str})
    cy = pd.read_csv(PROCESSED_DIR / "county_year_analysis.csv", dtype={"county_fips": str, "year": str})
    models = pd.read_csv(TABLE_DIR / "suppression_bounds_model_results.csv")
    interval = pd.read_csv(TABLE_DIR / "interval_model_results.csv") if (TABLE_DIR / "interval_model_results.csv").exists() else pd.DataFrame()
    temporal = pd.read_csv(TABLE_DIR / "temporal_summary.csv")

    table1 = county.groupby("death_status", dropna=False).agg(
        counties=("county_fips", "count"),
        person_years=("model_exposure_person_years", "sum"),
        exact_deaths=("deaths_exact", "sum"),
        lower=("death_lower", "sum"),
        upper=("death_upper", "sum"),
        pct_nonmetro=("rurality_binary", lambda s: (s == "nonmetro").mean() * 100),
        mean_svi=("SVI_overall", "mean"),
        mean_poverty=("acs_pct_poverty", "mean"),
        mean_uninsured=("acs_pct_uninsured", "mean"),
        mean_age65=("acs_pct_age_65_plus", "mean"),
    ).reset_index()
    table1.to_csv(TABLE_DIR / "table1_county_characteristics.csv", index=False)

    groups = county.groupby(["primary_rurality", "svi_quartile"], dropna=False).agg(
        counties=("county_fips", "count"),
        person_years=("model_exposure_person_years", "sum"),
        lower=("death_lower", "sum"),
        midpoint=("death_midpoint", "sum"),
        upper=("death_upper", "sum"),
        exact_deaths=("deaths_exact", "sum"),
        suppressed=("suppressed_indicator", "sum"),
        zero=("zero_indicator", "sum"),
    ).reset_index()
    groups["rate_lower_per_100k"] = safe_rate(groups["lower"], groups["person_years"])
    groups["rate_midpoint_per_100k"] = safe_rate(groups["midpoint"], groups["person_years"])
    groups["rate_upper_per_100k"] = safe_rate(groups["upper"], groups["person_years"])
    table2 = groups
    table2.to_csv(TABLE_DIR / "table2_mortality_by_rurality_svi.csv", index=False)

    table3 = models[
        models["term"].isin(
            [
                "primary_rurality_metro_other",
                "primary_rurality_nonmetro_adjacent",
                "primary_rurality_nonmetro_nonadjacent",
                "svi_quartile_Q4_highest",
            ]
        )
    ].copy()
    if not interval.empty:
        interval_focus = interval[
            interval["term"].isin(
                [
                    "primary_rurality_metro_other",
                    "primary_rurality_nonmetro_adjacent",
                    "primary_rurality_nonmetro_nonadjacent",
                    "svi_quartile_Q4_highest",
                ]
            )
        ].rename(columns={"ci_low_approx": "ci_low", "ci_high_approx": "ci_high"})
        interval_focus["scenario"] = "interval_likelihood"
        table3 = pd.concat([table3, interval_focus.reindex(columns=table3.columns)], ignore_index=True)
    table3.to_csv(TABLE_DIR / "table3_suppression_aware_models.csv", index=False)

    table4 = temporal.copy()
    q002_status = cy.groupby(["year", "death_status"], dropna=False).agg(rows=("county_fips", "count"), lower=("death_lower", "sum"), upper=("death_upper", "sum")).reset_index()
    q002_status["source"] = "county_year_suppression"
    table4 = pd.concat([table4, q002_status], ignore_index=True, sort=False)
    table4.to_csv(TABLE_DIR / "table4_temporal_context.csv", index=False)

    q014 = pd.read_csv(TABLE_DIR / "map_ready_ucd_county_period.csv", dtype={"county_fips": str}) if (TABLE_DIR / "map_ready_ucd_county_period.csv").exists() else pd.DataFrame()
    ucd_profile = q014.groupby("death_count_status", dropna=False).agg(rows=("county_fips", "count")).reset_index() if not q014.empty else pd.DataFrame()
    ucd_urban = pd.read_csv(TABLE_DIR / "uc_vs_mc_urbanization_year.csv") if (TABLE_DIR / "uc_vs_mc_urbanization_year.csv").exists() else pd.DataFrame()
    table5 = pd.concat(
        [
            ucd_profile.assign(section="ucd_county_suppression_profile"),
            ucd_urban.assign(section="uc_vs_mc_urbanization_year"),
        ],
        ignore_index=True,
        sort=False,
    )
    table5.to_csv(TABLE_DIR / "table5_ucd_sensitivity.csv", index=False)

    workbook = TABLE_DIR / "manuscript_tables.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        table1.to_excel(writer, sheet_name="Table1", index=False)
        table2.to_excel(writer, sheet_name="Table2", index=False)
        table3.to_excel(writer, sheet_name="Table3", index=False)
        table4.to_excel(writer, sheet_name="Table4", index=False)
        table5.to_excel(writer, sheet_name="Table5", index=False)

    model_focus = models[
        models["term"].eq("primary_rurality_nonmetro_nonadjacent")
        & models["model_family"].eq("rurality_svi_composite")
    ][["scenario", "irr", "ci_low", "ci_high", "p_value"]]
    phase9 = f"""# Phase 9 Final Report

Generated: 2026-06-13

## Technical Summary

All validated Q001-Q015 CDC WONDER inputs were copied and checksummed. Q001,
Q003, Q004, and Q005 reconciliation is preserved at 58,380 MCOD G40/G41 deaths
for 2019-2024. The analysis uses suppression-aware county-period intervals,
bias-bounding models, an attempted interval-likelihood model, temporal/COVID
context, UCD sensitivity, and atlas outputs.

## Inputs Used

- Frozen WONDER inputs: `data\\raw\\wonder`
- Input checksum manifest: `{rel(PROCESSED_DIR / "wonder_input_checksums.csv")}`
- County covariates: `{rel(PROCESSED_DIR / "county_covariates.csv")}`
- County-period analytic dataset: `{rel(PROCESSED_DIR / "county_period_analysis.csv")}`
- County-year analytic dataset: `{rel(PROCESSED_DIR / "county_year_analysis.csv")}`

## Extraction Totals and Reconciliation

- Q003 MCOD total: 58,380
- Q001 total row: 58,380
- Q001 exact county death sum: 51,388
- Q001 suppressed county rows: 1,722
- Q001 explicit zero county rows: 335
- Q010 COVID co-mention total row: 1,936, bounded by Q005
- Q012 UCD total: 22,306
- Q014 UCD exact county death sum: 16,650

## County Merge, Denominator, and Suppression

See:

- `{rel(REPORT_DIR / "county_merge_report.md")}`
- `{rel(REPORT_DIR / "suppression_status_report.md")}`

The denominator decision uses summed Q002 annual county populations as the
preferred person-year exposure for 2019-2024 count models when available.

## Rurality and Social Context

Primary collapsed RUCC categories are `metro_large`, `metro_other`,
`nonmetro_adjacent`, and `nonmetro_nonadjacent`. SVI composite and ACS component
models were kept as separate model families.

## Model Results

Primary nonmetro nonadjacent estimates from the rurality + SVI composite family:

{md_table(model_focus) if not model_focus.empty else "No nonmetro nonadjacent estimates available."}

Full model outputs:

- `{rel(TABLE_DIR / "suppression_bounds_model_results.csv")}`
- `{rel(TABLE_DIR / "interval_model_results.csv")}`
- `{rel(REPORT_DIR / "model_results_report.md")}`

## Temporal/COVID and UCD Findings

Temporal and context outputs are in `{rel(REPORT_DIR / "temporal_context_report.md")}`.
The UCD sensitivity total from Q012/Q014 is 22,306 deaths and is materially
lower than MCOD, supporting MCOD as a broader epilepsy/status epilepticus-related
mortality construct.

## Maps and Figures

Atlas report: `{rel(REPORT_DIR / "atlas_figure_report.md")}`.

Main figures include suppression status, exact-county rates, residual-allocation
rates, rural/high-SVI priority, state-period rates, UCD suppression status,
national trend, urbanization trend, COVID co-mention trend, and the model forest
plot.

## Manuscript Tables

- `{rel(TABLE_DIR / "table1_county_characteristics.csv")}`
- `{rel(TABLE_DIR / "table2_mortality_by_rurality_svi.csv")}`
- `{rel(TABLE_DIR / "table3_suppression_aware_models.csv")}`
- `{rel(TABLE_DIR / "table4_temporal_context.csv")}`
- `{rel(TABLE_DIR / "table5_ucd_sensitivity.csv")}`
- `{rel(workbook)}`

## Caveats

- CDC WONDER outcome-dependent suppression is central to interpretation.
- Connecticut county/county-equivalent warnings remain documented and unmodified.
- County-level analyses are ecological and do not estimate person-level risk.
- Interval-model standard errors are approximate; bias-bounding models remain the
  primary suppression-aware result if interval estimates are unstable.

## Next Recommended Manuscript Direction

Proceed to Phase 10 audit and story selection before manuscript drafting. The
manuscript should be organized around suppression-aware inference rather than
the old observed-only county model.
"""
    write_text(REPORT_DIR / "phase9_final_report.md", phase9)
    print("Completed manuscript tables and Phase 9 report.")


if __name__ == "__main__":
    main()
