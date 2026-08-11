# Full-data fixed-theta latent movement pilot

Four independently generated v1 initial allocations were evolved for 25,000 corrected latent-count proposals each while holding model parameters fixed at the archived v1.1.1 posterior medians. This is a movement and tuning diagnostic only; it is not a corrected posterior analysis and does not update the manuscript estimate.

| Quantity | Value |
| --- | ---: |
| Chains | 4 |
| Proposals per chain | 25,000 |
| Minimum final fraction of free cells changed | 0.1517 |
| Median final fraction of free cells changed | 0.1590 |
| Maximum final fraction of free cells changed | 0.1625 |
| Minimum final L1 distance over free cells | 3,460 |
| Median pairwise final/start L1 ratio | 0.9582 |
| Unique recorded state hashes | 204 |

## Acceptance by move

| Move | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| county_period_exploration | 0.1532 | 0.1616 | 0.1654 |
| cycle_swap | 0.0077 | 0.0086 | 0.0101 |
| interval_path_transfer | 0.1031 | 0.1119 | 0.1254 |
| state_year_transfer | 0.0357 | 0.0371 | 0.0423 |
| swap_2x2 | 0.0310 | 0.0341 | 0.0365 |

The next pilot must update parameters jointly, use eight independently dispersed starts, and compute latent-summary autocorrelation and between-chain convergence. No epidemiologic estimate is authorized from this fixed-theta diagnostic.
