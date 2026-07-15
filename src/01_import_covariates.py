from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import (
    OLD_PROJECT,
    PROCESSED_DIR,
    RAW_COVARIATE_DIR,
    RAW_GEOGRAPHY_DIR,
    REPORT_DIR,
    copy_file,
    ensure_dirs,
    fips5,
    rel,
    sha256_file,
    md_table,
    write_text,
)


EXPECTED = {
    "county_covariates_50dc": OLD_PROJECT / "data" / "processed" / "county_covariates_50dc.csv",
    "acs_county_clean": OLD_PROJECT / "data" / "processed" / "acs_county_clean.csv",
    "svi_county_2022_clean": OLD_PROJECT / "data" / "processed" / "svi_county_2022_clean.csv",
    "rucc_2023_clean": OLD_PROJECT / "data" / "processed" / "rucc_2023_clean.csv",
    "nchs_urban_rural_clean": OLD_PROJECT / "data" / "processed" / "nchs_urban_rural_clean.csv",
    "prior_final_analysis_dataset": OLD_PROJECT / "data" / "processed" / "final_analysis_dataset_2019_2024.csv",
    "raw_svi_2022": OLD_PROJECT / "data" / "raw" / "svi" / "SVI_2022_US_county.csv",
    "raw_nchs_2023": OLD_PROJECT / "data" / "raw" / "nchs" / "NCHSurb-rural-codes.csv",
}

GEOGRAPHY = {
    "plotly_county_geojson": OLD_PROJECT / "data" / "raw" / "crosswalks" / "plotly_geojson_counties_fips.json",
}


def main() -> None:
    ensure_dirs()
    copied = []
    source_counts = []

    for label, src in EXPECTED.items():
        if not src.exists():
            copied.append({"label": label, "source": str(src), "copied_path": "", "status": "missing", "sha256": ""})
            continue
        dst = copy_file(src, RAW_COVARIATE_DIR / src.name)
        copied.append({"label": label, "source": str(src), "copied_path": rel(dst), "status": "copied", "sha256": sha256_file(dst)})
        try:
            df = pd.read_csv(dst, dtype={"county_fips": str, "state_fips": str})
            if "county_fips" in df.columns:
                df["county_fips"] = fips5(df["county_fips"])
                source_counts.append({"source": label, "rows": len(df), "unique_county_fips": df["county_fips"].nunique()})
        except Exception as exc:
            source_counts.append({"source": label, "rows": None, "unique_county_fips": None, "note": str(exc)})

    for label, src in GEOGRAPHY.items():
        if src.exists():
            dst = copy_file(src, RAW_GEOGRAPHY_DIR / src.name)
            copied.append({"label": label, "source": str(src), "copied_path": rel(dst), "status": "copied", "sha256": sha256_file(dst)})
        else:
            copied.append({"label": label, "source": str(src), "copied_path": "", "status": "missing", "sha256": ""})

    copied_df = pd.DataFrame(copied)
    copied_df.to_csv(PROCESSED_DIR / "covariate_input_manifest.csv", index=False)
    pd.DataFrame(source_counts).to_csv(PROCESSED_DIR / "covariate_source_counts.csv", index=False)

    combined = RAW_COVARIATE_DIR / "county_covariates_50dc.csv"
    if combined.exists():
        cov = pd.read_csv(combined, dtype={"county_fips": str, "state_fips": str})
        cov["county_fips"] = fips5(cov["county_fips"])
        cov.to_csv(PROCESSED_DIR / "county_covariates.csv", index=False)

    report = f"""# Covariate Import Report

Generated: 2026-06-13

## Search Root

`{OLD_PROJECT}`

## Files Used

{md_table(copied_df)}

## Source Counts

{md_table(pd.DataFrame(source_counts))}

## Notes

- The prior project's combined county covariate file was used as the main merge source.
- FIPS values are preserved as 5-character strings.
- Local county GeoJSON was available and copied for map construction.
- Connecticut geography is not silently modified. Any WONDER/covariate mismatch remains documented in merge reports.
"""
    write_text(REPORT_DIR / "covariate_import_report.md", report)
    print("Imported covariate/geography inputs.")


if __name__ == "__main__":
    main()
