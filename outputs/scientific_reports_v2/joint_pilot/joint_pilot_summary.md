# Scientific Reports v2 corrected joint pilot

Four corrected chains jointly updated latent counts and model parameters from dispersed feasible allocations. This run is intentionally short and is used only to identify gross target, mixing, and proposal-tuning failures before HPC production.

## Gate summary

- Chains completed: 4/4
- Retained draws per chain: 100
- Constraint-validation failures: 0
- Maximum primary-parameter R-hat: 1.6946
- Maximum rurality/SVI latent-summary R-hat: 1.3475
- Median final fraction of free cells changed: 0.4697
- Pilot status: HOLD

## Primary contrasts, explicitly nonfinal

| Parameter | Pilot median | Pilot 95% interval | v1.1.1 median | Relative shift | R-hat |
| --- | ---: | --- | ---: | ---: | ---: |
| primary_rurality_metro_other | 1.1458 | 1.1027–1.2093 | 1.1405 | 0.46% | 1.5486 |
| primary_rurality_nonmetro_adjacent | 1.2698 | 1.2057–1.3474 | 1.2726 | -0.22% | 1.5187 |
| primary_rurality_nonmetro_nonadjacent | 1.2464 | 1.1735–1.3464 | 1.2350 | 0.92% | 1.6946 |
| svi_quartile_Q2 | 1.1015 | 1.0440–1.1467 | 1.1128 | -1.02% | 1.1578 |
| svi_quartile_Q3 | 1.2348 | 1.1801–1.2934 | 1.2513 | -1.32% | 1.4027 |
| svi_quartile_Q4_highest | 1.4017 | 1.3292–1.4864 | 1.4330 | -2.18% | 1.4010 |

These values must not be copied into the manuscript. Production settings require a longer tuning run, eight independent chains, prespecified convergence thresholds, and full latent-summary diagnostics.
