# Full-data fixed-theta latent movement pilot

Four independently generated v1 initial allocations were evolved for 25,000 corrected latent-count proposals each while holding model parameters fixed at the archived v1.1.1 posterior medians. This is a movement and tuning diagnostic only; it is not a corrected posterior analysis and does not update the manuscript estimate.

| Quantity | Value |
| --- | ---: |
| Chains | 4 |
| Proposals per chain | 25,000 |
| Minimum final fraction of free cells changed | 0.1277 |
| Median final fraction of free cells changed | 0.1362 |
| Maximum final fraction of free cells changed | 0.1416 |
| Minimum final L1 distance over free cells | 3,010 |
| Median pairwise final/start L1 ratio | 0.9698 |
| Unique recorded state hashes | 204 |

## Acceptance by move

| Move | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| county_period_exploration | 0.1469 | 0.1615 | 0.1676 |
| cycle_swap | 0.0063 | 0.0076 | 0.0081 |
| state_year_transfer | 0.0337 | 0.0341 | 0.0369 |
| swap_2x2 | 0.0298 | 0.0349 | 0.0392 |

The next pilot must update parameters jointly, use eight independently dispersed starts, and compute latent-summary autocorrelation and between-chain convergence. No epidemiologic estimate is authorized from this fixed-theta diagnostic.
