# Final Map Figure Report

## Geometry

- Local geometry file: `C:\Research\EpilepsyMortalityOptionB\data\raw\geography\plotly_geojson_counties_fips.json`
- Feature count: 3,221
- Geometry note: the repository stores a local Plotly county GeoJSON with county FIPS-compatible identifiers. It does not retain a separate TIGER/Line or cartographic-boundary vintage identifier for this copied geometry source.

## Figure 1 Counts

- Exact count: 1,085
- Suppressed positive count, 1-9 deaths: 1,722
- Explicit zero: 335
- Unmatched/missing covariates overlay: 11

These match the Table 1 death-status counts for exact, suppressed, and explicit-zero counties; the unmatched/missing covariate count is shown as a hatch overlay rather than a mutually exclusive death-status category.

## Figure 3 Rate Bins

- <2 deaths per 100,000 person-years: 476
- 2-3 deaths per 100,000 person-years: 691
- 3-4 deaths per 100,000 person-years: 1,096
- 4-5 deaths per 100,000 person-years: 429
- >=5 deaths per 100,000 person-years: 450

Figure 3 uses a discrete, calm colorblind-safe palette and pairs the population-scaled residual-allocation rate panel with the underlying data-visibility panel. It is explicitly labeled as illustrative, not a recovered true county-rate map.

## Outputs

### Figure 1 data visibility

- PNG: `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\figures\figure1_county_data_visibility.png`
- SVG: `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\figures\figure1_county_data_visibility.svg`
- PDF: `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\figures\figure1_county_data_visibility.pdf`

### Figure 3 allocation atlas

- PNG: `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\figures\figure3_allocation_uncertainty_atlas.png`
- SVG: `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\figures\figure3_allocation_uncertainty_atlas.svg`
- PDF: `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\figures\figure3_allocation_uncertainty_atlas.pdf`

