# Temporal and Context Report

Generated: 2026-06-13

## Temporal Outputs

- National trend: `figures\plots\national_year_trend.png`
- Urbanization trend: `figures\plots\urbanization_year_trend.png`
- COVID co-mention trend: `figures\plots\covid_comention_urbanization_year.png`
- Temporal summary table: `tables\temporal_summary.csv`

## Validation

- Q010 COVID co-mention upper bounds are less than or equal to Q005 MCOD deaths by matched urbanization/year: True
- Q002 county-year suppression by rurality saved to `tables\county_year_suppression_by_rurality.csv`.

## Interpretation

Temporal figures are descriptive context for 2019-2024. They do not establish
person-level risk or cause-and-effect pandemic relationships. County-year rows are sparse and
suppression-heavy, so aggregate Q003/Q004/Q005/Q010 trends remain the primary
temporal context.

## Descriptive Clinical/Context Modules

# Descriptive Context Modules

Generated: 2026-06-13

## Outputs

- Workbook: `tables\descriptive_context_tables.xlsx`
- Place of death, age, sex, race, Hispanic origin, COVID co-mention, and UC/MC sensitivity tables are also saved as CSV files under `tables`.

## Caution

These outputs are aggregate ecological summaries. They should not be used to
infer individual-level risk. Suppressed 1-9 cells are represented as intervals
and are not parsed as zero.
