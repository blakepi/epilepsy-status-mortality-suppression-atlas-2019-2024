# Covariate Import Report

Generated: 2026-06-13

## Search Root

`C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility`

## Files Used

| label | source | copied_path | status | sha256 |
| --- | --- | --- | --- | --- |
| county_covariates_50dc | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\processed\county_covariates_50dc.csv | data\raw\covariates\county_covariates_50dc.csv | copied | 5a036f6c387c9105cc24a8fa17572da9469949d2e4cdf00f2dc3d6546325849e |
| acs_county_clean | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\processed\acs_county_clean.csv | data\raw\covariates\acs_county_clean.csv | copied | e8fbc0fdc0a63437fc9e09dd3101fc440b3480dcccdb60524759968f440c2ca0 |
| svi_county_2022_clean | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\processed\svi_county_2022_clean.csv | data\raw\covariates\svi_county_2022_clean.csv | copied | ff18206572074b7ad1020d2bf373b2c3637486cbb5ebcf66471abe6ed1cacecf |
| rucc_2023_clean | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\processed\rucc_2023_clean.csv | data\raw\covariates\rucc_2023_clean.csv | copied | cd0771b0238fec8202a8c64772c091769db692f643e72fedb55b208eacf5fbd7 |
| nchs_urban_rural_clean | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\processed\nchs_urban_rural_clean.csv | data\raw\covariates\nchs_urban_rural_clean.csv | copied | bfb13480cef9c5b8fc27cd19dfc535eea2f877f8475fb68200666ddfe7344c07 |
| prior_final_analysis_dataset | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\processed\final_analysis_dataset_2019_2024.csv | data\raw\covariates\final_analysis_dataset_2019_2024.csv | copied | 6f4973ae4fcb769b477758910e936b8878e0e3c49cec36fc0b37bffc458fcd54 |
| raw_svi_2022 | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\raw\svi\SVI_2022_US_county.csv | data\raw\covariates\SVI_2022_US_county.csv | copied | bc47d244153e359d5c09f621a4bf344a1e593159c16fbd3c28a15461b70a6c0f |
| raw_nchs_2023 | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\raw\nchs\NCHSurb-rural-codes.csv | data\raw\covariates\NCHSurb-rural-codes.csv | copied | ff45bc0951ff34eebcd1d952bdcc175560d0c5b398b59ea924eac3e26ea6fadf |
| plotly_county_geojson | C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\data\raw\crosswalks\plotly_geojson_counties_fips.json | data\raw\geography\plotly_geojson_counties_fips.json | copied | e540149b7525e71ee6b6cab6dea2a95205f11e0c3e7374d27a7c9c47ea96e8c0 |

## Source Counts

| source | rows | unique_county_fips | note |
| --- | --- | --- | --- |
| county_covariates_50dc | 3144 | 3144 |  |
| acs_county_clean | 3144 | 3144 |  |
| svi_county_2022_clean | 3144 | 3144 |  |
| rucc_2023_clean | 3144 | 3144 |  |
| nchs_urban_rural_clean | 3144 | 3144 |  |
| prior_final_analysis_dataset | 1169 | 1169 |  |
| raw_nchs_2023 |  |  | 'utf-8' codec can't decode byte 0xf1 in position 15532: invalid continuation byte |

## Notes

- The prior project's combined county covariate file was used as the main merge source.
- FIPS values are preserved as 5-character strings.
- Local county GeoJSON was available and copied for map construction.
- Connecticut geography is not silently modified. Any WONDER/covariate mismatch remains documented in merge reports.
