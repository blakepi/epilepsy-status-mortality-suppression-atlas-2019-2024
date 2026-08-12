# Calibration study batch 2, replicate 11

Scenario: `higher_rate_5_0_kappa_10`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0273
- Minimum primary bulk ESS: 163.9
- Maximum stochastic latent-summary R-hat: 1.0014
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.108 | 0.875–1.397 | -1.08% | True | 1.0119 | 289.2 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.511 | 1.133–1.979 | 19.01% | True | 1.0186 | 178.2 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.002 | 0.746–1.359 | -18.56% | True | 1.0273 | 163.9 |
| svi_quartile_Q2 | 1.100 | 1.004 | 0.813–1.256 | -8.72% | True | 1.0142 | 418.6 |
| svi_quartile_Q3 | 1.250 | 1.161 | 0.944–1.427 | -7.09% | True | 1.0186 | 311.1 |
| svi_quartile_Q4_highest | 1.430 | 1.229 | 0.932–1.617 | -14.05% | True | 1.0192 | 241.9 |

Suppressed-cell 95% interval coverage: 1.000.
Suppressed-cell posterior-mean RMSE: 1.153 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
