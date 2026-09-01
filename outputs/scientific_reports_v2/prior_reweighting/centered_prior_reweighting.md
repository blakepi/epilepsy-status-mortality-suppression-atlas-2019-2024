# Importance reweighting for the centered-prior normalization correction

The corrected target differs from the archived v1.1.1 target by the exact multiplicative factor sigma_state × sigma_year. Archived joint parameter draws were therefore importance-reweighted to estimate the isolated effect of this prior-normalization correction before launching a new production run.

This calculation does not repair or assess latent-state mixing and does not replace the corrected rerun. It is an efficient diagnostic of whether the prior correction alone is likely to move the principal parameter estimates.

## Weight diagnostics

- Draws: 36,000
- Importance ESS: 30311.7
- ESS fraction: 0.8420
- Maximum normalized weight: 0.00016309
- Weight coefficient of variation: 0.4332

## Focus estimates

| Parameter | v1.1.1 median | Reweighted median | v1.1.1 95% interval | Reweighted 95% interval | Relative median shift |
| --- | ---: | ---: | --- | --- | ---: |
| primary_rurality_metro_other | 1.140521 | 1.140384 | 1.105062–1.177531 | 1.104976–1.177282 | -0.0120% |
| primary_rurality_nonmetro_adjacent | 1.272649 | 1.272403 | 1.221224–1.325861 | 1.220567–1.325490 | -0.0193% |
| primary_rurality_nonmetro_nonadjacent | 1.234985 | 1.234585 | 1.170514–1.302017 | 1.169902–1.301579 | -0.0324% |
| sigma_state | 0.188080 | 0.190620 | 0.151736–0.238307 | 0.153955–0.242137 | 1.3510% |
| sigma_year | 0.138482 | 0.157379 | 0.079782–0.316811 | 0.085955–0.403976 | 13.6461% |
| svi_quartile_Q4_highest | 1.432987 | 1.433320 | 1.369870–1.499755 | 1.369958–1.500250 | 0.0232% |

Interpretation is conditional on the archived joint sample adequately representing the v1.1.1 target. The final Scientific Reports v2 estimates must come from newly sampled corrected chains.
