from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_WONDER_DIR = PROJECT_ROOT / "data" / "raw" / "wonder"
RAW_WONDER_CSV_DIR = RAW_WONDER_DIR / "csv"
RAW_WONDER_PARQUET_DIR = RAW_WONDER_DIR / "parquet"
RAW_COVARIATE_DIR = PROJECT_ROOT / "data" / "raw" / "covariates"
RAW_GEOGRAPHY_DIR = PROJECT_ROOT / "data" / "raw" / "geography"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports"
TABLE_DIR = PROJECT_ROOT / "tables"
FIGURE_DIR = PROJECT_ROOT / "figures"
PLOT_DIR = FIGURE_DIR / "plots"
MAP_DIR = FIGURE_DIR / "maps"
LOG_DIR = PROJECT_ROOT / "logs"


def ensure_dirs() -> None:
    for path in [
        RAW_WONDER_DIR,
        RAW_WONDER_CSV_DIR,
        RAW_WONDER_PARQUET_DIR,
        RAW_COVARIATE_DIR,
        RAW_GEOGRAPHY_DIR,
        INTERIM_DIR,
        PROCESSED_DIR,
        REPORT_DIR / "extraction_handoff",
        TABLE_DIR,
        PLOT_DIR,
        MAP_DIR,
        LOG_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"county_fips": str, "state_fips": str, "year": str})


def save_df(df: pd.DataFrame, csv_path: Path, parquet_path: Path | None = None) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    if parquet_path is not None:
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(parquet_path, index=False)
        except Exception as exc:
            write_text(parquet_path.with_suffix(".parquet.error.txt"), str(exc))


def wonder_csv(query_prefix: str) -> Path:
    query_prefix = query_prefix.lower()
    candidates = sorted(RAW_WONDER_CSV_DIR.glob("*.csv"))
    for path in candidates:
        if path.name.lower().startswith(query_prefix):
            return path
    raise FileNotFoundError(f"No copied WONDER CSV matching {query_prefix}")


def load_wonder(query_prefix: str) -> pd.DataFrame:
    return read_csv(wonder_csv(query_prefix))


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def fips5(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)


