# Scientific Reports v2 extended corrected joint pilot

Four corrected chains were resumed from the short joint pilot and extended to 10,000 total iterations. Diagnostics use only the final 650 retained draws per chain, after discarding the original 100 draws and the first 200 extension draws.

## Gate summary

- Chains completed: 4/4
- Total retained draws per chain: 950
- Diagnostic tail draws per chain: 650
- Constraint-validation failures: 0
- Maximum primary-parameter R-hat: 1.0631
- Minimum primary bulk ESS: 73.2
- Maximum latent-summary R-hat: 1.0489
- Minimum latent-summary bulk ESS: 75.2
- Median final fraction of free cells changed from the original dispersed starts: 0.5960
- Extended pilot status: PASS

## Primary contrasts, explicitly nonfinal

| Parameter | Pilot median | Pilot 95% interval | v1.1.1 median | Relative shift | R-hat | Bulk ESS |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| primary_rurality_metro_other | 1.1389 | 1.1050–1.1739 | 1.1405 | -0.14% | 1.0129 | 138.2 |
| primary_rurality_nonmetro_adjacent | 1.2701 | 1.2142–1.3200 | 1.2726 | -0.20% | 1.0275 | 73.2 |
| primary_rurality_nonmetro_nonadjacent | 1.2334 | 1.1683–1.2938 | 1.2350 | -0.12% | 1.0224 | 87.6 |
| svi_quartile_Q2 | 1.1106 | 1.0701–1.1590 | 1.1128 | -0.20% | 1.0336 | 111.0 |
| svi_quartile_Q3 | 1.2505 | 1.2025–1.3152 | 1.2513 | -0.06% | 1.0500 | 89.6 |
| svi_quartile_Q4_highest | 1.4347 | 1.3754–1.5149 | 1.4330 | 0.12% | 1.0631 | 76.4 |

These values remain tuning evidence and must not be copied into the manuscript. A corrected eight-chain production run requires prespecified final convergence thresholds and complete parameter and latent-summary validation.
