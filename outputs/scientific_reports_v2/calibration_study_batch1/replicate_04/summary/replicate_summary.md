# Calibration study batch 1, replicate 4

Scenario: `baseline_rate_3_4_kappa_4`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0298
- Minimum primary bulk ESS: 163.4
- Maximum stochastic latent-summary R-hat: 1.0041
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.171 | 0.849–1.589 | 4.54% | True | 1.0260 | 247.9 |
| primary_rurality_nonmetro_adjacent | 1.270 | 0.965 | 0.623–1.459 | -24.03% | True | 1.0298 | 163.4 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.084 | 0.710–1.648 | -11.83% | True | 1.0196 | 176.2 |
| svi_quartile_Q2 | 1.100 | 1.173 | 0.872–1.557 | 6.65% | True | 1.0201 | 336.5 |
| svi_quartile_Q3 | 1.250 | 1.206 | 0.908–1.622 | -3.49% | True | 1.0213 | 243.3 |
| svi_quartile_Q4_highest | 1.430 | 1.692 | 1.167–2.502 | 18.32% | True | 1.0178 | 177.3 |

Suppressed-cell 95% interval coverage: 0.990.
Suppressed-cell posterior-mean RMSE: 1.176 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
