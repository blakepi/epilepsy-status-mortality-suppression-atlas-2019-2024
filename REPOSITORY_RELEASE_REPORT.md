# Repository Release Report

Release date: 2026-07-15

Release: `v1.1.0`

## Scope

Version 1.1.0 promotes the constrained Bayesian analysis to the public reproducibility release. It includes the final eight-chain production parameter draws and statuses, all-parameter convergence diagnostics, compressed constraint-validation evidence, checksum manifests, county posterior summaries, final public tables and figures, manuscript Markdown, supplement Markdown, and release-time QC.

The earlier observed-only, bounding, residual-allocation, and interval-likelihood analysis remains available as contextual and sensitivity material.

## Production verification

- 8 completed chains, seeds 18291–18298
- 300,000 iterations per chain; 75,000 burn-in; thinning 50
- 4,500 retained draws per chain; 36,000 draws per parameter
- 69 retained parameters
- Maximum rank-normalized split R-hat: 1.008554
- Minimum bulk ESS: 1437.2
- Minimum tail ESS: 3199.4
- 489,696 constraint-validation records; 0 failures

## Public artifact policy

Included: parameter draws, resolved configs, statuses, acceptance/runtime summaries, all-parameter diagnostics, compressed validation evidence, county summaries, manifests, model frame, code, tables, figures, and manuscript text.

Excluded: large latent arrays, temporary arrays, checkpoints, caches, runtime environments, logs, submission ZIPs, DOCX duplicates, and TIFF duplicates. Large excluded latent arrays are represented by cryptographic hashes and full validation summaries.

## Known limitations

- Some proposal acceptance rates are outside the nominal tuning target; all-parameter convergence criteria nevertheless pass.
- An exact enumerated small-state stationary-distribution and irreducibility test for the custom latent-count transition kernel remains recommended before journal submission.

## Identifiers

- GitHub: https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024
- GitHub release: https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024/releases/tag/v1.1.0
- Zenodo concept DOI: https://doi.org/10.5281/zenodo.20691622

The immutable Zenodo version DOI is assigned after the GitHub release is archived.
