from __future__ import annotations

import pandas as pd

from utils import REPORT_DIR, TABLE_DIR, load_wonder, numeric, rel, write_text


def lower_upper(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    d = numeric(out["deaths"]).fillna(0)
    out["death_lower"] = d
    out["death_upper"] = d
    out.loc[out["death_count_status"].eq("suppressed_1_9"), "death_lower"] = 1
    out.loc[out["death_count_status"].eq("suppressed_1_9"), "death_upper"] = 9
    return out


def table_by(query: str, dims: list[str], label: str) -> pd.DataFrame:
    df = lower_upper(load_wonder(query))
    df = df[df["row_type"].ne("aggregate_total")].copy()
    out = df.groupby(dims + ["death_count_status"], dropna=False).agg(
        rows=("query_id", "size"),
        lower=("death_lower", "sum"),
        upper=("death_upper", "sum"),
    ).reset_index()
    out.insert(0, "table", label)
    return out


def main() -> None:
    tables = {
        "place_by_urbanization": table_by("Q006", ["urbanization", "place_of_death"], "place of death by urbanization"),
        "age_by_urbanization": table_by("Q007", ["urbanization", "age_group"], "age group by urbanization"),
        "sex_by_urbanization": table_by("Q008", ["urbanization", "sex"], "sex by urbanization"),
        "race_by_urbanization": table_by("Q009a", ["urbanization", "race"], "race by urbanization"),
        "hispanic_by_urbanization": table_by("Q009b", ["urbanization", "hispanic_origin"], "Hispanic origin by urbanization"),
        "covid_by_urbanization_year": table_by("Q010", ["urbanization", "year"], "COVID co-mention by urbanization-year"),
    }
    q005 = lower_upper(load_wonder("Q005"))
    q012 = lower_upper(load_wonder("Q012"))
    mc = q005[q005["row_type"].eq("urbanization")].groupby(["urbanization", "year"]).agg(mcod_lower=("death_lower", "sum"), mcod_upper=("death_upper", "sum")).reset_index()
    uc = q012[q012["row_type"].eq("urbanization")].groupby(["urbanization", "year"]).agg(ucd_lower=("death_lower", "sum"), ucd_upper=("death_upper", "sum")).reset_index()
    tables["uc_vs_mc_urbanization_year"] = mc.merge(uc, on=["urbanization", "year"], how="outer")

    q004 = lower_upper(load_wonder("Q004"))
    q011 = lower_upper(load_wonder("Q011"))
    mc_state = q004[q004["row_type"].eq("state")].groupby(["state", "year"]).agg(mcod_lower=("death_lower", "sum"), mcod_upper=("death_upper", "sum")).reset_index()
    uc_state = q011[q011["row_type"].eq("state")].groupby(["state", "year"]).agg(ucd_lower=("death_lower", "sum"), ucd_upper=("death_upper", "sum")).reset_index()
    tables["uc_vs_mc_state_year"] = mc_state.merge(uc_state, on=["state", "year"], how="outer")

    q014 = lower_upper(load_wonder("Q014"))
    ucd_status = q014.groupby("death_count_status", dropna=False).agg(rows=("query_id", "size"), lower=("death_lower", "sum"), upper=("death_upper", "sum")).reset_index()
    tables["ucd_county_suppression_profile"] = ucd_status

    for name, df in tables.items():
        df.to_csv(TABLE_DIR / f"{name}.csv", index=False)

    xlsx = TABLE_DIR / "descriptive_context_tables.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        for name, df in tables.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)

    report = f"""# Descriptive Context Modules

Generated: 2026-06-13

## Outputs

- Workbook: `{rel(xlsx)}`
- Place of death, age, sex, race, Hispanic origin, COVID co-mention, and UC/MC sensitivity tables are also saved as CSV files under `tables`.

## Caution

These outputs are aggregate ecological summaries. They should not be used to
infer individual-level risk. Suppressed 1-9 cells are represented as intervals
and are not parsed as zero.
"""
    with (REPORT_DIR / "temporal_context_report.md").open("a", encoding="utf-8") as f:
        f.write("\n## Descriptive Clinical/Context Modules\n\n")
        f.write(report)
    print("Completed descriptive context modules.")


if __name__ == "__main__":
    main()
