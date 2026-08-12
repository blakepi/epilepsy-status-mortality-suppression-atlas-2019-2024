# Calibration study batch 2, replicate 7

Scenario: `higher_rate_5_0_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0223
- Minimum primary bulk ESS: 150.4
- Maximum stochastic latent-summary R-hat: 1.0022
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.123 | 0.859–1.465 | 0.23% | True | 1.0126 | 258.4 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.160 | 0.864–1.633 | -8.65% | True | 1.0103 | 196.4 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.240 | 0.878–1.752 | 0.78% | True | 1.0200 | 150.4 |
| svi_quartile_Q2 | 1.100 | 1.180 | 0.910–1.512 | 7.24% | True | 1.0133 | 273.8 |
| svi_quartile_Q3 | 1.250 | 1.186 | 0.926–1.528 | -5.14% | True | 1.0223 | 253.0 |
| svi_quartile_Q4_highest | 1.430 | 1.116 | 0.829–1.510 | -21.94% | True | 1.0162 | 208.6 |

Suppressed-cell 95% interval coverage: 0.988.
Suppressed-cell posterior-mean RMSE: 1.077 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
