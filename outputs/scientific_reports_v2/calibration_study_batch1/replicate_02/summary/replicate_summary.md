# Calibration study batch 1, replicate 2

Scenario: `lower_rate_2_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0296
- Minimum primary bulk ESS: 145.4
- Maximum stochastic latent-summary R-hat: 1.0033
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.281 | 0.944–1.762 | 14.34% | True | 1.0160 | 202.3 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.571 | 1.040–2.318 | 23.68% | True | 1.0296 | 166.0 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.765 | 1.190–2.588 | 43.50% | True | 1.0254 | 148.6 |
| svi_quartile_Q2 | 1.100 | 1.122 | 0.827–1.500 | 1.98% | True | 1.0291 | 215.4 |
| svi_quartile_Q3 | 1.250 | 1.090 | 0.821–1.436 | -12.80% | True | 1.0158 | 199.3 |
| svi_quartile_Q4_highest | 1.430 | 1.010 | 0.691–1.424 | -29.36% | False | 1.0139 | 145.4 |

Suppressed-cell 95% interval coverage: 0.990.
Suppressed-cell posterior-mean RMSE: 0.847 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
