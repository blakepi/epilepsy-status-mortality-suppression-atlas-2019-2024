# Calibration study batch 2, replicate 8

Scenario: `baseline_rate_3_4_kappa_4`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0304
- Minimum primary bulk ESS: 173.1
- Maximum stochastic latent-summary R-hat: 1.0037
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.051 | 0.742–1.456 | -6.19% | True | 1.0160 | 300.6 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.028 | 0.683–1.593 | -19.04% | True | 1.0177 | 194.5 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.021 | 0.667–1.563 | -16.98% | True | 1.0304 | 173.1 |
| svi_quartile_Q2 | 1.100 | 1.124 | 0.814–1.482 | 2.14% | True | 1.0020 | 361.4 |
| svi_quartile_Q3 | 1.250 | 1.236 | 0.915–1.664 | -1.09% | True | 1.0134 | 265.7 |
| svi_quartile_Q4_highest | 1.430 | 1.454 | 1.025–2.156 | 1.68% | True | 1.0247 | 198.6 |

Suppressed-cell 95% interval coverage: 1.000.
Suppressed-cell posterior-mean RMSE: 1.062 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
