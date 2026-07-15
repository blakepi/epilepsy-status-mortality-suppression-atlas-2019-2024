# Phase 9 Final Report

Generated: 2026-06-13

## Technical Summary

All validated Q001-Q015 CDC WONDER inputs were copied and checksummed. Q001,
Q003, Q004, and Q005 reconciliation is preserved at 58,380 MCOD G40/G41 deaths
for 2019-2024. The analysis uses suppression-aware county-period intervals,
bias-bounding models, an attempted interval-likelihood model, temporal/COVID
context, UCD sensitivity, and atlas outputs.

## Inputs Used

- Frozen WONDER inputs: `data\raw\wonder`
- Input checksum manifest: `data\processed\wonder_input_checksums.csv`
- County covariates: `data\processed\county_covariates.csv`
- County-period analytic dataset: `data\processed\county_period_analysis.csv`
- County-year analytic dataset: `data\processed\county_year_analysis.csv`

## Extraction Totals and Reconciliation

- Q003 MCOD total: 58,380
- Q001 total row: 58,380
- Q001 exact county death sum: 51,388
- Q001 suppressed county rows: 1,722
- Q001 explicit zero county rows: 335
- Q010 COVID co-mention total row: 1,936, bounded by Q005
- Q012 UCD total: 22,306
- Q014 UCD exact county death sum: 16,650

## County Merge, Denominator, and Suppression

See:

- `reports\county_merge_report.md`
- `reports\suppression_status_report.md`

The denominator decision uses summed Q002 annual county populations as the
preferred person-year exposure for 2019-2024 count models when available.

## Rurality and Social Context

Primary collapsed RUCC categories are `metro_large`, `metro_other`,
`nonmetro_adjacent`, and `nonmetro_nonadjacent`. SVI composite and ACS component
models were kept as separate model families.

## Model Results

Primary nonmetro nonadjacent estimates from the rurality + SVI composite family:

| scenario | irr | ci_low | ci_high | p_value |
| --- | --- | --- | --- | --- |
| observed_exact_positive_only | 0.9743 | 0.7986 | 1.189 | 0.7977 |
| observed_exact_plus_zero | 0.9081 | 0.7766 | 1.062 | 0.2272 |
| suppressed_equals_1 | 0.9845 | 0.8844 | 1.096 | 0.7759 |
| suppressed_equals_5 | 1.291 | 1.178 | 1.415 | 4.784e-08 |
| suppressed_equals_9 | 1.423 | 1.266 | 1.598 | 3.135e-09 |
| population_scaled_residual_allocation | 1.037 | 0.9807 | 1.096 | 0.2033 |
| conservative_anti_rural_allocation | 0.9659 | 0.8988 | 1.038 | 0.3459 |
| pro_rural_allocation | 1.125 | 1.054 | 1.201 | 0.0003932 |

Full model outputs:

- `tables\suppression_bounds_model_results.csv`
- `tables\interval_model_results.csv`
- `reports\model_results_report.md`

## Temporal/COVID and UCD Findings

Temporal and context outputs are in `reports\temporal_context_report.md`.
The UCD sensitivity total from Q012/Q014 is 22,306 deaths and is materially
lower than MCOD, supporting MCOD as a broader epilepsy/status epilepticus-related
mortality construct.

## Maps and Figures

Atlas report: `reports\atlas_figure_report.md`.

Main figures include suppression status, exact-county rates, residual-allocation
rates, rural/high-SVI priority, state-period rates, UCD suppression status,
national trend, urbanization trend, COVID co-mention trend, and the model forest
plot.

## Manuscript Tables

- `tables\table1_county_characteristics.csv`
- `tables\table2_mortality_by_rurality_svi.csv`
- `tables\table3_suppression_aware_models.csv`
- `tables\table4_temporal_context.csv`
- `tables\table5_ucd_sensitivity.csv`
- `tables\manuscript_tables.xlsx`

## Caveats

- CDC WONDER outcome-dependent suppression is central to interpretation.
- Connecticut county/county-equivalent warnings remain documented and unmodified.
- County-level analyses are ecological and do not estimate person-level risk.
- Interval-model standard errors are approximate; bias-bounding models remain the
  primary suppression-aware result if interval estimates are unstable.

## Next Recommended Manuscript Direction

Proceed to Phase 10 audit and story selection before manuscript drafting. The
manuscript should be organized around suppression-aware inference rather than
the old observed-only county model.
