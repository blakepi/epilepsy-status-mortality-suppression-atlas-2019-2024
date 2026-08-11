# Calibration study batch 1, replicate 3

Scenario: `higher_rate_5_0_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0131
- Minimum primary bulk ESS: 192.1
- Maximum stochastic latent-summary R-hat: 1.0021
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 0.994 | 0.777–1.276 | -11.23% | True | 1.0103 | 337.3 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.015 | 0.748–1.382 | -20.08% | True | 1.0131 | 196.1 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 0.959 | 0.701–1.306 | -22.02% | True | 1.0108 | 192.1 |
| svi_quartile_Q2 | 1.100 | 0.901 | 0.686–1.150 | -18.12% | True | 1.0034 | 294.0 |
| svi_quartile_Q3 | 1.250 | 1.268 | 1.005–1.577 | 1.46% | True | 1.0127 | 256.5 |
| svi_quartile_Q4_highest | 1.430 | 1.629 | 1.243–2.138 | 13.89% | True | 1.0109 | 226.3 |

Suppressed-cell 95% interval coverage: 0.992.
Suppressed-cell posterior-mean RMSE: 1.188 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
