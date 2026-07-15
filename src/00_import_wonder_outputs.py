from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import (
    CDC_PROJECT,
    PROCESSED_DIR,
    RAW_WONDER_CSV_DIR,
    RAW_WONDER_PARQUET_DIR,
    REPORT_DIR,
    copy_file,
    ensure_dirs,
    rel,
    sha256_file,
    md_table,
    write_text,
)


def main() -> None:
    ensure_dirs()
    copied: list[dict] = []

    src_csv = CDC_PROJECT / "data" / "processed" / "csv"
    src_parquet = CDC_PROJECT / "data" / "processed" / "parquet"
    src_reports = CDC_PROJECT / "reports"
    handoff_dir = REPORT_DIR / "extraction_handoff"

    for src in sorted(src_csv.glob("Q*.csv")):
        if src.name.endswith("_notes.csv"):
            continue
        dst = copy_file(src, RAW_WONDER_CSV_DIR / src.name)
        copied.append({"source": str(src), "copied_path": rel(dst), "kind": "wonder_csv", "sha256": sha256_file(dst), "bytes": dst.stat().st_size})

    for src in sorted(src_parquet.glob("Q*.parquet")):
        dst = copy_file(src, RAW_WONDER_PARQUET_DIR / src.name)
        copied.append({"source": str(src), "copied_path": rel(dst), "kind": "wonder_parquet", "sha256": sha256_file(dst), "bytes": dst.stat().st_size})

    required_reports = [
        "export_inventory.csv",
        "option_b_data_manifest.md",
        "final_export_batch_report.md",
        "export_validation_report.md",
        "provenance_report.md",
        "manual_query_instructions.md",
        "api_limitations_report.md",
    ]
    for name in required_reports:
        src = src_reports / name
        if src.exists():
            dst = copy_file(src, handoff_dir / name)
            copied.append({"source": str(src), "copied_path": rel(dst), "kind": "extraction_report", "sha256": sha256_file(dst), "bytes": dst.stat().st_size})

    checksums = pd.DataFrame(copied)
    checksums_path = PROCESSED_DIR / "wonder_input_checksums.csv"
    checksums.to_csv(checksums_path, index=False)

    q_csv = checksums[checksums["kind"].eq("wonder_csv")]
    q_parquet = checksums[checksums["kind"].eq("wonder_parquet")]
    reports = checksums[checksums["kind"].eq("extraction_report")]
    report_text = f"""# Input Audit Report

Generated: 2026-06-13

## WONDER Freeze Summary

- Source extraction project: `{CDC_PROJECT}`
- Copied Q-series CSV files: {len(q_csv)}
- Copied Q-series parquet files: {len(q_parquet)}
- Copied extraction reports: {len(reports)}
- Checksum manifest: `{rel(checksums_path)}`

All copied WONDER files are frozen under `data\\raw\\wonder`. The scripts read
these copied files rather than the extraction project.

## Copied Extraction Reports

{md_table(reports[["copied_path", "sha256"]]) if not reports.empty else "No extraction reports copied."}

## Validation Note

The extraction handoff reports state that all Q001-Q015 exports were present,
parsed, and validated before this analysis project was created. Failed/manual
queries were zero. The Connecticut county/county-equivalent geography warning
is retained for Q001/Q002/Q014 and is not corrected here.
"""
    write_text(REPORT_DIR / "input_audit_report.md", report_text)
    print(f"Copied {len(q_csv)} CSV, {len(q_parquet)} parquet, and {len(reports)} report files.")


if __name__ == "__main__":
    main()
