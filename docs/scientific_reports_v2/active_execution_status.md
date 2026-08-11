# Scientific Reports v2 active execution status

Updated: 2026-08-11

## Interpretation boundary

The archived `v1.1.1` release remains the immutable baseline. No corrected empirical estimate is authorized until the new eight-chain production run completes and `outputs/scientific_reports_v2/production_8chain/production_gate.json` records `passed: true`. Pilot values are tuning evidence and must not be copied into the manuscript.

## Completed technical-soundness gates

- Corrected the centered state/year prior normalization and stale joint-target bookkeeping.
- Added general alternating-cycle and interval-path latent moves.
- Passed deterministic exact finite-state stationarity, detailed-balance, connectivity, and empirical-frequency checks.
- Passed randomized exact finite-state validation.
- Audited the full constraint geometry: 9,695 latent variables, 1,256 independent equalities, and equality nullity 8,439 before bounds and interval inequalities.
- Demonstrated movement from deliberately dispersed feasible starts in the corrected real-data pilot.
- Passed the four-chain extended real-data pilot gate with zero constraint failures.
- Built and passed a truth-known synthetic suppression design.
- Passed a tuned one-replicate calibration extension with zero constraint failures and all six prespecified coefficient truths covered.
- Passed final production-infrastructure and launch-readiness audits.

## Substantive work started in the current execution tranche

### Multi-replicate truth-known calibration

A reusable four-replicate batch has been implemented and launched through GitHub Actions. Batch 1 spans:

1. baseline rate 3.4 per 100,000 with NB2 kappa 10;
2. lower rate 2.4 per 100,000 with kappa 10;
3. higher rate 5.0 per 100,000 with kappa 10;
4. baseline rate 3.4 per 100,000 with stronger overdispersion, kappa 4.

Each replicate creates a truth-known 72-county panel, applies the public 1–9 suppression rule, constructs compatible county-period and geographic aggregates, generates four dispersed feasible starts, runs four corrected chains for 24,000 iterations, and aggregates coefficient and suppressed-cell recovery. Exact binomial intervals are reported so four replicates cannot be misrepresented as a precise nominal-coverage study.

Active workflow: `Scientific Reports v2 calibration study batch 1`.

### Method-forward manuscript and technical supplement

A new nonfinal Scientific Reports manuscript was created under `manuscript/scientific_reports_v2/`. It:

- foregrounds suppression-aware constrained inference;
- distinguishes the contribution from prior Bayesian censored-WONDER work;
- gives the complete NB2 likelihood and linear predictor;
- states every primary prior and the corrected subspace normalization;
- documents feasible initialization and every latent proposal family;
- reports constraint rank, redundancy, and nullity;
- documents exact finite-state validation;
- prespecifies convergence, calibration, prior, temporal, model-family, age, and spatial analyses;
- contains locked placeholders instead of pilot or unvalidated production values;
- removes scientific-result labels tied to a named computing cluster;
- replaces the Elsevier AI-policy reference with a factual methods disclosure.

A technical supplement now contains the full target density, move definitions, exact-validation evidence, production gate, calibration design, robustness registry, and shells for final tables.

### Manuscript fail-closed QC

A placeholder manifest maps every locked result sentence to its required source and gate. Working-draft QC checks title length, abstract length and structure, keyword count, required mathematical sections, unregistered placeholders, prohibited pilot literals, Elsevier-policy text, cluster-result language, and required supplement content. Submission mode additionally requires zero unresolved placeholders and a passed corrected production gate.

Active workflow: `Scientific Reports v2 substantive scaffold audit`.

### Spatial-dependence work

A reproducible county-adjacency and Moran diagnostic module has been implemented with unit tests. The post-production script:

- downloads and checksums the official 2024 U.S. Census Bureau county-adjacency file;
- reconstructs posterior-mean expected county-period deaths from corrected production draws;
- computes raw and conditional Pearson residuals;
- evaluates global Moran's I with 9,999 deterministic permutations;
- evaluates within-state Moran statistics where at least ten connected counties are available;
- records a prespecified trigger for a structured county spatial-effect sensitivity model.

The diagnostic refuses to run unless the corrected production gate has passed.

### Robustness registry

`config/scientific_reports_v2_robustness_registry.yaml` freezes the primary estimand, default/broader/regularizing priors, production seeds and thresholds, suppression comparators, pandemic analyses, model-family sensitivity, age-structure plan, spatial diagnostic, spatial-model trigger, and truth-known calibration scenarios before corrected results are available.

## Authenticated compute boundary

The only step that cannot be launched through the repository connector is the full Wahab Slurm production run. The guarded command remains:

```bash
bash hpc/wahab/submit_sr_v2_production_ready.sh
```

That helper reruns launch-readiness checks, freezes configuration and evidence hashes, stages the required code and validation evidence, submits eight independent corrected production chains, and schedules the merger/final gate with an `afterok` dependency.

## Immediate sequence after corrected production passes

1. Freeze corrected parameter and county summaries.
2. Run the spatial residual diagnostic and trigger the spatial sensitivity if required.
3. Run broader and regularizing prior profiles.
4. Run model-family and pandemic-period sensitivities.
5. Complete additional truth-known calibration batches before making nominal coverage claims.
6. Populate manuscript placeholders only from frozen machine-readable outputs.
7. Generate main figures, supplementary diagnostics, and the immutable archive.
8. Run submission-mode manuscript and package QC.
