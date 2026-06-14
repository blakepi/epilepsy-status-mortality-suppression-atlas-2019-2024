# Atlas Figure Report

Generated: 2026-06-13

## Maps Produced

- Map 1: `figures\maps\map1_county_suppression_status.png`
- Map 2: `figures\maps\map2_observed_exact_county_rates.png`
- Map 3: `figures\maps\map3_suppression_aware_predicted_rates.png`
- Map 4: `figures\maps\map4_rural_svi_priority.png`
- Map 5: `figures\maps\map5_state_period_rates.png`
- Map 6: `figures\maps\map6_ucd_suppression_status.png`

## Map-Ready Data

- County-period MCOD map data: `tables\map_ready_county_period.csv`
- County-period UCD map data: `tables\map_ready_ucd_county_period.csv`

## Geometry Source

Local Plotly county GeoJSON copied from the prior feasibility project:
`data\raw\geography\plotly_geojson_counties_fips.json`.

## Caveats

- The static PNG viewport emphasizes the contiguous United States for legibility.
- Map-ready CSVs retain all copied county rows.
- Connecticut county/county-equivalent warnings from CDC WONDER are flagged in the map-ready data and not crosswalked away.
- Suppressed counties are explicitly marked or represented by interval-aware/residual-allocation values rather than omitted silently.
