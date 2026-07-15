# Option B Data Manifest

Status as of 2026-06-13: all registered exports Q001-Q015 are present, parsed,
and validated. This includes Q001, Chunk A (Q003/Q004/Q005), Chunk B
(Q013/Q002), Q010 COVID co-mention smoke testing, Chunk D multiple-cause
descriptive extensions (Q006/Q007/Q008/Q009A/Q009B/Q015), and underlying-cause
sensitivity queries Q011/Q012/Q014. Modeling and mapping have not started.

## Quarantine

The first Q003/Q004/Q005 run was invalid because the browser selector matched
`Year` as a substring inside `Ten-Year Age Groups`. Those invalid files were
quarantined, not deleted:

```text
data\quarantine\invalid_groupby_year_age_collision_20260613_165150
```

## Available Data

Q001: county-period multiple-cause G40/G41, 2019-2024, with zero and suppressed
values requested.

- Raw XLS: `data\raw\xls\wonder_q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.xls`
- Processed CSV: `data\processed\csv\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.csv`
- Processed parquet: `data\processed\parquet\Q001_county_period_mc_g40_g41_2019_2024_zero_suppressed.parquet`
- County rows: 3,142
- Exact county rows: 1,085
- Suppressed 1-9 county rows: 1,722
- Explicit zero county rows: 335
- Missing/unreturned county rows represented: 0
- Exact county death sum: 51,388
- Q001 total row deaths: 58,380
- Suppressed residual deaths: 6,992

Q002: county-year multiple-cause G40/G41, 2019-2024, with zero and suppressed
values requested.

- Raw XLS: `data\raw\xls\wonder_q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.xls`
- Processed CSV: `data\processed\csv\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.csv`
- Processed parquet: `data\processed\parquet\Q002_county_year_mc_g40_g41_2019_2024_zero_suppressed.parquet`
- County-year rows: 18,852
- Exact county-year rows: 1,350
- Suppressed 1-9 county-year rows: 9,695
- Explicit zero county-year rows: 7,807
- Missing/unreturned county-year rows represented: 0
- Exact county-year death sum: 33,217
- Suppressed residual to Q003 total: 25,163
- County FIPS check: all 3,142 county/county-equivalent FIPS values are 5-character strings
- Reconciles to Q003: yes, each year falls within the possible 1-9 suppressed-cell interval

Q003: national-year multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q003_national_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q003_national_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q003_national_year_mc_g40_g41_2019_2024.parquet`
- 2019-2024 total deaths: 58,380
- Reconciles to Q001 total row: yes

Q004: state-year multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q004_state_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q004_state_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q004_state_year_mc_g40_g41_2019_2024.parquet`
- 2019-2024 total deaths: 58,380
- Reconciles to Q003: yes

Q005: urbanization-year multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q005_urbanization_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q005_urbanization_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q005_urbanization_year_mc_g40_g41_2019_2024.parquet`
- 2019-2024 total deaths: 58,380
- Reconciles to Q003: yes

Q010: urbanization-year multiple-cause G40/G41 AND U07.1 COVID co-mention,
2019-2024.

- Raw XLS: `data\raw\xls\wonder_q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q010_urbanization_year_mc_g40_g41_and_u071_2019_2024.parquet`
- Urbanization-year rows: 42
- Exact rows: 30
- Suppressed 1-9 rows: 5
- Explicit zero rows: 7
- Known exact year-cell death sum: 1,918
- WONDER total row deaths: 1,936
- COVID MCD AND2 text submitted: `U07.1 (COVID-19)`
- Reconciles to Q005: yes, every Q010 year and urbanization/year cell is bounded by Q005, including suppressed-cell upper bounds

Q013: national age-year multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q013_national_age_year_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q013_national_age_year_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q013_national_age_year_mc_g40_g41_2019_2024.parquet`
- Age-year rows: 72
- Age groups represented: 12
- Exact deaths: 58,379
- Suppressed 1-9 cells: 1
- Explicit zero cells: 5
- Reconciles to Q003: yes, exact deaths plus one suppressed residual equals 58,380

Q006: urbanization by place of death, multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q006_urbanization_place_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q006_urbanization_place_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q006_urbanization_place_mc_g40_g41_2019_2024.parquet`
- Rows: 63
- Exact rows: 47
- Suppressed 1-9 rows: 6
- Explicit zero rows: 10
- Exact deaths: 58,364
- Reconciles to Q003/Q005: yes, 58,380 falls within the suppressed-cell interval

Q007: urbanization by ten-year age group, multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q007_urbanization_age_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q007_urbanization_age_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q007_urbanization_age_mc_g40_g41_2019_2024.parquet`
- Rows: 84
- Exact rows: 75
- Suppressed 1-9 rows: 3
- Explicit zero rows: 6
- Exact deaths: 58,369
- Reconciles to Q003/Q005: yes, 58,380 falls within the suppressed-cell interval
- Column check: age labels are in `age_group`; `year` is blank because year was not requested as a group

