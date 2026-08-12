# Scientific Reports v2 truth-known calibration program

## Reporting gate

- Replicates completed: 20/20
- Replicates passing computational gates: 20/20
- Descriptive calibration reporting: AUTHORIZED
- Precise nominal-coverage claim: NOT AUTHORIZED

## Coefficient recovery

| Parameter | Coverage | Exact 95% Monte Carlo interval | RMSE (IRR) | Median absolute relative bias |
| --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 19/20 (0.950) | 0.751-0.999 | 0.1691 | 8.76% |
| primary_rurality_nonmetro_adjacent | 18/20 (0.900) | 0.683-0.988 | 0.3021 | 12.22% |
| primary_rurality_nonmetro_nonadjacent | 20/20 (1.000) | 0.832-1.000 | 0.2017 | 13.46% |
| svi_quartile_Q2 | 18/20 (0.900) | 0.683-0.988 | 0.1637 | 7.80% |
| svi_quartile_Q3 | 20/20 (1.000) | 0.832-1.000 | 0.1408 | 7.58% |
| svi_quartile_Q4_highest | 19/20 (0.950) | 0.751-0.999 | 0.2304 | 12.93% |

## Suppressed-cell recovery

- Suppressed cells pooled across replicates: 4337
- Cell-weighted 95% interval coverage: 0.994
- Pooled posterior-mean RMSE: 1.006 deaths

The 20-replicate program authorizes descriptive reporting of bias, RMSE, interval coverage, convergence, and exact binomial Monte Carlo intervals. It does not authorize a claim that coverage has been estimated precisely or proven equal to the nominal 95% level.
