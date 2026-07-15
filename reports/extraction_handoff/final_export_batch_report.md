# Final Export Batch Report

Generated: 2026-06-13

## Final Status

- Queries registered: 16
- Queries successful: 16
- Queries failed: 0
- Queries requiring manual download: 0
- Raw XLS files present: 16
- Processed CSV/parquet outputs present: 16
- UCD Finder-style syntax accepted for Q011/Q012/Q014: yes
- Modeling/mapping started: no
- Manuscript repository modified: no

Confirmed MCD epilepsy/status epilepticus text:

```text
G40 (Epilepsy)
G41 (Status epilepticus)
```

Confirmed UCD epilepsy/status epilepticus text:

```text
G40 (Epilepsy)
G41 (Status epilepticus)
```

Confirmed COVID co-mention MCD AND2 text:

```text
U07.1 (COVID-19)
```

## Export Inventory

| Query | Raw XLS | Processed CSV | Processed parquet | Exact deaths | Suppressed cells | Zero cells |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Q001 | `data\raw\xls\wonder_q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.xls` | `data\processed\csv\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.csv` | `data\processed\parquet\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.parquet` | 51,388 | 1,722 | 335 |
| Q002 | `data\raw\xls\wonder_q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.xls` | `data\processed\csv\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.csv` | `data\processed\parquet\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.parquet` | 33,217 | 9,695 | 7,807 |
| Q003 | `data\raw\xls\wonder_q003_national_year_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q003_national_year_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q003_national_year_mc_g40_g41_2019_2024.parquet` | 58,380 | 0 | 0 |
| Q004 | `data\raw\xls\wonder_q004_state_year_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q004_state_year_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q004_state_year_mc_g40_g41_2019_2024.parquet` | 58,380 | 0 | 0 |
| Q005 | `data\raw\xls\wonder_q005_urbanization_year_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q005_urbanization_year_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q005_urbanization_year_mc_g40_g41_2019_2024.parquet` | 58,380 | 0 | 0 |
| Q006 | `data\raw\xls\wonder_q006_urbanization_place_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q006_urbanization_place_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q006_urbanization_place_mc_g40_g41_2019_2024.parquet` | 58,364 | 6 | 10 |
| Q007 | `data\raw\xls\wonder_q007_urbanization_age_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q007_urbanization_age_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q007_urbanization_age_mc_g40_g41_2019_2024.parquet` | 58,369 | 3 | 6 |
| Q008 | `data\raw\xls\wonder_q008_urbanization_sex_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q008_urbanization_sex_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q008_urbanization_sex_mc_g40_g41_2019_2024.parquet` | 58,380 | 0 | 0 |
| Q009A | `data\raw\xls\wonder_q009a_urbanization_race6_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q009a_urbanization_race6_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q009a_urbanization_race6_mc_g40_g41_2019_2024.parquet` | 58,357 | 5 | 8 |
| Q009B | `data\raw\xls\wonder_q009b_urbanization_hispanic_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.parquet` | 58,370 | 2 | 0 |
| Q010 | `data\raw\xls\wonder_q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.xls` | `data\processed\csv\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.csv` | `data\processed\parquet\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.parquet` | 1,918 | 5 | 7 |
| Q011 | `data\raw\xls\wonder_q011_state_year_uc_g40_g41_2019_2024.xls` | `data\processed\csv\Q011_state_year_uc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q011_state_year_uc_g40_g41_2019_2024.parquet` | 22,124 | 25 | 0 |
| Q012 | `data\raw\xls\wonder_q012_urbanization_year_uc_g40_g41_2019_2024.xls` | `data\processed\csv\Q012_urbanization_year_uc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q012_urbanization_year_uc_g40_g41_2019_2024.parquet` | 22,306 | 0 | 0 |
| Q013 | `data\raw\xls\wonder_q013_national_age_year_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q013_national_age_year_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q013_national_age_year_mc_g40_g41_2019_2024.parquet` | 58,379 | 1 | 5 |
| Q014 | `data\raw\xls\wonder_q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.xls` | `data\processed\csv\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.csv` | `data\processed\parquet\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.parquet` | 16,650 | 1,866 | 772 |
| Q015 | `data\raw\xls\wonder_q015_state_period_mc_g40_g41_2019_2024.xls` | `data\processed\csv\Q015_state_period_mc_g40_g41_2019_2024.csv` | `data\processed\parquet\Q015_state_period_mc_g40_g41_2019_2024.parquet` | 58,380 | 0 | 0 |

## Reconciliation

- Q003 national-year multiple-cause total: 58,380 deaths.
- Q001 WONDER county-period total row: 58,380 deaths; exact county sum is 51,388 with 1,722 suppressed county cells.
- Q004 and Q005 reconcile exactly to Q003 at 58,380 deaths.
- Q006, Q007, Q009A, and Q009B reconcile to Q003/Q005 because 58,380 falls inside their suppressed-cell intervals.
- Q008 and Q015 reconcile exactly to 58,380 non-aggregate deaths.
- Q010 COVID co-mention total row is 1,936 deaths; all Q010 year and urbanization/year counts are bounded by Q005.
- Q011 UCD exact state-year deaths are 22,124 with 25 suppressed cells; its interval contains the Q012/Q014 aggregate total of 22,306.
- Q012 UCD urbanization-year aggregate total is 22,306 deaths.
- Q014 UCD county-period exact deaths are 16,650 with 1,866 suppressed county cells; its interval contains the Q012 aggregate total of 22,306.
- Q013 exact age-year deaths are 58,379 with one suppressed residual, reconciling to Q003.

## Caveats

- Q001, Q002, and Q014 contain Connecticut county/county-equivalent rows; keep CDC WONDER 2022+ geography/rate caveats with county-level interpretation.
- Suppressed values are preserved as `suppressed_1_9`; they were not parsed as zero.
- Zero cells are preserved as `zero`.
- Year columns for year-requested queries contain only 2019-2024 values.

## Readiness

All Q001-Q015 registered exports are valid and ready for downstream Option B temporal/COVID/descriptive extraction analysis. No extension modeling or mapping was started.
