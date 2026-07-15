# Production Chain Verification

## Frozen run

- Source: exact Wahab HPC production archive
- Chains: 8 (`chain_01` through `chain_08`)
- Seeds: 18291–18298
- Iterations: 300,000 per chain
- Burn-in: 75,000
- Thinning: 50
- Retained draws: 4,500 per chain; 36,000 per parameter
- Retained parameters: 69

The release verifier checked the per-chain resolved configuration and completion status, parameter-draw shape and finiteness, expected seed and iteration metadata, every saved latent array's shape and integer totals, every latent validation record, and fixed SHA-256 hashes for the final merged support artifacts.

## Convergence result

- Maximum rank-normalized split R-hat: 1.0085537588710927 (`state_effect[11]`)
- Minimum bulk ESS: 1437.2439572757296
- Minimum 5%/95% tail ESS: 3199.3579952429254
- Primary nonmetro nonadjacent contrast: R-hat 1.0009353605050912; bulk ESS 4024.3950396146324; tail ESS 8819.052613526208
- Constraint validation: 489,696 records; 0 failures

The release gate requires R-hat at most 1.01 and both bulk and tail ESS at least 400 for every retained parameter. All 69 passed.

## Provenance correction

Earlier local publication assets mixed final scalar estimates with county summaries from a stale four-chain development run. Version 1.1.0 routes every manuscript table, county file, map, and validation figure to the checksum-verified eight-chain production archive. The rebuilt QC fails closed when a configured source hash is absent or differs from the production manifest.

## Sampler correction and interpretation

Saved state and year effects in the archived production run were centered before storage. Future proposals and checkpoints now explicitly recenter these effects, removing an unidentifiable additive direction from the raw sampler state without changing the archived centered inference.

Proposal acceptance for beta was approximately 0.082–0.085, for log-kappa approximately 0.65, for log-sigma-state approximately 0.815, and for log-sigma-year approximately 0.94. These are retained as efficiency warnings because the all-parameter convergence criteria passed.

## Remaining methodological test

The constraint-preserving latent-count transition kernel has extensive invariant validation, but the release does not yet include an exact small-state enumeration test establishing its stationary distribution and irreducibility. This targeted test remains the principal unresolved methodological check before journal submission.

## Public-versus-large artifacts

The public release includes all per-chain parameter draws, chain statuses, resolved configurations, acceptance and runtime summaries, compressed validation records, county summaries, diagnostics, and manifests. Large latent arrays are omitted; their cryptographic hashes and complete validation evidence are retained in the public manifests and reports.
