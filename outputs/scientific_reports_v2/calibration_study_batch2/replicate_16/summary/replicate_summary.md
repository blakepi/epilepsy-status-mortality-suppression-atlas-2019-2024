# Calibration study batch 2, replicate 16

Scenario: `baseline_rate_3_4_kappa_4`

## Computational gate

- Chains completed: 4/4
- Draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0344
- Minimum primary bulk ESS: 168.9
- Maximum stochastic latent-summary R-hat: 1.0022
- Computational status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 0.956 | 0.680–1.340 | -14.67% | True | 1.0128 | 272.2 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.249 | 0.818–1.886 | -1.66% | True | 1.0227 | 207.8 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.400 | 0.927–2.136 | 13.84% | True | 1.0344 | 168.9 |
| svi_quartile_Q2 | 1.100 | 1.212 | 0.857–1.642 | 10.15% | True | 1.0084 | 264.9 |
| svi_quartile_Q3 | 1.250 | 1.443 | 1.042–1.938 | 15.43% | True | 1.0130 | 276.7 |
| svi_quartile_Q4_highest | 1.430 | 1.158 | 0.799–1.662 | -19.00% | True | 1.0161 | 214.5 |

Suppressed-cell 95% interval coverage: 0.995.
Suppressed-cell posterior-mean RMSE: 1.058 deaths.

This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.
