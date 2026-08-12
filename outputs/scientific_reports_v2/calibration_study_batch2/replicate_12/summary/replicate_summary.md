# Calibration study batch 2, replicate 12

Scenario: `baseline_rate_3_4_kappa_4`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0240
- Minimum primary bulk ESS: 146.0
- Maximum stochastic latent-summary R-hat: 1.0033
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.043 | 0.747–1.429 | -6.88% | True | 1.0122 | 326.4 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.252 | 0.815–1.918 | -1.41% | True | 1.0181 | 146.0 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.391 | 0.870–2.132 | 13.09% | True | 1.0240 | 153.9 |
| svi_quartile_Q2 | 1.100 | 1.051 | 0.744–1.491 | -4.49% | True | 1.0158 | 240.2 |
| svi_quartile_Q3 | 1.250 | 1.432 | 1.060–1.950 | 14.55% | True | 1.0087 | 296.4 |
| svi_quartile_Q4_highest | 1.430 | 1.628 | 1.110–2.352 | 13.82% | True | 1.0123 | 238.3 |

Suppressed-cell 95% interval coverage: 1.000.
Suppressed-cell posterior-mean RMSE: 0.936 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
