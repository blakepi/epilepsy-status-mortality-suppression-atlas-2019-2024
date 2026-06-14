# Covariate Import Report

Generated: 2026-06-14

## Source

Covariate and geography inputs are staged under `data/raw/covariates` and `data/raw/geography`.

## Files Used

| label | source | copied_path | status | sha256 |
| --- | --- | --- | --- | --- |
| acs_county_clean | staged_release_input | data\raw\covariates\acs_county_clean.csv | staged | e8fbc0fdc0a63437fc9e09dd3101fc440b3480dcccdb60524759968f440c2ca0 |
| county_covariates_50dc | staged_release_input | data\raw\covariates\county_covariates_50dc.csv | staged | 5a036f6c387c9105cc24a8fa17572da9469949d2e4cdf00f2dc3d6546325849e |
| final_analysis_dataset_2019_2024 | staged_release_input | data\raw\covariates\final_analysis_dataset_2019_2024.csv | staged | 6f4973ae4fcb769b477758910e936b8878e0e3c49cec36fc0b37bffc458fcd54 |
| nchs_urban_rural_clean | staged_release_input | data\raw\covariates\nchs_urban_rural_clean.csv | staged | bfb13480cef9c5b8fc27cd19dfc535eea2f877f8475fb68200666ddfe7344c07 |
| NCHSurb-rural-codes | staged_release_input | data\raw\covariates\NCHSurb-rural-codes.csv | staged | ff45bc0951ff34eebcd1d952bdcc175560d0c5b398b59ea924eac3e26ea6fadf |
| rucc_2023_clean | staged_release_input | data\raw\covariates\rucc_2023_clean.csv | staged | cd0771b0238fec8202a8c64772c091769db692f643e72fedb55b208eacf5fbd7 |
| SVI_2022_US_county | staged_release_input | data\raw\covariates\SVI_2022_US_county.csv | staged | bc47d244153e359d5c09f621a4bf344a1e593159c16fbd3c28a15461b70a6c0f |
| svi_county_2022_clean | staged_release_input | data\raw\covariates\svi_county_2022_clean.csv | staged | ff18206572074b7ad1020d2bf373b2c3637486cbb5ebcf66471abe6ed1cacecf |
| plotly_geojson_counties_fips | staged_release_input | data\raw\geography\plotly_geojson_counties_fips.json | staged | e540149b7525e71ee6b6cab6dea2a95205f11e0c3e7374d27a7c9c47ea96e8c0 |

## Source Counts

| source | rows | unique_county_fips | note |
| --- | --- | --- | --- |
| acs_county_clean | 3144 | 3144 |  |
| county_covariates_50dc | 3144 | 3144 |  |
| final_analysis_dataset_2019_2024 | 1169 | 1169 |  |
| nchs_urban_rural_clean | 3144 | 3144 |  |
| NCHSurb-rural-codes |  |  | 'utf-8' codec can't decode byte 0xf1 in position 15532: invalid continuation byte |
| rucc_2023_clean | 3144 | 3144 |  |
| SVI_2022_US_county | 3144 |  |  |
| svi_county_2022_clean | 3144 | 3144 |  |

## Notes

- The staged combined county covariate file is used as the main merge source.
- FIPS values are preserved as 5-character strings.
- Local county GeoJSON is staged for map construction.
- Connecticut geography is not silently modified. Any WONDER/covariate mismatch remains documented in merge reports.
