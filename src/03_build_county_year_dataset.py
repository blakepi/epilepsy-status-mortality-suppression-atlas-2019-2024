from __future__ import annotations

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
    q002 = load_wonder("Q002")
    q003 = load_wonder("Q003")
    cov = load_covariates()

    q002["county_fips"] = fips5(q002["county_fips"])
    county_year = q002[q002["row_type"].eq("county")].copy()
    county_year = parse_county_state(add_death_intervals(county_year))
    county_year["population"] = numeric(county_year["population"])
    county_year["year"] = county_year["year"].astype(str)
    county_year["annual_rate_per_100k_midpoint"] = safe_rate(county_year["death_midpoint"], county_year["population"])
    county_year["annual_rate_per_100k_exact_or_zero"] = safe_rate(county_year["deaths_exact"], county_year["population"])

    merged = county_year.merge(cov, on="county_fips", how="left", suffixes=("", "_cov"))
    merged["death_status"] = merged["death_count_status"]
    merged["collapsed_RUCC"] = merged.get("primary_rurality")
    merged["NCHS"] = merged.get("nchs_urban_rural_6")
    merged["SVI"] = numeric(merged.get("svi_overall"))

    save_df(
        merged,
        PROCESSED_DIR / "county_year_analysis.csv",
        PROCESSED_DIR / "county_year_analysis.parquet",
    )

    years = sorted(merged["year"].dropna().unique().tolist())
    fips_ok = bool(merged["county_fips"].str.match(r"^\d{5}$").all())
    age_label_in_year = bool(merged["year"].str.contains("year|years|\\+", case=False, regex=True).any())

    q003_year = q003[q003["row_type"].ne("aggregate_total")].copy()
    q003_year["year"] = q003_year["year"].astype(str)
    q003_year["q003_deaths"] = numeric(q003_year["deaths"])
    bounds = merged.groupby("year").agg(lower=("death_lower", "sum"), upper=("death_upper", "sum")).reset_index()
    bounds = bounds.merge(q003_year[["year", "q003_deaths"]], on="year", how="left")
    bounds["contains_q003"] = (bounds["lower"] <= bounds["q003_deaths"]) & (bounds["upper"] >= bounds["q003_deaths"])
    bounds.to_csv(PROCESSED_DIR / "q002_year_interval_reconciliation.csv", index=False)

    rurality_status = merged.groupby(["year", "primary_rurality", "death_status"], dropna=False).agg(
        rows=("county_fips", "count"),
        lower=("death_lower", "sum"),
        upper=("death_upper", "sum"),
        population=("population", "sum"),
    ).reset_index()
    rurality_status.to_csv(PROCESSED_DIR / "q002_suppression_by_year_rurality.csv", index=False)

    report = f"""# County-Year Dataset Report

Generated: 2026-06-13

## Validation

- County-year rows: {len(merged):,}
- Years present: {", ".join(years)}
- All FIPS are 5-character strings: {fips_ok}
- Age labels in year field: {age_label_in_year}
- Suppressed cells parsed as zero: False

## Q002/Q003 Interval Reconciliation

{md_table(bounds)}

## Outputs

- County-year dataset: `{rel(PROCESSED_DIR / "county_year_analysis.csv")}`
- Year-rurality suppression summary: `{rel(PROCESSED_DIR / "q002_suppression_by_year_rurality.csv")}`
"""
    write_text(REPORT_DIR / "county_year_dataset_report.md", report)
    print(f"Built county-year dataset: {rel(PROCESSED_DIR / 'county_year_analysis.csv')}")


if __name__ == "__main__":
    main()
