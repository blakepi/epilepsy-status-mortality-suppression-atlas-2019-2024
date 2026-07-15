# County-Year Dataset Report

Generated: 2026-06-13

## Validation

- County-year rows: 18,852
- Years present: 2019, 2020, 2021, 2022, 2023, 2024
- All FIPS are 5-character strings: True
- Age labels in year field: False
- Suppressed cells parsed as zero: False

## Q002/Q003 Interval Reconciliation

| year | lower | upper | q003_deaths | contains_q003 |
| --- | --- | --- | --- | --- |
| 2019 | 5385 | 1.734e+04 | 7583 | True |
| 2020 | 6701 | 1.948e+04 | 9147 | True |
| 2021 | 7191 | 2.006e+04 | 9733 | True |
| 2022 | 7739 | 2.135e+04 | 10575 | True |
| 2023 | 7836 | 2.109e+04 | 10546 | True |
| 2024 | 8060 | 2.116e+04 | 10796 | True |

## Outputs

- County-year dataset: `data\processed\county_year_analysis.csv`
- Year-rurality suppression summary: `data\processed\q002_suppression_by_year_rurality.csv`
