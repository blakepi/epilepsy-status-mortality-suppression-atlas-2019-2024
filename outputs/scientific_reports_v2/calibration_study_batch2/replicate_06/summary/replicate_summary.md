# Calibration study batch 2, replicate 6

Scenario: `lower_rate_2_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0191
- Minimum primary bulk ESS: 136.1
- Maximum stochastic latent-summary R-hat: 1.0024
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.286 | 0.949–1.730 | 14.79% | True | 1.0031 | 306.1 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.414 | 0.959–2.120 | 11.37% | True | 1.0136 | 160.2 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.021 | 0.678–1.548 | -17.00% | True | 1.0170 | 136.1 |
| svi_quartile_Q2 | 1.100 | 1.061 | 0.775–1.494 | -3.51% | True | 1.0191 | 235.5 |
| svi_quartile_Q3 | 1.250 | 1.233 | 0.915–1.625 | -1.36% | True | 1.0095 | 253.5 |
| svi_quartile_Q4_highest | 1.430 | 1.559 | 1.132–2.166 | 9.02% | True | 1.0148 | 192.2 |

Suppressed-cell 95% interval coverage: 1.000.
Suppressed-cell posterior-mean RMSE: 0.806 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
