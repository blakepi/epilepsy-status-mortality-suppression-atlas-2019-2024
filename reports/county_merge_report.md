# County Merge Report

Generated: 2026-06-13

## County Universe

- WONDER Q001 county rows: 3,142
- Combined covariate county rows: 3,144
- Matched by FIPS: 3,131
- WONDER counties missing covariates: 11
- Covariate counties missing WONDER Q001 rows: 13
- Final analytic county count, county-period scenario: 3,142

## Covariate Sources

The combined covariate file `data\processed\county_covariates.csv` was copied
from the prior feasibility project and includes SVI 2022, RUCC 2023, NCHS 2023,
and ACS 2019-2023 county variables.

## Rurality Mapping

- `metro_large`: RUCC 1
- `metro_other`: RUCC 2-3
- `nonmetro_adjacent`: RUCC 4, 6, 8
- `nonmetro_nonadjacent`: RUCC 5, 7, 9
- Binary sensitivity: RUCC 1-3 vs RUCC 4-9
- NCHS sensitivity: `nchs_urban_rural_6`

## Connecticut Geography Warning

CDC WONDER emitted Connecticut county/county-equivalent geography/rate warnings
for Q001/Q002/Q014. No Connecticut crosswalk correction was applied in this
phase. Any county-level Connecticut interpretation should retain this caveat.

## Unmatched Files

- WONDER missing covariates: `data\processed\counties_present_in_wonder_missing_covariates.csv`
- Covariates missing WONDER: `data\processed\counties_present_in_covariates_missing_wonder.csv`
