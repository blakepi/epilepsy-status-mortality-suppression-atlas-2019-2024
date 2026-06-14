# Input Audit Report

Generated: 2026-06-14

## WONDER Freeze Summary

- Source: staged aggregate CDC WONDER outputs under `data/raw/wonder`.
- Staged Q-series CSV files: 16
- Staged Q-series parquet files: 16
- Staged extraction reports: 7
- Checksum manifest: `data\processed\wonder_input_checksums.csv`

All WONDER files are frozen under `data/raw/wonder`. The scripts read these staged files and do not automate CDC WONDER extraction.

## Staged Extraction Reports

| copied_path | sha256 |
| --- | --- |
| reports\extraction_handoff\api_limitations_report.md | 6285a6e9e5eba0e8a3fa7599b6d0df549f28bddfcdf4a5da550e88ed5b5ce0b8 |
| reports\extraction_handoff\export_inventory.csv | c62fc1216962f80325471357b9e44952a1074325316df1a788387874e2469a17 |
| reports\extraction_handoff\export_validation_report.md | bbd456c5c1d811c8a73dd8e3ee3a1cca92de612ee647a560e55a3811d799f9e6 |
| reports\extraction_handoff\final_export_batch_report.md | 285392492de979559639384a0f434c66e4c54bdf52cccd7dd9e18bcf80c84ab6 |
| reports\extraction_handoff\manual_query_instructions.md | 92fceb9cea8dd10e1348d9287c935ee57db98d4940d009880be99237b60e0fb1 |
| reports\extraction_handoff\option_b_data_manifest.md | 65918399fbdc7821c4fad1b7a7129dd192e0c2be180ad6b43623dedaf2bae9bc |
| reports\extraction_handoff\provenance_report.md | a94e31f9289e98a8bff9dd2a87a2b2ca5ac7f1b0828561c9f8fb63800ea0f596 |

## Validation Note

The extraction handoff reports state that all Q001-Q015 exports were present, parsed, and validated before this release was created. Failed/manual queries were zero. The Connecticut county/county-equivalent geography warning is retained for Q001/Q002/Q014 and is not corrected here.
