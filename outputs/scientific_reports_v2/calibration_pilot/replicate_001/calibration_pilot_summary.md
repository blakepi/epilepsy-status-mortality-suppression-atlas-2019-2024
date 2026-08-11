# Scientific Reports v2 truth-known calibration pilot

One synthetic data set with known rurality, SVI, age, sex, state, year, and dispersion parameters was suppressed using the 1–9 rule and analyzed with the corrected constrained sampler. This is an end-to-end computational smoke test, not the final calibration study.

## Computational gate

- Chains completed: 4/4
- Draws per chain: 600
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.7663
- Minimum primary bulk ESS: 6.2
- Computational status: HOLD

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.276 | 0.984–1.712 | 13.96% | True | 1.3876 | 9.4 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.512 | 1.136–1.965 | 19.02% | True | 1.6303 | 6.7 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.135 | 0.853–1.644 | -7.70% | True | 1.6057 | 6.9 |
| svi_quartile_Q2 | 1.100 | 1.192 | 0.973–1.654 | 8.37% | True | 1.7663 | 6.2 |
| svi_quartile_Q3 | 1.250 | 1.399 | 1.110–1.649 | 11.91% | True | 1.5928 | 6.9 |
| svi_quartile_Q4_highest | 1.430 | 1.666 | 1.351–2.010 | 16.50% | True | 1.5218 | 7.7 |

## Suppressed-cell recovery

- 95% interval coverage: 0.996
- Posterior-mean RMSE: 1.049 deaths
- Mean 95% interval width: 3.132 deaths

The values above are one-replicate diagnostics. They cannot establish nominal coverage or comparative superiority; those claims require the planned multi-replicate study.
