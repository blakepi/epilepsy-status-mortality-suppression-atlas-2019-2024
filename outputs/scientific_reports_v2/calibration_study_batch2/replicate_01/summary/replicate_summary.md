# Calibration study batch 2, replicate 1

Scenario: `baseline_rate_3_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0236
- Minimum primary bulk ESS: 132.6
- Maximum stochastic latent-summary R-hat: 1.0031
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.036 | 0.762–1.389 | -7.48% | True | 1.0142 | 227.6 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.474 | 1.010–2.142 | 16.09% | True | 1.0236 | 162.3 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.268 | 0.872–1.864 | 3.10% | True | 1.0155 | 132.6 |
| svi_quartile_Q2 | 1.100 | 0.814 | 0.615–1.087 | -25.99% | False | 1.0143 | 352.2 |
| svi_quartile_Q3 | 1.250 | 1.010 | 0.763–1.307 | -19.23% | True | 1.0195 | 254.3 |
| svi_quartile_Q4_highest | 1.430 | 1.272 | 0.920–1.754 | -11.06% | True | 1.0180 | 174.5 |

Suppressed-cell 95% interval coverage: 1.000.
Suppressed-cell posterior-mean RMSE: 0.795 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
