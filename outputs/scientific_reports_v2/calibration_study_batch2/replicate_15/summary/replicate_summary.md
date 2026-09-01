# Calibration study batch 2, replicate 15

Scenario: `higher_rate_5_0_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0152
- Minimum primary bulk ESS: 263.4
- Maximum stochastic latent-summary R-hat: 1.0015
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.097 | 0.867–1.376 | -2.02% | True | 1.0079 | 432.1 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.222 | 0.916–1.599 | -3.80% | True | 1.0040 | 312.2 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.468 | 1.077–1.933 | 19.37% | True | 1.0098 | 263.4 |
| svi_quartile_Q2 | 1.100 | 1.051 | 0.827–1.327 | -4.43% | True | 1.0152 | 319.5 |
| svi_quartile_Q3 | 1.250 | 1.335 | 1.077–1.680 | 6.80% | True | 1.0141 | 312.9 |
| svi_quartile_Q4_highest | 1.430 | 1.353 | 1.044–1.767 | -5.39% | True | 1.0112 | 302.1 |

Suppressed-cell 95% interval coverage: 0.992.
Suppressed-cell posterior-mean RMSE: 0.976 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
