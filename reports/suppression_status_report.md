# Suppression Status Report

Generated: 2026-06-13

## Q001 County-Period Suppression Profile

| death_status | rows | lower | upper | exact_deaths | population_or_person_years |
| --- | --- | --- | --- | --- | --- |
| exact | 1085 | 5.139e+04 | 5.139e+04 | 5.139e+04 | 1.749e+09 |
| suppressed_1_9 | 1722 | 1722 | 1.55e+04 | 0 | 2.268e+08 |
| zero | 335 | 0 | 0 | 0 | 1.097e+07 |

## Reconciliation

- Q001/Q003 MCOD total deaths, 2019-2024: 58,380
- Exact county death sum: 51,388
- Explicit zero county rows: 335
- Suppressed county rows: 1,722
- Residual hidden deaths to allocate across suppressed rows: 6,992

## Denominator Decision

Q001 county population was compared with summed Q002 county-year populations.
Exact Q001/Q002 person-year matches within tolerance: 3,142 of 3,142.
Maximum absolute difference: 0.000.

For count models over 2019-2024, `model_exposure_person_years` uses summed Q002
annual county populations when available. This treats the period denominator as
person-years rather than an average annual population.

## Interval Coding

- exact: lower = deaths, upper = deaths
- suppressed_1_9: lower = 1, upper = 9, midpoint = 5
- zero: lower = 0, upper = 0
- aggregate_total: retained for reconciliation, excluded from county models
- missing_unreturned: not observed in Q001; would remain missing, not zero