def state_fips2(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(2)


def add_death_intervals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    status = out["death_count_status"].fillna("")
    deaths = numeric(out.get("deaths", pd.Series(index=out.index, dtype=float))).fillna(0)
    out["deaths_exact"] = np.where(status.isin(["exact", "zero"]), deaths, np.nan)
    out["death_lower"] = np.select(
        [
            status.eq("exact"),
            status.eq("zero"),
            status.eq("suppressed_1_9"),
            status.eq("aggregate_total"),
        ],
        [deaths, 0, 1, deaths],
        default=np.nan,
    )
    out["death_upper"] = np.select(
        [
            status.eq("exact"),
            status.eq("zero"),
            status.eq("suppressed_1_9"),
            status.eq("aggregate_total"),
        ],
        [deaths, 0, 9, deaths],
        default=np.nan,
    )
    out["death_midpoint"] = np.select(
        [
            status.eq("exact"),
            status.eq("zero"),
            status.eq("suppressed_1_9"),
            status.eq("aggregate_total"),
        ],
        [deaths, 0, 5, deaths],
        default=np.nan,
    )
    out["suppressed_indicator"] = status.eq("suppressed_1_9")
    out["zero_indicator"] = status.eq("zero")
    out["exact_indicator"] = status.eq("exact")
    out["aggregate_total_indicator"] = status.eq("aggregate_total") | out["row_type"].fillna("").eq("aggregate_total")
    return out


def parse_county_state(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "county" in out.columns:
        parts = out["county"].fillna("").str.rsplit(", ", n=1, expand=True)
        if parts.shape[1] == 2:
            out["county_name_from_wonder"] = parts[0]
            out["state_abbrev_from_wonder"] = parts[1]
        else:
            out["county_name_from_wonder"] = out["county"]
            out["state_abbrev_from_wonder"] = pd.NA
    return out


def primary_rurality_from_rucc(value: object) -> str | float:
    try:
        code = int(float(value))
    except Exception:
        return np.nan
    if code == 1:
        return "metro_large"
    if code in (2, 3):
        return "metro_other"
    if code in (4, 6, 8):
        return "nonmetro_adjacent"
    if code in (5, 7, 9):
        return "nonmetro_nonadjacent"
    return np.nan


def binary_rurality_from_rucc(value: object) -> str | float:
    try:
        code = int(float(value))
    except Exception:
        return np.nan
    if code in (1, 2, 3):
        return "metro"
    if code in (4, 5, 6, 7, 8, 9):
        return "nonmetro"
    return np.nan


def load_covariates() -> pd.DataFrame:
    path = PROCESSED_DIR / "county_covariates.csv"
    if not path.exists():
        path = RAW_COVARIATE_DIR / "county_covariates_50dc.csv"
    df = read_csv(path)
    df["county_fips"] = fips5(df["county_fips"])
    if "state_fips" in df.columns:
        df["state_fips"] = state_fips2(df["state_fips"])
    if "rucc_code" in df.columns:
        df["primary_rurality"] = df["rucc_code"].map(primary_rurality_from_rucc)
        df["rurality_binary"] = df["rucc_code"].map(binary_rurality_from_rucc)
        df["rucc_1_3_vs_4_9"] = df["rurality_binary"].map({"metro": "RUCC_1_3", "nonmetro": "RUCC_4_9"})
    return df


def summarize_status(df: pd.DataFrame, label: str = "") -> pd.DataFrame:
    g = df.groupby("death_count_status", dropna=False).agg(
        rows=("death_count_status", "size"),
        exact_deaths=("death_lower", lambda s: float(pd.to_numeric(s, errors="coerce").where(df.loc[s.index, "death_lower"].eq(df.loc[s.index, "death_upper"])).sum(skipna=True))),
        lower=("death_lower", "sum"),
        upper=("death_upper", "sum"),
    )
    g = g.reset_index()
    if label:
        g.insert(0, "source", label)
    return g


def constrained_allocation(
    weights: pd.Series, target: float, lower: float = 1.0, upper: float = 9.0
) -> pd.Series:
    weights = pd.to_numeric(weights, errors="coerce").fillna(0).clip(lower=0)
    n = len(weights)
    if n == 0:
        return pd.Series(dtype=float)
    target = float(target)
    target = min(max(target, n * lower), n * upper)
    allocation = pd.Series(lower, index=weights.index, dtype=float)
    remaining = target - allocation.sum()
    capacity = pd.Series(upper - lower, index=weights.index, dtype=float)
    active = capacity > 1e-9
    while remaining > 1e-8 and active.any():
        w = weights.where(active, 0)
        if w.sum() <= 0:
            w = pd.Series(np.where(active, 1.0, 0.0), index=weights.index)
        add = remaining * w / w.sum()
        add = np.minimum(add, capacity)
        allocation += add
        capacity -= add
        remaining = target - allocation.sum()
        active = capacity > 1e-8
        if add.sum() <= 1e-10:
            break
    if abs(target - allocation.sum()) > 1e-6 and active.any():
        allocation.loc[active] += (target - allocation.sum()) / active.sum()
    return allocation.clip(lower, upper)


def safe_rate(deaths: pd.Series, exposure: pd.Series, multiplier: float = 100000.0) -> pd.Series:
    deaths = pd.to_numeric(deaths, errors="coerce")
    exposure = pd.to_numeric(exposure, errors="coerce")
    return np.where(exposure > 0, deaths / exposure * multiplier, np.nan)


def run_script(script_name: str) -> None:
    cmd = [sys.executable, str(PROJECT_ROOT / "src" / script_name)]
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def md_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return ""
    show = df.head(max_rows).copy()
    cols = [str(c) for c in show.columns]
    rows = []
    for _, row in show.iterrows():
        vals = []
        for col in show.columns:
            val = row[col]
            if pd.isna(val):
                vals.append("")
            elif isinstance(val, float):
                vals.append(f"{val:.4g}")
            else:
                vals.append(str(val))
        rows.append(vals)
    def clean(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")
    header = "| " + " | ".join(clean(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = ["| " + " | ".join(clean(v) for v in r) + " |" for r in rows]
    suffix = ""
    if len(df) > max_rows:
        suffix = f"\n\nShowing first {max_rows} of {len(df)} rows."
    return "\n".join([header, sep, *body]) + suffix


def write_csv_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
