# Bayesian Constrained Model-Frame Data Audit

Generated: 2026-06-16 14:37:39

| Metric | Value | Detail |
| --- | ---: | --- |
| county_year_rows | 18852 |  |
| counties | 3142 |  |
| state_dc_equivalents | 51 |  |
| exact_county_year_cells | 1350 |  |
| suppressed_county_year_cells | 9695 |  |
| explicit_zero_county_year_cells | 7807 |  |
| missing_unreturned_county_year_cells | 0 | No missing/unreturned Q002 cells in current validated extract. |
| county_period_exact_rows | 1085 |  |
| county_period_suppressed_rows | 1722 |  |
| county_period_zero_rows | 335 |  |
| state_year_total_reconciliation | True | 306 state-year constraints |
| national_year_total_reconciliation | True | 6 national-year constraints |
| total_mcod_g40_g41_reconciliation | 58380 | Known full-extract total |
| unmatched_covariate_counties | 11 | Imputed with state medians/modes where available, national medians/modes otherwise. |
| county_year_population_offsets_imputed | 24 | Rows with missing Q002 county-year population offsets filled from Q001 period person-years/6; driven by Connecticut county-equivalent denominator gaps. |

Suppressed cells are retained as 1-9 intervals and are not treated as zero. The 11 covariate-unmatched WONDER counties remain in the latent count constraint system; covariates are imputed only for model design variables and are flagged. Missing county-year population offsets are imputed from county-period person-years divided by six and flagged.

Outputs:
- `data\processed\bayes_constrained\model_frame.parquet`
- `data\processed\bayes_constrained\model_frame.csv.gz`
