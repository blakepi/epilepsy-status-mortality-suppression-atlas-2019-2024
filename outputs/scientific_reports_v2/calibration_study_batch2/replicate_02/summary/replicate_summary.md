# Calibration study batch 2, replicate 2

Scenario: `lower_rate_2_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0180
- Minimum primary bulk ESS: 167.1
- Maximum stochastic latent-summary R-hat: 1.0022
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.351 | 1.002–1.837 | 20.64% | True | 1.0079 | 268.7 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.236 | 0.811–1.820 | -2.67% | True | 1.0092 | 167.1 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.296 | 0.856–1.926 | 5.33% | True | 1.0072 | 197.1 |
| svi_quartile_Q2 | 1.100 | 1.021 | 0.767–1.421 | -7.15% | True | 1.0180 | 293.3 |
| svi_quartile_Q3 | 1.250 | 1.241 | 0.963–1.627 | -0.75% | True | 1.0120 | 316.3 |
| svi_quartile_Q4_highest | 1.430 | 1.357 | 0.962–1.953 | -5.10% | True | 1.0100 | 223.3 |

Suppressed-cell 95% interval coverage: 0.989.
Suppressed-cell posterior-mean RMSE: 0.935 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
