from __future__ import annotations

import numpy as np
import pandas as pd

from utils import (
    PROCESSED_DIR,
    REPORT_DIR,
    add_death_intervals,
    fips5,
    load_covariates,
    load_wonder,
    md_table,
    numeric,
    parse_county_state,
    rel,
    safe_rate,
    save_df,
    write_text,
)


def main() -> None:
    q001 = load_wonder("Q001")
    q002 = load_wonder("Q002")
    q003 = load_wonder("Q003")
    cov = load_covariates()

    q001["county_fips"] = fips5(q001["county_fips"])
    q002["county_fips"] = fips5(q002["county_fips"])

    q001_total = numeric(q001.loc[q001["row_type"].eq("aggregate_total"), "deaths"]).sum()
    if not q001_total:
        q001_total = numeric(q003.loc[q003["row_type"].ne("aggregate_total"), "deaths"]).sum()

    county = q001[q001["row_type"].eq("county")].copy()
    county = parse_county_state(add_death_intervals(county))
    county["population_or_person_years_wonder_q001"] = numeric(county["population"])

    q002_county = q002[q002["row_type"].eq("county")].copy()
    q002_exposure = (
        q002_county.assign(population_num=numeric(q002_county["population"]))
        .groupby("county_fips", dropna=False)["population_num"]
        .sum()
        .rename("person_years_from_q002")
        .reset_index()
    )
    county = county.merge(q002_exposure, on="county_fips", how="left")
    county["q001_minus_q002_person_years"] = county["population_or_person_years_wonder_q001"] - county["person_years_from_q002"]
    county["model_exposure_person_years"] = county["person_years_from_q002"].where(
        county["person_years_from_q002"].notna(), county["population_or_person_years_wonder_q001"]
    )
    county["annualized_rate_per_100k_midpoint"] = safe_rate(county["death_midpoint"], county["model_exposure_person_years"])
    county["annualized_rate_per_100k_exact_or_zero"] = safe_rate(county["deaths_exact"], county["model_exposure_person_years"])

    merged = county.merge(cov, on="county_fips", how="left", suffixes=("", "_cov"))
    merged["death_status"] = merged["death_count_status"]
    merged["invalid_noncounty_indicator"] = False
    merged["rate_reliability_flag"] = np.select(
        [
            merged["death_status"].eq("exact") & (merged["deaths_exact"] >= 20),
            merged["death_status"].eq("exact") & (merged["deaths_exact"] < 20),
            merged["death_status"].eq("zero"),
            merged["death_status"].eq("suppressed_1_9"),
        ],
        ["stable_count_ge20", "unstable_count_lt20", "zero", "suppressed"],
        default="unknown",
    )

    merged["collapsed_RUCC"] = merged.get("primary_rurality")
    merged["NCHS_urban_rural"] = merged.get("nchs_urban_rural_6")
    merged["SVI_overall"] = numeric(merged.get("svi_overall"))
    merged["SVI_quartile"] = merged.get("svi_quartile")
    merged["geometry_key"] = merged["county_fips"]

    merge_rows = len(merged)
    matched = merged["rucc_code"].notna().sum() if "rucc_code" in merged.columns else 0
    unmatched_wonder = merged.loc[merged["rucc_code"].isna(), ["county_fips", "county"]].copy() if "rucc_code" in merged.columns else merged[["county_fips", "county"]]
    cov_only = cov.loc[~cov["county_fips"].isin(merged["county_fips"]), ["county_fips"]].copy()

    save_df(
        merged,
        PROCESSED_DIR / "county_period_analysis.csv",
        PROCESSED_DIR / "county_period_analysis.parquet",
    )
    unmatched_wonder.to_csv(PROCESSED_DIR / "counties_present_in_wonder_missing_covariates.csv", index=False)
    cov_only.to_csv(PROCESSED_DIR / "counties_present_in_covariates_missing_wonder.csv", index=False)

    denom_abs_diff = merged["q001_minus_q002_person_years"].abs()
    denom_exact_match = int((denom_abs_diff.fillna(0) < 1e-6).sum())
    status_counts = merged.groupby("death_status", dropna=False).agg(
        rows=("county_fips", "count"),
        lower=("death_lower", "sum"),
        upper=("death_upper", "sum"),
        exact_deaths=("deaths_exact", "sum"),
        population_or_person_years=("model_exposure_person_years", "sum"),
    ).reset_index()
    residual = q001_total - numeric(merged.loc[merged["death_status"].eq("exact"), "deaths_exact"]).sum()

    merge_report = f"""# County Merge Report

Generated: 2026-06-13

## County Universe

- WONDER Q001 county rows: {merge_rows:,}
- Combined covariate county rows: {len(cov):,}
- Matched by FIPS: {matched:,}
- WONDER counties missing covariates: {len(unmatched_wonder):,}
- Covariate counties missing WONDER Q001 rows: {len(cov_only):,}
- Final analytic county count, county-period scenario: {merge_rows:,}

## Covariate Sources

The combined covariate file `data\\processed\\county_covariates.csv` was copied
from the prior feasibility project and includes SVI 2022, RUCC 2023, NCHS 2023,
and ACS 2019-2023 county variables.

## Rurality Mapping

- `metro_large`: RUCC 1
- `metro_other`: RUCC 2-3
- `nonmetro_adjacent`: RUCC 4, 6, 8
- `nonmetro_nonadjacent`: RUCC 5, 7, 9
- Binary sensitivity: RUCC 1-3 vs RUCC 4-9
- NCHS sensitivity: `nchs_urban_rural_6`

## Connecticut Geography Warning

CDC WONDER emitted Connecticut county/county-equivalent geography/rate warnings
for Q001/Q002/Q014. No Connecticut crosswalk correction was applied in this
phase. Any county-level Connecticut interpretation should retain this caveat.

## Unmatched Files

- WONDER missing covariates: `{rel(PROCESSED_DIR / "counties_present_in_wonder_missing_covariates.csv")}`
- Covariates missing WONDER: `{rel(PROCESSED_DIR / "counties_present_in_covariates_missing_wonder.csv")}`
"""
    write_text(REPORT_DIR / "county_merge_report.md", merge_report)

    suppression_report = f"""# Suppression Status Report

Generated: 2026-06-13

## Q001 County-Period Suppression Profile

{md_table(status_counts)}

## Reconciliation

- Q001/Q003 MCOD total deaths, 2019-2024: {int(q001_total):,}
- Exact county death sum: {int(numeric(merged.loc[merged["death_status"].eq("exact"), "deaths_exact"]).sum()):,}
- Explicit zero county rows: {int(merged["death_status"].eq("zero").sum()):,}
- Suppressed county rows: {int(merged["death_status"].eq("suppressed_1_9").sum()):,}
- Residual hidden deaths to allocate across suppressed rows: {int(residual):,}

## Denominator Decision

Q001 county population was compared with summed Q002 county-year populations.
Exact Q001/Q002 person-year matches within tolerance: {denom_exact_match:,} of {merge_rows:,}.
Maximum absolute difference: {float(denom_abs_diff.max(skipna=True) or 0):,.3f}.

For count models over 2019-2024, `model_exposure_person_years` uses summed Q002
annual county populations when available. This treats the period denominator as
person-years rather than an average annual population.

## Interval Coding

- exact: lower = deaths, upper = deaths
- suppressed_1_9: lower = 1, upper = 9, midpoint = 5
- zero: lower = 0, upper = 0
- aggregate_total: retained for reconciliation, excluded from county models
- missing_unreturned: not observed in Q001; would remain missing, not zero
"""
    write_text(REPORT_DIR / "suppression_status_report.md", suppression_report)
    print(f"Built county-period dataset: {rel(PROCESSED_DIR / 'county_period_analysis.csv')}")


if __name__ == "__main__":
    main()
