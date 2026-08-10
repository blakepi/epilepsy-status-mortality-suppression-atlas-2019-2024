# Full-data fixed-theta latent movement pilot

Four independently generated v1 initial allocations were evolved for 25,000 corrected latent-count proposals each while holding model parameters fixed at the archived v1.1.1 posterior medians. This is a movement and tuning diagnostic only; it is not a corrected posterior analysis and does not update the manuscript estimate.

| Quantity | Value |
| --- | ---: |
| Chains | 4 |
| Proposals per chain | 25,000 |
| Minimum final fraction of free cells changed | 0.0851 |
| Median final fraction of free cells changed | 0.0877 |
| Maximum final fraction of free cells changed | 0.0937 |
| Minimum final L1 distance over free cells | 1,106 |
| Median pairwise final/start L1 ratio | 0.9857 |
| Unique recorded state hashes | 204 |

## Acceptance by move

| Move | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| county_period_exploration | 0.0969 | 0.1068 | 0.1105 |
| cycle_swap | 0.0021 | 0.0035 | 0.0062 |
| state_year_transfer | 0.0205 | 0.0233 | 0.0238 |
| swap_2x2 | 0.0190 | 0.0226 | 0.0232 |

The next pilot must update parameters jointly, use eight independently dispersed starts, and compute latent-summary autocorrelation and between-chain convergence. No epidemiologic estimate is authorized from this fixed-theta diagnostic.
