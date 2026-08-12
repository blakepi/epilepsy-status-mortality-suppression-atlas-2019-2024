# Calibration study batch 2, replicate 10

Scenario: `lower_rate_2_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0306
- Minimum primary bulk ESS: 187.3
- Maximum stochastic latent-summary R-hat: 1.0036
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.326 | 0.973–1.831 | 18.39% | True | 1.0116 | 302.0 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.561 | 1.024–2.290 | 22.88% | True | 1.0306 | 187.3 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.415 | 0.954–2.042 | 15.05% | True | 1.0222 | 216.5 |
| svi_quartile_Q2 | 1.100 | 1.640 | 1.213–2.258 | 49.12% | False | 1.0172 | 228.8 |
| svi_quartile_Q3 | 1.250 | 1.387 | 1.040–1.873 | 10.97% | True | 1.0158 | 278.1 |
| svi_quartile_Q4_highest | 1.430 | 1.934 | 1.367–2.781 | 35.25% | True | 1.0128 | 232.3 |

Suppressed-cell 95% interval coverage: 0.984.
Suppressed-cell posterior-mean RMSE: 0.738 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
