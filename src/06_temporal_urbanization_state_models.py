from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from utils import PLOT_DIR, PROCESSED_DIR, REPORT_DIR, TABLE_DIR, load_wonder, numeric, rel, write_text


def exact_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["death_count_status"].isin(["exact", "zero"]) & df["row_type"].ne("aggregate_total")].copy()


def main() -> None:
    q003 = load_wonder("Q003")
    q004 = load_wonder("Q004")
    q005 = load_wonder("Q005")
    q010 = load_wonder("Q010")
    q013 = load_wonder("Q013")
    county_year = pd.read_csv(PROCESSED_DIR / "county_year_analysis.csv", dtype={"county_fips": str, "year": str})

    nat = exact_rows(q003)
    nat["deaths"] = numeric(nat["deaths"])
    nat["population"] = numeric(nat["population"])
    nat["rate_per_100k"] = nat["deaths"] / nat["population"] * 100000
    nat[["year", "deaths", "population", "rate_per_100k"]].to_csv(TABLE_DIR / "national_year_trend.csv", index=False)

    urb = exact_rows(q005)
    urb["deaths"] = numeric(urb["deaths"])
    urb["population"] = numeric(urb["population"])
    urb["rate_per_100k"] = urb["deaths"] / urb["population"] * 100000

    covid = q010[q010["row_type"].ne("aggregate_total")].copy()
    covid["death_lower"] = pd.to_numeric(covid["deaths"], errors="coerce").where(covid["death_count_status"].eq("exact"), 0)
    covid.loc[covid["death_count_status"].eq("suppressed_1_9"), "death_lower"] = 1
    covid["death_upper"] = pd.to_numeric(covid["deaths"], errors="coerce").where(covid["death_count_status"].eq("exact"), 0)
    covid.loc[covid["death_count_status"].eq("suppressed_1_9"), "death_upper"] = 9

    merged_covid = urb[["urbanization", "year", "deaths"]].rename(columns={"deaths": "mcod_deaths"}).merge(
        covid[["urbanization", "year", "death_lower", "death_upper", "death_count_status"]],
        on=["urbanization", "year"],
        how="left",
    )
    merged_covid["covid_upper_leq_mcod"] = merged_covid["death_upper"] <= merged_covid["mcod_deaths"]

    cy_summary = county_year.groupby(["year", "primary_rurality", "death_status"], dropna=False).agg(
        rows=("county_fips", "count"),
        lower=("death_lower", "sum"),
        upper=("death_upper", "sum"),
        population=("population", "sum"),
    ).reset_index()
    cy_summary.to_csv(TABLE_DIR / "county_year_suppression_by_rurality.csv", index=False)

    temporal = pd.concat(
        [
            nat.assign(source="national_year")[["source", "year", "deaths", "population", "rate_per_100k"]],
            urb.assign(source="urbanization_year")[["source", "year", "urbanization", "deaths", "population", "rate_per_100k"]],
        ],
        ignore_index=True,
        sort=False,
    )
    temporal.to_csv(TABLE_DIR / "temporal_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(nat["year"], nat["deaths"], marker="o", color="#1f4e79")
    ax.set_title("National MCOD G40/G41 deaths by year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Deaths")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "national_year_trend.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, g in urb.groupby("urbanization"):
        ax.plot(g["year"], g["rate_per_100k"], marker="o", label=label)
    ax.set_title("Urbanization-year MCOD G40/G41 rates")
    ax.set_xlabel("Year")
    ax.set_ylabel("Deaths per 100,000 person-years")
    ax.legend(fontsize=7, loc="best")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "urbanization_year_trend.png", dpi=200)
    plt.close(fig)

    covid_plot = covid.groupby(["urbanization", "year"]).agg(lower=("death_lower", "sum"), upper=("death_upper", "sum")).reset_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, g in covid_plot.groupby("urbanization"):
        ax.plot(g["year"], g["upper"], marker="o", label=label)
    ax.set_title("COVID co-mention upper-bound deaths by urbanization")
    ax.set_xlabel("Year")
    ax.set_ylabel("Deaths, exact plus suppressed upper bound")
    ax.legend(fontsize=7, loc="best")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "covid_comention_urbanization_year.png", dpi=200)
    plt.close(fig)

    state_year = exact_rows(q004)
    state_year["deaths"] = numeric(state_year["deaths"])
    state_year["population"] = numeric(state_year["population"])
    state_year["rate_per_100k"] = state_year["deaths"] / state_year["population"] * 100000
    state_year.to_csv(TABLE_DIR / "state_year_rates.csv", index=False)

    report = f"""# Temporal and Context Report

Generated: 2026-06-13

## Temporal Outputs

- National trend: `{rel(PLOT_DIR / "national_year_trend.png")}`
- Urbanization trend: `{rel(PLOT_DIR / "urbanization_year_trend.png")}`
- COVID co-mention trend: `{rel(PLOT_DIR / "covid_comention_urbanization_year.png")}`
- Temporal summary table: `{rel(TABLE_DIR / "temporal_summary.csv")}`

## Validation

- Q010 COVID co-mention upper bounds are less than or equal to Q005 MCOD deaths by matched urbanization/year: {bool(merged_covid["covid_upper_leq_mcod"].fillna(True).all())}
- Q002 county-year suppression by rurality saved to `{rel(TABLE_DIR / "county_year_suppression_by_rurality.csv")}`.

## Interpretation

Temporal figures are descriptive context for 2019-2024. They do not establish
person-level risk or cause-and-effect pandemic relationships. County-year rows are sparse and
suppression-heavy, so aggregate Q003/Q004/Q005/Q010 trends remain the primary
temporal context.
"""
    write_text(REPORT_DIR / "temporal_context_report.md", report)
    print("Completed temporal analyses.")


if __name__ == "__main__":
    main()
