# Scientific Reports v2 residual spatial-dependence diagnostic

This analysis is conditional on a passed corrected eight-chain production gate. County-period posterior-mean count residuals were compared with county adjacency using global and within-state Moran statistics.

| Residual | Moran's I | Expected under randomization | Two-sided permutation p | Nonisolated counties |
| --- | ---: | ---: | ---: | ---: |
| raw_residual | 0.23121 | -0.00032 | 0.00010 | 3128 |
| pearson_residual | 0.11730 | -0.00032 | 0.00010 | 3128 |

Prespecified action: **run_spatial_random_effect_sensitivity**.

The diagnostic uses the posterior-mean conditional expectation and therefore does not propagate the full posterior distribution into the Moran statistic. It is intended as a transparent residual check and trigger for the separately prespecified spatial sensitivity model.
