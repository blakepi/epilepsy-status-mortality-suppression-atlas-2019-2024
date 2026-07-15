# v1.1.0 — Verified constrained Bayesian production release

This release adds the checksum-verified eight-chain Wahab HPC production analysis and its publication artifacts.

## Highlights

- 8 completed production chains; 36,000 retained draws per parameter.
- Modern rank-normalized R-hat plus bulk and 5%/95% tail ESS for all 69 parameters.
- Maximum R-hat 1.0086; minimum bulk ESS 1437.2; minimum tail ESS 3199.4.
- 489,696 latent-count constraint-validation records with zero failures.
- Per-chain parameter draws, statuses, resolved configs, acceptance/runtime summaries, compressed validation evidence, county posterior summaries, and SHA-256 manifests.
- Publication tables, figures, manuscript Markdown, supplement Markdown, and fail-closed QC rebuilt from the exact production run.
- Future sampler proposals/checkpoints explicitly center state and year effects.

## Important correction

Earlier local publication assets mixed final scalar estimates with county outputs from a stale development run. All v1.1.0 publication artifacts are routed to the checksum-verified eight-chain production archive.

## Remaining limitation

The custom constraint-preserving latent-count kernel does not yet have an exact enumerated small-state stationary-distribution and irreducibility test. This remains the principal methodological check recommended before journal submission.

Large latent arrays are excluded from GitHub/Zenodo because of size; hashes and complete validation evidence are included.
