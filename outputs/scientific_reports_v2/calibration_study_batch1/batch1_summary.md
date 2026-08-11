# Scientific Reports v2 multi-replicate calibration, batch 1

Four prespecified truth-known data sets varied the baseline event rate and negative-binomial overdispersion while preserving the same rurality, SVI, age-composition, sex-composition, state, and year effect structure.

## Computational status

- Replicates completed: 4
- Replicates passing the computational gate: 4/4
- Maximum primary R-hat: 1.0319
- Minimum primary bulk ESS: 145.4
- Computational batch status: PASS

## Coefficient recovery

| Parameter | Coverage | Exact 95% interval for coverage | RMSE (IRR) | Median absolute relative bias |
| --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 4/4 (1.000) | 0.398–1.000 | 0.1078 | 7.88% |
| primary_rurality_nonmetro_adjacent | 3/4 (0.750) | 0.194–0.994 | 0.3425 | 23.86% |
| primary_rurality_nonmetro_nonadjacent | 4/4 (1.000) | 0.398–1.000 | 0.3160 | 16.93% |
| svi_quartile_Q2 | 4/4 (1.000) | 0.398–1.000 | 0.1203 | 8.37% |
| svi_quartile_Q3 | 4/4 (1.000) | 0.398–1.000 | 0.0880 | 3.99% |
| svi_quartile_Q4_highest | 3/4 (0.750) | 0.194–0.994 | 0.2766 | 16.10% |

## Suppressed-cell recovery

- Pooled suppressed cells: 857
- Cell-weighted 95% interval coverage: 0.992
- Pooled posterior-mean RMSE: 1.051 deaths

This batch is deliberately reported with exact binomial uncertainty. Four replicates cannot establish nominal 95% coverage; additional prespecified batches are required before the manuscript makes a calibration-performance claim.
