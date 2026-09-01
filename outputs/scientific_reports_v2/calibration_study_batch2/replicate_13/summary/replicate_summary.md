# Calibration study batch 2, replicate 13

Scenario: `baseline_rate_3_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0220
- Minimum primary bulk ESS: 161.2
- Maximum stochastic latent-summary R-hat: 1.0026
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.171 | 0.900–1.513 | 4.57% | True | 1.0164 | 262.0 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.104 | 0.780–1.570 | -13.07% | True | 1.0172 | 179.6 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.108 | 0.792–1.589 | -9.91% | True | 1.0125 | 169.6 |
| svi_quartile_Q2 | 1.100 | 0.997 | 0.762–1.332 | -9.37% | True | 1.0220 | 247.5 |
| svi_quartile_Q3 | 1.250 | 1.093 | 0.868–1.419 | -12.53% | True | 1.0172 | 238.2 |
| svi_quartile_Q4_highest | 1.430 | 1.342 | 1.019–1.885 | -6.14% | True | 1.0158 | 161.2 |

Suppressed-cell 95% interval coverage: 0.991.
Suppressed-cell posterior-mean RMSE: 1.044 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
