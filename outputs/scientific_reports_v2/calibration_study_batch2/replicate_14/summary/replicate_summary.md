# Calibration study batch 2, replicate 14

Scenario: `lower_rate_2_4_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0274
- Minimum primary bulk ESS: 155.4
- Maximum stochastic latent-summary R-hat: 1.0015
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.209 | 0.876–1.647 | 7.94% | True | 1.0152 | 245.5 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.142 | 0.783–1.688 | -10.05% | True | 1.0274 | 164.5 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.051 | 0.725–1.562 | -14.54% | True | 1.0120 | 155.4 |
| svi_quartile_Q2 | 1.100 | 0.935 | 0.695–1.237 | -15.01% | True | 1.0121 | 336.4 |
| svi_quartile_Q3 | 1.250 | 1.028 | 0.797–1.300 | -17.79% | True | 1.0068 | 401.3 |
| svi_quartile_Q4_highest | 1.430 | 1.257 | 0.903–1.698 | -12.08% | True | 1.0061 | 208.0 |

Suppressed-cell 95% interval coverage: 1.000.
Suppressed-cell posterior-mean RMSE: 0.827 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
