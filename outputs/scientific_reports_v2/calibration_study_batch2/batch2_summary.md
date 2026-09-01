# Scientific Reports v2 multi-replicate calibration, batch 2

16 prespecified truth-known data sets varied the baseline event rate and negative-binomial overdispersion while preserving the same rurality, SVI, age-composition, sex-composition, state, and year effect structure.

## Computational status

- Replicates completed: 16
- Replicates passing the computational gate: 16/16
- Maximum primary R-hat: 1.0344
- Minimum primary bulk ESS: 132.6
- Computational batch status: PASS

## Coefficient recovery

| Parameter | Coverage | Exact 95% interval for coverage | RMSE (IRR) | Median absolute relative bias |
| --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 15/16 (0.938) | 0.698–0.998 | 0.1812 | 8.76% |
| primary_rurality_nonmetro_adjacent | 15/16 (0.938) | 0.698–0.998 | 0.2912 | 9.35% |
| primary_rurality_nonmetro_nonadjacent | 16/16 (1.000) | 0.794–1.000 | 0.1608 | 13.46% |
| svi_quartile_Q2 | 14/16 (0.875) | 0.617–0.984 | 0.1729 | 7.80% |
| svi_quartile_Q3 | 16/16 (1.000) | 0.794–1.000 | 0.1511 | 9.52% |
| svi_quartile_Q4_highest | 16/16 (1.000) | 0.794–1.000 | 0.2173 | 11.57% |

## Suppressed-cell recovery

- Pooled suppressed cells: 3480
- Cell-weighted 95% interval coverage: 0.994
- Pooled posterior-mean RMSE: 0.994 deaths

This batch is deliberately reported with exact binomial uncertainty and does not by itself establish precise nominal 95% coverage.
