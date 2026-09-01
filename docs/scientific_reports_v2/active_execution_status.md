# Scientific Reports v2 active execution status

Updated: 2026-08-18

## Interpretation boundary

The archived `v1.1.1` release remains the immutable baseline. The corrected eight-chain production run completed, and `outputs/scientific_reports_v2/production_8chain/production_gate.json` records `passed: true` with action `freeze_corrected_results`; those corrected outputs are frozen computational evidence for downstream sensitivity analyses. Manuscript result freeze remains on HOLD until the triggered identifiable structured-plus-unstructured county spatial sensitivity passes, along with the other prespecified robustness and package gates. Pilot values are tuning evidence and must not be copied into the manuscript.

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

## Substantive work completed in the current execution tranche

### Multi-replicate truth-known calibration, completed 20-replicate program

A reusable four-replicate batch was implemented and completed through GitHub Actions. The program was then expanded with 16 independently seeded replicates, producing five replicates under each of four frozen conditions:

1. baseline rate 3.4 per 100,000 with NB2 kappa 10;
2. lower rate 2.4 per 100,000 with kappa 10;
3. higher rate 5.0 per 100,000 with kappa 10;
4. baseline rate 3.4 per 100,000 with stronger overdispersion, kappa 4.

Each replicate used a truth-known 72-county panel, the public 1–9 suppression rule, compatible county-period and geographic aggregates, four dispersed feasible starts, and four corrected chains of 24,000 iterations with 6,000 burn-in iterations and thinning of 10. All 20 replicates passed the computational gate with zero constraint-validation failures.

Across 120 prespecified coefficient-by-replicate intervals, 114 covered the true IRR (95.0%; exact binomial 95% Monte Carlo interval 89.4%–98.1%). Contrast-specific coverage ranged from 90% to 100%. Across 4,337 suppressed cells, cell-weighted 95% interval coverage was 99.38% and posterior-mean RMSE was 1.01 deaths. The descriptive calibration reporting gate passed, while the repository explicitly records `precise_nominal_coverage_claim_authorized: false`.

Evidence:

- `outputs/scientific_reports_v2/calibration_study_batch1/`
- `outputs/scientific_reports_v2/calibration_study_batch2/`
- `outputs/scientific_reports_v2/calibration_program/`

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

### Manuscript fail-closed QC and citation normalization

Working-draft QC passed. The title contains 14 words, the unstructured abstract contains 184 words, six keywords are present, all required sections and mathematical subsections were detected, all locked placeholders are registered, prohibited pilot literals are absent, and the supplement states the constraint rank/nullity and kernel-validation evidence.

The numeric citation normalizer corrected four semantic reference mappings, confirmed 17 contiguous references, and found no out-of-range citations. The six journal references were then verified against current PubMed records for title, journal, volume, locator, year, PMID, and DOI; that bibliographic metadata gate passed. Web-source access dates and the final repository DOI remain release-time gates.

Evidence:

- `outputs/scientific_reports_v2/manuscript_scaffold_qc/`
- `outputs/scientific_reports_v2/citation_qc/`

### Spatial-dependence work

A reproducible county-adjacency and Moran diagnostic module has been implemented with unit tests. The post-production script:

- downloads and checksums the official 2024 U.S. Census Bureau county-adjacency file;
- reconstructs posterior-mean expected county-period deaths from corrected production draws;
- computes raw and conditional Pearson residuals;
- evaluates global Moran's I with 9,999 deterministic permutations;
- evaluates within-state Moran statistics where at least ten connected counties are available;
- records a prespecified trigger for a structured county spatial-effect sensitivity model.

The diagnostic refuses to run unless the corrected production gate has passed.

The production diagnostic completed on 2026-08-18 UTC from the frozen passed-production inputs. It included 3,142 counties (3,128 with at least one model neighbor). Global Moran's I was 0.2312117978976916 for the raw residual and 0.11730487181632097 for the conditional Pearson residual; both two-sided 9,999-permutation P values were 0.0001. Nineteen within-state Pearson rows also met the prespecified materiality rule, exceeding the repeated-state threshold of three. The exact generated action is `run_spatial_random_effect_sensitivity`.

Accordingly, an identifiable scaled structured-plus-unstructured county spatial sensitivity is required and must pass before manuscript result freeze. The Moran diagnostic is a model check, not causal evidence; neither a trigger nor a non-trigger would establish spatial dependence or independence.

Evidence:

- `outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json`
- `outputs/scientific_reports_v2/spatial_residual_diagnostics/global_morans_i.csv`
- `outputs/scientific_reports_v2/spatial_residual_diagnostics/within_state_morans_i.csv`
- `outputs/scientific_reports_v2/spatial_residual_diagnostics/production_input_sha256.csv`
- `outputs/scientific_reports_v2/spatial_residual_diagnostics/county_adjacency2024.txt`

### Explicit prior profiles and prior-sensitivity infrastructure

The primary prior is now represented as an explicit immutable `PriorSpecification` with default values identical to the corrected primary target. Broader and regularizing profiles can be activated through an exception-safe process context that reuses the same validated sampler instead of duplicating transition code. Unit tests verify default equivalence, profile parsing, target-density changes, context restoration, and fail-closed invalid-scale handling.

Guarded preparation, chain, and summary scripts have been added for four broader-prior and four regularizing-prior chains. They require a passed corrected production gate, generate fresh feasible starts with profile-specific seeds, report all-parameter diagnostics, and compare material IRR shifts and interval overlap with the primary posterior. The infrastructure audit passed; no prior-sensitivity chain has been launched before production.

Evidence: `outputs/scientific_reports_v2/prior_sensitivity_infrastructure/`.

### Robustness registry

`config/scientific_reports_v2_robustness_registry.yaml` freezes the primary estimand, default/broader/regularizing priors, production seeds and thresholds, suppression comparators, pandemic analyses, model-family sensitivity, age-structure plan, spatial diagnostic, spatial-model trigger, and truth-known calibration scenarios before corrected results are available.

## Corrected production completion

The authenticated Wahab launch completed on 2026-08-13 UTC from commit `11691bd882020f76e1b6eb6224e4789a6534f65c` after the launch-readiness audit passed and the frozen evidence/configuration hashes were recorded. Slurm accepted:

- eight-chain production array job `6647934` (`epi_sr_v2_prod`); and
- dependent merger/final-gate job `6647935` (`epi_sr_v2_final`), scheduled with `afterok:6647934`.

The historical submission record is `outputs/scientific_reports_v2/production_8chain/submitted_jobs.tsv` in the authenticated Wahab checkout. The eight production chains and dependent merger/final-gate workflow subsequently completed. The gate generated on 2026-08-14 UTC records eight completed 300,000-iteration chains, 4,500 saved draws per chain, zero constraint failures across 489,696 validation records, `passed: true`, and action `freeze_corrected_results`. Corrected primary results are therefore frozen for downstream analysis; the distinct current HOLD is the triggered identifiable structured-plus-unstructured county spatial sensitivity, which must pass before manuscript result freeze.

## Immediate sequence after corrected production passes

1. Freeze corrected parameter and county summaries.
2. Implement, execute, and pass the triggered structured-plus-unstructured county spatial sensitivity.
3. Run broader and regularizing prior profiles using the validated sensitivity runner.
4. Run model-family and pandemic-period sensitivities.
5. Populate manuscript placeholders only from frozen machine-readable outputs.
6. Generate main figures, supplementary diagnostics, and the immutable archive.
7. Run submission-mode manuscript and package QC.
