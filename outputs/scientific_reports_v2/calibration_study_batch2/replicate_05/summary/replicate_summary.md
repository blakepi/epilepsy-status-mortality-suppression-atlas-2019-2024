# Calibration study batch 2, replicate 5

Scenario: `baseline_rate_3_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0106
- Minimum primary bulk ESS: 188.3
- Maximum stochastic latent-summary R-hat: 1.0031
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 0.996 | 0.736–1.319 | -11.07% | True | 1.0039 | 302.7 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.263 | 0.863–1.818 | -0.56% | True | 1.0106 | 188.3 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.145 | 0.801–1.673 | -6.92% | True | 1.0075 | 210.0 |
| svi_quartile_Q2 | 1.100 | 0.999 | 0.751–1.294 | -9.17% | True | 1.0077 | 311.1 |
| svi_quartile_Q3 | 1.250 | 1.149 | 0.887–1.446 | -8.07% | True | 1.0043 | 341.4 |
| svi_quartile_Q4_highest | 1.430 | 1.233 | 0.898–1.628 | -13.78% | True | 1.0095 | 275.7 |

Suppressed-cell 95% interval coverage: 0.987.
Suppressed-cell posterior-mean RMSE: 1.032 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
