# Calibration study batch 2, replicate 9

Scenario: `baseline_rate_3_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0251
- Minimum primary bulk ESS: 163.0
- Maximum stochastic latent-summary R-hat: 1.0026
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.651 | 1.276–2.104 | 47.39% | False | 1.0105 | 271.8 |
| primary_rurality_nonmetro_adjacent | 1.270 | 2.286 | 1.621–3.200 | 79.98% | False | 1.0251 | 171.4 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.348 | 0.911–1.989 | 9.59% | True | 1.0126 | 163.0 |
| svi_quartile_Q2 | 1.100 | 1.074 | 0.840–1.397 | -2.39% | True | 1.0137 | 394.1 |
| svi_quartile_Q3 | 1.250 | 1.041 | 0.825–1.306 | -16.69% | True | 1.0046 | 330.7 |
| svi_quartile_Q4_highest | 1.430 | 1.085 | 0.809–1.471 | -24.14% | True | 1.0107 | 223.8 |

Suppressed-cell 95% interval coverage: 0.992.
Suppressed-cell posterior-mean RMSE: 1.068 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
