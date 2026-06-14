from __future__ import annotations

import pandas as pd

from utils import (
    PROCESSED_DIR,
    RAW_WONDER_CSV_DIR,
    RAW_WONDER_PARQUET_DIR,
    REPORT_DIR,
    ensure_dirs,
    md_table,
    rel,
    sha256_file,
    write_text,
)


def staged_file_row(path, kind: str) -> dict:
    return {
        "source": "staged_release_input",
        "copied_path": rel(path),
        "kind": kind,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def main() -> None:
    ensure_dirs()
    copied: list[dict] = []

    for src in sorted(RAW_WONDER_CSV_DIR.glob("Q*.csv")):
        if src.name.endswith("_notes.csv"):
            continue
        copied.append(staged_file_row(src, "wonder_csv"))

    for src in sorted(RAW_WONDER_PARQUET_DIR.glob("Q*.parquet")):
        copied.append(staged_file_row(src, "wonder_parquet"))

    handoff_dir = REPORT_DIR / "extraction_handoff"
    for src in sorted(handoff_dir.glob("*")):
        if src.is_file():
            copied.append(staged_file_row(src, "extraction_report"))

    checksums = pd.DataFrame(copied)
    checksums_path = PROCESSED_DIR / "wonder_input_checksums.csv"
    checksums.to_csv(checksums_path, index=False)

    q_csv = checksums[checksums["kind"].eq("wonder_csv")]
    q_parquet = checksums[checksums["kind"].eq("wonder_parquet")]
    reports = checksums[checksums["kind"].eq("extraction_report")]
    report_text = f"""# Input Audit Report

Generated: 2026-06-14

## WONDER Freeze Summary

- Source: staged aggregate CDC WONDER outputs under `data/raw/wonder`.
- Staged Q-series CSV files: {len(q_csv)}
- Staged Q-series parquet files: {len(q_parquet)}
- Staged extraction reports: {len(reports)}
- Checksum manifest: `{rel(checksums_path)}`

All WONDER files are frozen under `data/raw/wonder`. The scripts read these staged files and do not automate CDC WONDER extraction.

## Staged Extraction Reports

{md_table(reports[["copied_path", "sha256"]]) if not reports.empty else "No extraction reports staged."}

## Validation Note

The extraction handoff reports state that all Q001-Q015 exports were present, parsed, and validated before this release was created. Failed/manual queries were zero. The Connecticut county/county-equivalent geography warning is retained for Q001/Q002/Q014 and is not corrected here.
"""
    write_text(REPORT_DIR / "input_audit_report.md", report_text)
    print(f"Audited {len(q_csv)} CSV, {len(q_parquet)} parquet, and {len(reports)} report files.")


if __name__ == "__main__":
    main()
