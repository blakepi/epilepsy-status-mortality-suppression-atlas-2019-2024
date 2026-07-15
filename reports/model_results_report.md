# Model Results Report

Generated: 2026-06-13

## Bias-Bounding Models

County-period negative-binomial count models used log person-years as the
offset. When robust GLM negative-binomial fitting was not stable, the script
falls back to a robust Poisson model and records that model type in the fit
summary.

Primary output files:

- `tables\suppression_bounds_model_results.csv`
- `tables\model_fit_summary.csv`
- `tables\component_model_vif.csv`
- `figures\plots\suppression_bounds_forest_plot.png`

## Main Nonmetro Nonadjacent Signal

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

## Component Collinearity Diagnostics

| variable | vif | r_squared | n |
| --- | --- | --- | --- |
| acs_pct_poverty | 2.912 | 0.6566 | 3129 |
| acs_median_household_income | 2.916 | 0.657 | 3129 |
| acs_pct_high_school_grad_or_higher | 2.391 | 0.5818 | 3129 |
| acs_pct_uninsured | 1.547 | 0.3535 | 3129 |
| acs_pct_non_hispanic_black | 1.345 | 0.2566 | 3129 |
| acs_pct_hispanic | 1.631 | 0.3867 | 3129 |
| acs_pct_age_65_plus | 1.367 | 0.2687 | 3129 |

## Interpretation Guardrail

These are ecological county-level count models. They do not estimate person-level
risk or cause-and-effect relationships. SVI composite and ACS component variables are modeled
in separate families to avoid including SVI with its own components in the same
primary model.

## Interval-Likelihood Addendum

| model_family | term | coef | se_approx | irr | ci_low_approx | ci_high_approx | n_rows | interval_log_likelihood | converged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| interval_nb_rurality_only | primary_rurality_nonmetro_nonadjacent | 0.07474 | 0.2838 | 1.078 | 0.6179 | 1.879 | 3131 | -5172 | True |
| interval_nb_rurality_svi | primary_rurality_nonmetro_nonadjacent | 0.06538 | 0.266 | 1.068 | 0.6338 | 1.798 | 3131 | -5169 | True |
