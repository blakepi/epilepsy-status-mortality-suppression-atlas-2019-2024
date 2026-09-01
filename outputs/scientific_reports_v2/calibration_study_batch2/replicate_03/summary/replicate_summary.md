# Calibration study batch 2, replicate 3

Scenario: `higher_rate_5_0_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0311
- Minimum primary bulk ESS: 150.8
- Maximum stochastic latent-summary R-hat: 1.0020
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 0.927 | 0.719–1.192 | -17.27% | True | 1.0143 | 301.4 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.253 | 0.921–1.705 | -1.30% | True | 1.0214 | 174.8 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.350 | 0.965–1.840 | 9.72% | True | 1.0308 | 150.8 |
| svi_quartile_Q2 | 1.100 | 1.179 | 0.933–1.493 | 7.19% | True | 1.0033 | 436.6 |
| svi_quartile_Q3 | 1.250 | 1.233 | 0.991–1.504 | -1.39% | True | 1.0053 | 392.8 |
| svi_quartile_Q4_highest | 1.430 | 1.437 | 1.078–1.935 | 0.52% | True | 1.0311 | 163.3 |

Suppressed-cell 95% interval coverage: 0.996.
Suppressed-cell posterior-mean RMSE: 1.088 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
