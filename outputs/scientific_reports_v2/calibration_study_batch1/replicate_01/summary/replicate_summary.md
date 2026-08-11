# Calibration study batch 1, replicate 1

Scenario: `baseline_rate_3_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0319
- Minimum primary bulk ESS: 170.8
- Maximum stochastic latent-summary R-hat: 1.0008
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.168 | 0.886–1.500 | 4.27% | True | 1.0166 | 252.5 |
| primary_rurality_nonmetro_adjacent | 1.270 | 0.800 | 0.539–1.111 | -36.98% | False | 1.0319 | 173.4 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.093 | 0.766–1.525 | -11.12% | True | 1.0096 | 170.8 |
| svi_quartile_Q2 | 1.100 | 0.989 | 0.749–1.316 | -10.09% | True | 1.0147 | 236.6 |
| svi_quartile_Q3 | 1.250 | 1.306 | 1.004–1.697 | 4.49% | True | 1.0083 | 284.5 |
| svi_quartile_Q4_highest | 1.430 | 1.578 | 1.143–2.168 | 10.32% | True | 1.0088 | 208.3 |

Suppressed-cell 95% interval coverage: 0.995.
Suppressed-cell posterior-mean RMSE: 0.926 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