Q008: urbanization by sex, multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q008_urbanization_sex_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q008_urbanization_sex_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q008_urbanization_sex_mc_g40_g41_2019_2024.parquet`
- Rows: 22
- Exact rows: 14
- Aggregate subtotal rows: 8
- Suppressed 1-9 rows: 0
- Explicit zero rows: 0
- Exact non-aggregate deaths: 58,380
- Reconciles to Q003/Q005: yes

Q009A: urbanization by Single Race 6, multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q009a_urbanization_race6_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q009a_urbanization_race6_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q009a_urbanization_race6_mc_g40_g41_2019_2024.parquet`
- Rows: 49
- Exact rows: 36
- Suppressed 1-9 rows: 5
- Explicit zero rows: 8
- Exact deaths: 58,357
- Reconciles to Q003/Q005: yes, 58,380 falls within the suppressed-cell interval

Q009B: urbanization by Hispanic origin, multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q009b_urbanization_hispanic_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q009b_urbanization_hispanic_mc_g40_g41_2019_2024.parquet`
- Rows: 21
- Exact rows: 19
- Suppressed 1-9 rows: 2
- Explicit zero rows: 0
- Exact deaths: 58,370
- Reconciles to Q003/Q005: yes, 58,380 falls within the suppressed-cell interval

Q015: state-period multiple-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q015_state_period_mc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q015_state_period_mc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q015_state_period_mc_g40_g41_2019_2024.parquet`
- Rows: 52
- Exact state rows: 51
- Aggregate total rows: 1
- Suppressed 1-9 rows: 0
- Explicit zero rows: 0
- Exact non-aggregate deaths: 58,380
- Reconciles to Q003/Q004: yes

Q011: state-year underlying-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q011_state_year_uc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q011_state_year_uc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q011_state_year_uc_g40_g41_2019_2024.parquet`
- State-year rows: 306
- Exact rows: 281
- Suppressed 1-9 rows: 25
- Explicit zero rows: 0
- Exact deaths: 22,124
- Suppressed-cell interval: 22,149 to 22,349
- UCD text accepted: `G40 (Epilepsy)` / `G41 (Status epilepticus)`
- Reconciles to Q012/Q014: yes, interval contains the 22,306 UCD aggregate total

Q012: urbanization-year underlying-cause G40/G41, 2019-2024.

- Raw XLS: `data\raw\xls\wonder_q012_urbanization_year_uc_g40_g41_2019_2024.xls`
- Processed CSV: `data\processed\csv\Q012_urbanization_year_uc_g40_g41_2019_2024.csv`
- Processed parquet: `data\processed\parquet\Q012_urbanization_year_uc_g40_g41_2019_2024.parquet`
- Urbanization-year rows: 42
- Aggregate subtotal/total rows: 8
- Exact rows: 42
- Suppressed 1-9 rows: 0
- Explicit zero rows: 0
- Exact non-aggregate deaths: 22,306
- Grand aggregate total row deaths: 22,306
- UCD text accepted: `G40 (Epilepsy)` / `G41 (Status epilepticus)`
- Years represented: 2019, 2020, 2021, 2022, 2023, 2024

Q014: county-period underlying-cause G40/G41, 2019-2024, with zero and
suppressed values requested.

- Raw XLS: `data\raw\xls\wonder_q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.xls`
- Processed CSV: `data\processed\csv\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.csv`
- Processed parquet: `data\processed\parquet\Q014_county_period_uc_g40_g41_2019_2024_zero_suppressed.parquet`
- County rows: 3,142
- County FIPS values: 3,142 unique 5-character county/county-equivalent strings
- Exact county rows: 504
- Suppressed 1-9 county rows: 1,866
- Explicit zero county rows: 772
- Exact county death sum: 16,650
- Grand aggregate total row deaths: 22,306
- Suppressed-cell interval: 18,516 to 33,444
- UCD text accepted: `G40 (Epilepsy)` / `G41 (Status epilepticus)`
- Reconciles to Q012: yes, interval contains 22,306

No suppressed values in available files were parsed as explicit zero rows. Year
columns in Q002/Q003/Q004/Q005/Q010/Q013 contain only 2019-2024 values after
normalization. Chunk D files do not contain year labels unless the query
requested year, and age labels appear only in age-group columns.

## Pending Data

None for registered Q001-Q015 extraction. Extension modeling, temporal
analysis, COVID modeling, and mapping have not started.

## Benchmark Reconciliation Note

- Prior benchmark: approximately 58,556 known-county deaths
- New Q001 total row: 58,380
- New Q001 exact county death sum: 51,388
- Q002 exact county-year death sum: 33,217, with 25,163 deaths represented by suppressed county-year residuals against Q003
- Q010 COVID co-mention total row deaths: 1,936, bounded by Q005 total 58,380
- Possible explanations to investigate later: prior export settings, dataset
  version, code syntax, inclusion/exclusion handling, suppression handling, or
  prior parser assumptions
- For new Option B analyses, use the newly validated Q001-Q015 exports as the current source of truth unless reconciliation proves otherwise
