from __future__ import annotations

import pandas as pd

from utils import (
    PROCESSED_DIR,
    RAW_COVARIATE_DIR,
    RAW_GEOGRAPHY_DIR,
    REPORT_DIR,
    ensure_dirs,
    fips5,
    md_table,
    rel,
    sha256_file,
    write_text,
)


def staged_row(label: str, path, status: str = "staged") -> dict:
    return {
        "label": label,
        "source": "staged_release_input",
        "copied_path": rel(path) if path.exists() else "",
        "status": status if path.exists() else "missing",
        "sha256": sha256_file(path) if path.exists() else "",
    }


def main() -> None:
    ensure_dirs()
    copied = []
    source_counts = []

    for src in sorted(RAW_COVARIATE_DIR.glob("*.csv")):
        label = src.stem
        copied.append(staged_row(label, src))
        try:
            df = pd.read_csv(src, dtype={"county_fips": str, "state_fips": str}, low_memory=False)
            if "county_fips" in df.columns:
                df["county_fips"] = fips5(df["county_fips"])
                source_counts.append({"source": label, "rows": len(df), "unique_county_fips": df["county_fips"].nunique()})
            else:
                source_counts.append({"source": label, "rows": len(df), "unique_county_fips": ""})
        except Exception as exc:
            source_counts.append({"source": label, "rows": "", "unique_county_fips": "", "note": str(exc)})

    for src in sorted(RAW_GEOGRAPHY_DIR.glob("*")):
        if src.is_file():
            copied.append(staged_row(src.stem, src))

    copied_df = pd.DataFrame(copied)
    copied_df.to_csv(PROCESSED_DIR / "covariate_input_manifest.csv", index=False)
    pd.DataFrame(source_counts).to_csv(PROCESSED_DIR / "covariate_source_counts.csv", index=False)

    combined = RAW_COVARIATE_DIR / "county_covariates_50dc.csv"
    if combined.exists():
        cov = pd.read_csv(combined, dtype={"county_fips": str, "state_fips": str}, low_memory=False)
        cov["county_fips"] = fips5(cov["county_fips"])
        cov.to_csv(PROCESSED_DIR / "county_covariates.csv", index=False)

    report = f"""# Covariate Import Report

Generated: 2026-06-14

## Source

Covariate and geography inputs are staged under `data/raw/covariates` and `data/raw/geography`.

## Files Used

{md_table(copied_df)}

## Source Counts

{md_table(pd.DataFrame(source_counts))}

## Notes

- The staged combined county covariate file is used as the main merge source.
- FIPS values are preserved as 5-character strings.
- Local county GeoJSON is staged for map construction.
- Connecticut geography is not silently modified. Any WONDER/covariate mismatch remains documented in merge reports.
"""
    write_text(REPORT_DIR / "covariate_import_report.md", report)
    print("Audited staged covariate/geography inputs.")


if __name__ == "__main__":
    main()
