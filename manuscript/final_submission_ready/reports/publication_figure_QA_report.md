# Publication Figure QA Report

Overall status: PASS

## Checks

- Expected main figure bundles present as PNG/SVG/PDF/TIFF: yes
- Figure 1 counts: exact=1,085; suppressed=1,722; zero=335; missing overlay=11
- Figure 2 CI range from frozen model table: 0.460-2.526; plotting range: 0.42-2.75; silently clipped: no
- Figure 3 decision: replaced main residual-allocation map with scenario-envelope figure; moved residual-allocation atlas to supplement Figure S3
- Figure 3 residual-allocation envelope: 0.97-1.13
- Supplementary Figure S3 caution label: `Illustrative allocation; not recovered true county rates.`
- Figure 4 urbanization-year deaths total from frozen input: 58,380
- Figure 4 COVID interval total from frozen input: 1,923-1,963; bars are midpoint values: True

## Inputs

- `C:\Research\EpilepsyMortalityOptionB\data\raw\geography\plotly_geojson_counties_fips.json`
- `C:\Research\EpilepsyMortalityOptionB\data\processed\county_period_analysis.csv`
- `C:\Research\EpilepsyMortalityOptionB\tables\map_ready_county_period.csv`
- `C:\Research\EpilepsyMortalityOptionB\manuscript\final_submission_ready\tables\table3_suppression_aware_models_revised_full.csv`
- `C:\Research\EpilepsyMortalityOptionB\tables\table4_temporal_context.csv`
- `C:\Research\EpilepsyMortalityOptionB\tables\covid_by_urbanization_year.csv`
