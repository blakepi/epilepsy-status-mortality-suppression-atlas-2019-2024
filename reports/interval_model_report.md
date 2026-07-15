# Interval-Likelihood Model Addendum

Generated: 2026-06-13

## Feasibility

The script attempted a custom maximum-likelihood negative-binomial interval
model:

- exact rows: P(Y = y)
- zero rows: P(Y = 0)
- suppressed rows: P(1 <= Y <= 9)

## Outputs

- Results: `tables\interval_model_results.csv`
- Fit summary: `tables\interval_model_fit_summary.csv`

## Main Interval Estimates

| model_family | term | coef | se_approx | irr | ci_low_approx | ci_high_approx | n_rows | interval_log_likelihood | converged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| interval_nb_rurality_only | primary_rurality_nonmetro_nonadjacent | 0.07474 | 0.2838 | 1.078 | 0.6179 | 1.879 | 3131 | -5172 | True |
| interval_nb_rurality_svi | primary_rurality_nonmetro_nonadjacent | 0.06538 | 0.266 | 1.068 | 0.6338 | 1.798 | 3131 | -5169 | True |

## Caveat

Approximate standard errors use the optimizer inverse-Hessian approximation.
Bias-bounding models remain the primary suppression-aware evidence if interval
standard errors are unstable.
