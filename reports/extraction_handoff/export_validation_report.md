# Export Validation Report

Generated: 2026-06-13

## Inventory Summary

- Queries registered: 16
- Raw files present: 16
- Parsed successfully: 16
- Processed CSV/parquet outputs present: 16

## Query Warnings

- `Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed`: Connecticut county/county-equivalent rows present; verify 2022+ geography/rate caveats.
- `Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed`: Connecticut county/county-equivalent rows present; verify 2022+ geography/rate caveats.
- `Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed`: Connecticut county/county-equivalent rows present; verify 2022+ geography/rate caveats.

## Cross-Query Reconciliation

- Q003, Q004, and Q005 reconcile exactly: 58,380 multiple-cause G40/G41 deaths in 2019-2024.
- Q001 total row reconciles exactly to Q003: 58,380 deaths.
- Q002 county-year exact-plus-suppressed intervals contain Q003 totals for every year.
- Q006, Q007, Q009A, and Q009B exact-plus-suppressed intervals contain the Q003/Q005 total.
- Q008 and Q015 reconcile exactly to 58,380 non-aggregate deaths.
- Q010 COVID co-mention is bounded by Q005 by year and urbanization; Q010 total row is 1,936 deaths, below Q005 total 58,380.
- Q011 state-year UCD exact-plus-suppressed interval contains Q012/Q014 aggregate total 22,306.
- Q012 and Q014 UCD aggregate total rows agree at 22,306 deaths.
- Q013 exact deaths plus one suppressed residual reconcile to Q003.

## Field and Label Checks

- MCD G40/G41 Finder-style text was accepted for Q001-Q010/Q013/Q015 MCD queries.
- UCD G40/G41 Finder-style text was accepted for Q011/Q012/Q014 UCD queries.
- Q010 MCD AND1 used G40/G41 and MCD AND2 used `U07.1 (COVID-19)`.
- UCD remained blank/default for MCD queries.
- MCD remained blank/default for UCD sensitivity queries.
- Year fields contain only 2019, 2020, 2021, 2022, 2023, and 2024 where year was requested.
- No age-group labels appear in year columns.
- Q007 age labels are confined to `age_group`.
- Suppressed cells remain `suppressed_1_9`; explicit zeros remain `zero`.

## Validation Conclusion

All Q001-Q015 registered exports are valid for downstream Option B temporal/COVID/descriptive extraction analysis. No manual downloads are currently required.
