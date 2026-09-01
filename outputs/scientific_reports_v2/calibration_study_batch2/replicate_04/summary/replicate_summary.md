# Calibration study batch 2, replicate 4

Scenario: `baseline_rate_3_4_kappa_4`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0226
- Minimum primary bulk ESS: 147.8
- Maximum stochastic latent-summary R-hat: 1.0016
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.013 | 0.727–1.381 | -9.59% | True | 1.0076 | 209.7 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.292 | 0.846–1.907 | 1.77% | True | 1.0226 | 162.2 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.431 | 0.921–2.196 | 16.33% | True | 1.0085 | 147.8 |
| svi_quartile_Q2 | 1.100 | 1.192 | 0.870–1.635 | 8.36% | True | 1.0163 | 329.1 |
| svi_quartile_Q3 | 1.250 | 1.516 | 1.103–2.062 | 21.30% | True | 1.0160 | 267.0 |
| svi_quartile_Q4_highest | 1.430 | 1.448 | 0.991–2.113 | 1.29% | True | 1.0136 | 199.4 |

Suppressed-cell 95% interval coverage: 0.995.
Suppressed-cell posterior-mean RMSE: 1.049 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
