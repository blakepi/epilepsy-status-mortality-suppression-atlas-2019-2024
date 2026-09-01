# Scientific Reports v2 tuned truth-known calibration extension

The original four synthetic calibration chains were resumed for 20,000 additional iterations using proposal scales selected from the initial acceptance profile. Diagnostics use only the final 1,800 retained draws per chain.

## Computational gate

- Chains completed: 4/4
- Total retained draws per chain: 2600
- Diagnostic tail draws per chain: 1800
- Constraint-validation failures: 0
- Maximum primary R-hat: 1.0220
- Minimum primary bulk ESS: 152.6
- Minimum primary tail ESS: 290.8
- Status: PASS

## Primary coefficient recovery

| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| primary_rurality_metro_other | 1.120 | 1.282 | 1.002–1.637 | 14.44% | True | 1.0196 | 239.2 |
| primary_rurality_nonmetro_adjacent | 1.270 | 1.355 | 1.000–1.861 | 6.70% | True | 1.0220 | 152.6 |
| primary_rurality_nonmetro_nonadjacent | 1.230 | 1.227 | 0.880–1.695 | -0.28% | True | 1.0100 | 187.9 |
| svi_quartile_Q2 | 1.100 | 1.183 | 0.926–1.495 | 7.52% | True | 1.0080 | 413.2 |
| svi_quartile_Q3 | 1.250 | 1.330 | 1.076–1.625 | 6.43% | True | 1.0045 | 408.6 |
| svi_quartile_Q4_highest | 1.430 | 1.562 | 1.206–1.988 | 9.25% | True | 1.0080 | 241.1 |

Suppressed-cell 95% interval coverage in this one replicate was 1.000; posterior-mean RMSE was 1.043 deaths.

These are one-replicate diagnostics and do not establish nominal frequentist coverage or comparative superiority.
