# Repository Safety Summary

Generated: 2026-07-15

- Public release tree: approximately 90.4 MiB before Git internals.
- Largest file: `data/processed/county_year_analysis.csv` (14,017,297 bytes).
- Files over 95 MiB: 0.
- Sensitive credential-pattern hits: 0.
- Public-facing private local-path hits: 0.
- Included raw latent arrays, ZIP archives, TIFF duplicates, or DOCX duplicates: 0.
- Production derived-manifest checks: 62 of 62 matched SHA-256.
- Public convergence gate: PASS; action `finalize`.
- Automated tests: 28 passed, 1 archive-dependent test skipped.
- Standalone public release build: PASS; final submission QC passed with 77 packaged files.

The skipped test requires the full large production archive. That archive was verified separately with `scripts/60_verify_production_chains.py`: eight chains, 69 parameters, 489,696 validation records, and zero failures.
