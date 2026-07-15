from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import BAYES_DATA, CONFIG_PATH, DATA_PROCESSED, OUTPUT_DIR, PROJECT_ROOT, RAW_WONDER, ensure_bayes_dirs, rel


YEARS = ["2019", "2020", "2021", "2022", "2023", "2024"]
GRAND_TOTAL = 58380
RURAL_ORDER = ["metro_large", "metro_other", "nonmetro_adjacent", "nonmetro_nonadjacent"]
SVI_ORDER = ["Q1_lowest", "Q2", "Q3", "Q4_highest"]


@dataclass(frozen=True)
class FramePaths:
    parquet: Path = BAYES_DATA / "model_frame.parquet"
    csv_gz: Path = BAYES_DATA / "model_frame.csv.gz"
    audit_csv: Path = OUTPUT_DIR / "data_audit.csv"
    audit_md: Path = OUTPUT_DIR / "data_audit.md"


def _read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"county_fips": str, "state_fips": str, "year": str}, **kwargs)


def _state_fips_from_county(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5).str[:2]


def _year_string(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64").astype(str)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mode_or_none(values: pd.Series) -> object:
    values = values.dropna()
    if values.empty:
        return None
    return values.mode().iloc[0]


def _impute_covariates(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_missing = out["primary_rurality"].isna() | out["svi_quartile"].isna() | out["acs_pct_age_65_plus"].isna() | out["acs_pct_male"].isna()
    out["unmatched_covariate_flag"] = base_missing
    out["analysis_in_primary_covariate_set"] = ~base_missing

    numeric_cols = [
        "svi_overall",
        "svi_score",
        "pct_age65",
        "pct_male",
        "acs_pct_age_65_plus",
        "acs_pct_male",
        "acs_pct_poverty",
        "acs_pct_uninsured",
    ]
    for col in numeric_cols:
        if col not in out.columns:
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce")
        state_medians = out.groupby("state_fips")[col].transform("median")
        national_median = out[col].median(skipna=True)
        out[col] = out[col].fillna(state_medians).fillna(national_median)

    categorical_cols = [
        "primary_rurality",
        "rurality_rucc_collapsed",
        "rurality_nchs",
        "nchs_urban_rural_6",
        "svi_quartile",
    ]
    for col in categorical_cols:
        if col not in out.columns:
            continue
        state_modes = out.groupby("state_fips")[col].transform(_mode_or_none)
        national_mode = _mode_or_none(out[col])
        out[col] = out[col].fillna(state_modes).fillna(national_mode)

    out["pct_age65"] = out["pct_age65"].fillna(out["acs_pct_age_65_plus"])
    out["pct_male"] = out["pct_male"].fillna(out["acs_pct_male"])
    for source, target in [
        ("primary_rurality", "rurality_rucc_collapsed"),
        ("nchs_urban_rural_6", "rurality_nchs"),
        ("svi_overall", "svi_score"),
    ]:
        if source in out and target in out:
            out[target] = out[target].fillna(out[source])
    return out


def _standardize(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce")
    sd = vals.std(skipna=True)
    if not sd or np.isnan(sd):
        return pd.Series(0.0, index=series.index)
    return (vals - vals.mean(skipna=True)) / sd


def load_config() -> dict:
    import yaml

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_model_frame() -> pd.DataFrame:
    ensure_bayes_dirs()
    q002 = _read_csv(DATA_PROCESSED / "county_year_analysis.csv")
    q001 = _read_csv(DATA_PROCESSED / "county_period_analysis.csv")
    q003 = _read_csv(RAW_WONDER / "Q003_national_year_mc_g40_g41_2019_2024.csv")
    q004 = _read_csv(RAW_WONDER / "Q004_state_year_mc_g40_g41_2019_2024.csv")

    frame = q002.copy()
    frame["county_fips"] = frame["county_fips"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)
    frame["state_fips"] = _state_fips_from_county(frame["county_fips"])
    frame["year"] = _year_string(frame["year"])
    frame["county_name"] = frame.get("county_name").fillna(frame.get("county_name_from_wonder")).fillna(frame.get("county"))
    frame["county_name"] = frame["county_name"].fillna(frame["county_fips"])
    frame["population"] = pd.to_numeric(frame["population"], errors="coerce")
    frame["q002_count_status"] = frame["death_status"].fillna(frame["death_count_status"])
    frame["q002_lower"] = pd.to_numeric(frame["death_lower"], errors="coerce").astype(int)
    frame["q002_upper"] = pd.to_numeric(frame["death_upper"], errors="coerce").astype(int)
    frame["q002_exact_count"] = pd.to_numeric(frame["deaths_exact"], errors="coerce")
    frame.loc[frame["q002_count_status"].eq("zero"), "q002_exact_count"] = 0

    q001_small = q001.copy()
    q001_small["county_fips"] = q001_small["county_fips"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)
    q001_small = q001_small[
        [
            "county_fips",
            "death_status",
            "death_lower",
            "death_upper",
            "deaths_exact",
            "population_or_person_years_wonder_q001",
            "model_exposure_person_years",
        ]
    ].rename(
        columns={
            "death_status": "q001_period_status",
            "death_lower": "q001_period_lower",
            "death_upper": "q001_period_upper",
            "deaths_exact": "q001_period_exact_count",
        }
    )
    q001_small["q001_period_lower"] = pd.to_numeric(q001_small["q001_period_lower"], errors="coerce").astype(int)
    q001_small["q001_period_upper"] = pd.to_numeric(q001_small["q001_period_upper"], errors="coerce").astype(int)
    q001_small.loc[q001_small["q001_period_status"].eq("zero"), "q001_period_exact_count"] = 0
    frame = frame.merge(q001_small, on="county_fips", how="left", validate="many_to_one")
    frame["population_imputed_from_period_person_years"] = frame["population"].isna()
    fallback_annual_population = pd.to_numeric(frame["model_exposure_person_years"], errors="coerce") / len(YEARS)
    frame["population"] = frame["population"].fillna(fallback_annual_population)
    frame["log_population"] = np.log(frame["population"].clip(lower=1))

    q004_state = q004[q004["row_type"].eq("state")].copy()
    q004_state["state_fips"] = pd.to_numeric(q004_state["state_fips"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
    q004_state["year"] = _year_string(q004_state["year"])
    q004_state["q004_state_year_total"] = pd.to_numeric(q004_state["deaths"], errors="coerce").astype(int)
    q004_state["state_name"] = q004_state["state"]
    frame = frame.merge(q004_state[["state_fips", "year", "state_name", "q004_state_year_total"]], on=["state_fips", "year"], how="left")

    q003_year = q003[q003["row_type"].eq("national")].copy()
    q003_year["year"] = _year_string(q003_year["year"])
    q003_year["q003_national_year_total"] = pd.to_numeric(q003_year["deaths"], errors="coerce").astype(int)
    frame = frame.merge(q003_year[["year", "q003_national_year_total"]], on="year", how="left", validate="many_to_one")

    frame["rurality_rucc_collapsed"] = frame.get("primary_rurality")
    frame["rurality_nchs"] = frame.get("nchs_urban_rural_6", frame.get("NCHS"))
    frame["svi_score"] = pd.to_numeric(frame.get("svi_overall"), errors="coerce")
    frame["pct_age65"] = pd.to_numeric(frame.get("acs_pct_age_65_plus"), errors="coerce")
    frame["pct_male"] = pd.to_numeric(frame.get("acs_pct_male"), errors="coerce")
    frame = _impute_covariates(frame)
    frame["z_pct_age65"] = _standardize(frame["pct_age65"])
    frame["z_pct_male"] = _standardize(frame["pct_male"])

    if "rucc_1_3_vs_4_9" not in frame.columns:
        frame["rucc_1_3_vs_4_9"] = frame["primary_rurality"].map(
            {
                "metro_large": "RUCC_1_3",
                "metro_other": "RUCC_1_3",
                "nonmetro_adjacent": "RUCC_4_9",
                "nonmetro_nonadjacent": "RUCC_4_9",
            }
        )

    required = [
        "county_fips",
        "county_name",
        "state_fips",
        "state_name",
        "year",
        "population",
        "log_population",
        "q002_count_status",
        "q002_lower",
        "q002_upper",
        "q002_exact_count",
        "q001_period_status",
        "q001_period_lower",
        "q001_period_upper",
        "q001_period_exact_count",
        "q004_state_year_total",
        "q003_national_year_total",
        "rurality_rucc_collapsed",
        "rurality_nchs",
        "svi_quartile",
        "svi_score",
        "pct_age65",
        "pct_male",
        "z_pct_age65",
        "z_pct_male",
        "unmatched_covariate_flag",
        "analysis_in_primary_covariate_set",
        "population_imputed_from_period_person_years",
        "primary_rurality",
        "rucc_1_3_vs_4_9",
        "acs_pct_poverty",
        "acs_pct_uninsured",
    ]
    extra = [c for c in frame.columns if c not in required]
    frame = frame[required + extra].sort_values(["state_fips", "county_fips", "year"]).reset_index(drop=True)

    if len(frame) != frame["county_fips"].nunique() * len(YEARS):
        raise ValueError("Model frame is not a complete county-year panel.")
    frame.to_parquet(FramePaths.parquet, index=False)
    frame.to_csv(FramePaths.csv_gz, index=False, compression="gzip")
    write_data_audit(frame)
    write_environment_report()
    return frame


def load_model_frame() -> pd.DataFrame:
    if not FramePaths.parquet.exists():
        return build_model_frame()
    return pd.read_parquet(FramePaths.parquet)


def audit_rows(frame: pd.DataFrame) -> list[dict]:
    q001_by_county = frame.drop_duplicates("county_fips")
    state_year = frame.groupby(["state_fips", "year"], dropna=False).agg(
        lower=("q002_lower", "sum"),
        upper=("q002_upper", "sum"),
        target=("q004_state_year_total", "first"),
    )
    national_year = frame.groupby("year", dropna=False).agg(
        lower=("q002_lower", "sum"),
        upper=("q002_upper", "sum"),
        target=("q003_national_year_total", "first"),
    )
    rows = [
        {"metric": "county_year_rows", "value": len(frame), "detail": ""},
        {"metric": "counties", "value": frame["county_fips"].nunique(), "detail": ""},
        {"metric": "state_dc_equivalents", "value": frame["state_fips"].nunique(), "detail": ""},
        {"metric": "exact_county_year_cells", "value": int(frame["q002_count_status"].eq("exact").sum()), "detail": ""},
        {"metric": "suppressed_county_year_cells", "value": int(frame["q002_count_status"].eq("suppressed_1_9").sum()), "detail": ""},
        {"metric": "explicit_zero_county_year_cells", "value": int(frame["q002_count_status"].eq("zero").sum()), "detail": ""},
        {"metric": "missing_unreturned_county_year_cells", "value": int(frame["q002_count_status"].eq("missing_unreturned").sum()), "detail": "No missing/unreturned Q002 cells in current validated extract."},
        {"metric": "county_period_exact_rows", "value": int(q001_by_county["q001_period_status"].eq("exact").sum()), "detail": ""},
        {"metric": "county_period_suppressed_rows", "value": int(q001_by_county["q001_period_status"].eq("suppressed_1_9").sum()), "detail": ""},
        {"metric": "county_period_zero_rows", "value": int(q001_by_county["q001_period_status"].eq("zero").sum()), "detail": ""},
        {"metric": "state_year_total_reconciliation", "value": bool(((state_year["lower"] <= state_year["target"]) & (state_year["upper"] >= state_year["target"])).all()), "detail": f"{len(state_year)} state-year constraints"},
        {"metric": "national_year_total_reconciliation", "value": bool(((national_year["lower"] <= national_year["target"]) & (national_year["upper"] >= national_year["target"])).all()), "detail": f"{len(national_year)} national-year constraints"},
        {"metric": "total_mcod_g40_g41_reconciliation", "value": int(frame.drop_duplicates(['year'])["q003_national_year_total"].sum()), "detail": "Known full-extract total"},
        {"metric": "unmatched_covariate_counties", "value": int(q001_by_county["unmatched_covariate_flag"].sum()), "detail": "Imputed with state medians/modes where available, national medians/modes otherwise."},
        {"metric": "county_year_population_offsets_imputed", "value": int(frame["population_imputed_from_period_person_years"].sum()), "detail": "Rows with missing Q002 county-year population offsets filled from Q001 period person-years/6; driven by Connecticut county-equivalent denominator gaps."},
    ]
    return rows


def write_data_audit(frame: pd.DataFrame) -> None:
    rows = audit_rows(frame)
    audit = pd.DataFrame(rows)
    audit.to_csv(FramePaths.audit_csv, index=False)
    lines = [
        "# Bayesian Constrained Model-Frame Data Audit",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Metric | Value | Detail |",
        "| --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['detail']} |")
    lines.extend(
        [
            "",
            "Suppressed cells are retained as 1-9 intervals and are not treated as zero. The 11 covariate-unmatched WONDER counties remain in the latent count constraint system; covariates are imputed only for model design variables and are flagged. Missing county-year population offsets are imputed from county-period person-years divided by six and flagged.",
            "",
            "Outputs:",
            f"- `{rel(FramePaths.parquet)}`",
            f"- `{rel(FramePaths.csv_gz)}`",
        ]
    )
    FramePaths.audit_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_environment_report() -> None:
    import importlib

    packages = ["pandas", "numpy", "scipy", "pyarrow", "statsmodels", "matplotlib", "openpyxl", "yaml", "pytest", "geopandas", "arviz", "numba"]
    rows = []
    for name in packages:
        try:
            mod = importlib.import_module(name)
            version = getattr(mod, "__version__", "available")
            available = True
        except Exception as exc:
            version = str(exc)
            available = False
        rows.append({"package": name, "available": available, "version_or_error": version})
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / "package_versions.csv", index=False)

    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        commit = "not_available_no_git_repository"
        branch = "not_available_no_git_repository"

    input_paths = [
        DATA_PROCESSED / "county_year_analysis.csv",
        DATA_PROCESSED / "county_period_analysis.csv",
        RAW_WONDER / "Q003_national_year_mc_g40_g41_2019_2024.csv",
        RAW_WONDER / "Q004_state_year_mc_g40_g41_2019_2024.csv",
        PROJECT_ROOT / "config" / "bayes_constrained.yaml",
    ]
    checksums = [{"path": rel(path), "sha256": _sha256(path)} for path in input_paths if path.exists()]
    pd.DataFrame(checksums).to_csv(OUTPUT_DIR / "input_checksums.csv", index=False)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "git_branch": branch,
        "git_commit": commit,
        "config": rel(CONFIG_PATH),
        "input_checksums": checksums,
    }
    (OUTPUT_DIR / "environment_report.txt").write_text(json.dumps(report, indent=2), encoding="utf-8")
