# Scientific Reports v2 execution plan

## Baseline and target

- Frozen baseline: tag `v1.1.1`, commit `50b468d212616ee80be55045dedf8a696db14df5`.
- Development branch: `scientific-reports-v2`.
- Target journal: *Scientific Reports*.
- Canonical framing: methodological problem first, epilepsy/status epilepticus application second, rural-health result third.
- No v1.1.1 files or tags will be rewritten. All corrected outputs will use a new v2 namespace and provenance chain.

## Reconciliation of the external research report with v1.1.1

Several concerns in the research report were based on an earlier submission package and are already resolved in v1.1.1:

- The main manuscript now states the NB2 likelihood structure, linear predictor, and all fixed-effect, random-effect-scale, and dispersion priors.
- Release-time convergence diagnostics cover all 69 retained parameters, not only the primary rurality coefficient.
- The verified production run contains eight completed chains, 36,000 retained parameter draws, modern rank-normalized R-hat/bulk ESS/tail ESS/MCSE diagnostics, and 489,696 zero-failure latent validation records.
- Public artifacts are checksum-gated to the eight-chain production source rather than the stale four-chain development source.

These resolved items still require clearer mathematical exposition in the Scientific Reports manuscript and supplement, but they are not reasons to repeat the existing production run by themselves.

## Remaining submission-critical risks

1. **Sampler correctness beyond feasibility.** Every retained state is legal, but exact small-state evidence is still needed that the transition kernel targets the intended posterior and can traverse the relevant feasible state space.
2. **Random-effect parameterization audit.** Confirm the prior density and normalization under the enforced sum-to-zero state/year parameterization; correct and rerun if necessary.
3. **Local runner bookkeeping defect.** Repair stale log-posterior bookkeeping after latent-count updates in the non-HPC runner and add regression tests. The archived HPC path refreshes this quantity before parameter updates, but all advertised execution paths must be valid.
4. **Constraint information geometry.** Quantify nominal constraints, independent rank, algebraic redundancies, inequality/bound constraints, and affine-space nullity after fixed cells are removed.
5. **Latent-space exploration diagnostics.** Add movement frequencies, representative-cell/function ESS, between-chain agreement, initialization sensitivity, log-posterior traces, and transition diagnostics.
6. **Calibration and model adequacy.** Add exact toy-posterior validation, synthetic or masking calibration, and non-tautological posterior predictive/model-fit checks.
7. **Epidemiologic robustness.** Add prior sensitivity, richer age-composition sensitivity where source data permit, residual spatial-dependence testing, and pandemic/year-effect sensitivity.
8. **Disclosure-safe output review.** Reassess public named-county posterior count summaries and main-text atlas placement; keep protected counts distinct from model-derived quantities.

## Execution sequence and hard gates

### Phase 1 — inferential-engine repair and mathematical audit

Deliverables:

- Derivation of the intended joint posterior and constrained random-effect parameterization.
- Unit test exposing and then repairing the local-runner stale-posterior defect.
- Independent confirmation or correction of the sum-to-zero random-effect prior.
- Tests that fixed-cell, interval, county-period, state-year, and higher-level constraints remain invariant after all move classes.
- A versioned mathematical model specification with exact NB2 parameterization and priors.

**Gate 1:** no production rerun until all engine tests pass and the target density is unambiguous.

### Phase 2 — exact constrained-kernel validation

Construct multiple small systems whose full feasible state space can be enumerated. For each system:

- enumerate all feasible integer allocations;
- calculate the exact normalized posterior;
- construct or empirically estimate the sampler transition matrix;
- test detailed balance/stationarity as appropriate;
- verify irreducibility/connectivity and aperiodicity, or explicitly identify limitations;
- compare long-run sampled state frequencies with exact probabilities;
- test all move classes separately and jointly.

Add deliberately adversarial examples with tight county-period margins, exact margins, interval margins, and multiple disconnected-looking blocks.

**Gate 2:** the corrected kernel must reproduce exact toy posteriors within prespecified Monte Carlo tolerances before any epidemiologic inference is accepted.

### Phase 3 — constraint rank, redundancy, and identifiability

Build the linear system on the free latent variables after subtracting fixed exact/zero contributions. Report:

- number of free suppressed variables;
- nominal equality constraints by level;
- rank after dependent rows are removed;
- nullity of the equality-constrained affine space;
- number and type of interval/bound inequalities;
- which national-year and grand-total rows are algebraically implied by state-year totals;
- how county-period inequalities further restrict, but do not necessarily identify, cell counts.

Higher-level totals that are algebraically redundant will be described as validation/reconciliation checks rather than independent information.

**Gate 3:** manuscript language about what the public constraints identify must match the rank analysis exactly.

### Phase 4 — corrected production pilot and final run

Run a short tuning pilot from deliberately dispersed feasible starts, including randomized and extremal MILP objectives where feasible. Then run the corrected eight-chain analysis under a frozen configuration.

Required diagnostics:

- all-parameter rank-normalized split R-hat, bulk ESS, tail ESS, and MCSE;
- proposal and move-class acceptance rates;
- fraction of free cells moved and distance traveled from initialization;
- representative latent-cell and latent-summary autocorrelation/ESS;
- chain agreement for rurality-, SVI-, state-, and county-level latent summaries;
- log-posterior traces;
- exact constraint validation for every retained latent draw;
- comparison of v1.1.1 and v2 primary/secondary estimates.

**Gate 4:** freeze v2 inference only if the corrected run passes all diagnostics and substantive conclusions are not an artifact of the correction. Any material change will be reported rather than hidden.

### Phase 5 — calibration, predictive checks, and method comparison

Use a two-tier validation design to remain rigorous but computationally practical:

1. **Exact small-system calibration:** complete posterior truth is known from enumeration.
2. **Realistic synthetic/masking calibration:** use real or representative county populations/covariates, generate complete counts under known coefficients and dispersion, impose WONDER-style suppression and analogous public constraints, then compare:
   - visible-only deletion;
   - fixed substitutions;
   - residual allocation;
   - interval likelihood;
   - corrected constrained Bayesian inference.

Primary metrics:

- bias and RMSE of rurality/SVI coefficients;
- 95% interval coverage and width;
- false-positive behavior under null effects;
- recovery of standardized rates;
- calibration/coverage of selected latent summaries;
- runtime and failure rates.

Simulation size will be selected after a benchmark pilot and documented with Monte Carlo uncertainty. Include at least one mild model-misspecification condition.

Posterior/model-fit checks on the observed application will include exact-cell predictive calibration and residual summaries stratified by rurality, SVI, year, population, and state. Hard-constraint satisfaction will not be presented as a model-fit test.

**Gate 5:** method-forward claims must be supported by calibration results; if calibration is weak, the paper will be reframed as an applied analysis with explicit limitations.

### Phase 6 — focused epidemiologic robustness

Run only reviewer-relevant analyses:

- broader and more regularizing prior families;
- exclusion of covariate-imputed counties and denominator-imputed rows;
- alternative rurality classification;
- richer age composition if available from the source covariate files;
- residual Moran's I or an equivalent spatial diagnostic;
- a spatial sensitivity model only if residual dependence is material and a defensible implementation is feasible;
- rurality-by-year or pandemic-period interaction within the full constrained system;
- model-family/overdispersion sensitivity;
- G40/G41 decomposition only if equivalent public constraints permit valid inference.

**Gate 6:** the headline conclusion must survive the prespecified high-value sensitivities or be rewritten accordingly.

### Phase 7 — Scientific Reports manuscript rebuild

Provisional title:

> Suppression-aware Bayesian estimation of county mortality using public aggregate constraints: U.S. epilepsy, 2019–2024

Planned structure:

1. Introduction
2. Results
   - suppression structure and constraint geometry;
   - exact/simulation validation and sampler diagnostics;
   - corrected primary rurality and SVI estimates;
   - consequences of alternative suppression handling;
   - focused robustness analyses.
3. Discussion without excessive subheadings
4. Methods
   - data/query provenance;
   - mathematical model and priors;
   - constraint system and rank analysis;
   - sampler algorithm;
   - exact validation, calibration, diagnostics, and sensitivities;
   - ethics, AI use, data availability, and code availability.

Main displays:

- Figure 1: suppression and constraint architecture with a worked county example.
- Figure 2: exact/synthetic calibration and method performance.
- Figure 3: corrected posterior associations plus interpretable absolute rates where useful.
- Figure 4: consequences of alternative suppression handling.
- Table 1: data structure, nominal constraints, independent rank, and nullity.
- Table 2: primary estimates with comprehensive diagnostics.

Move the detailed county atlas, full scenario table, absolute-rate table, complete diagnostics, prior sensitivity, spatial diagnostics, contextual COVID/underlying-cause analyses, and full county outputs to Supplementary Information or the repository.

Scientific Reports production requirements to enforce:

- title no more than 20 words;
- unstructured abstract no more than 200 words;
- no more than six keywords;
- Nature sequential numerical reference style;
- separate Data availability and Code availability sections;
- factual LLM-use documentation in Methods with no Elsevier policy citation;
- explicit competing-interests and author-contribution statements;
- separate Supplementary Information file beginning with title and author list.

### Phase 8 — reproducibility freeze and adversarial review

- Generate one immutable v2 analysis release and archive DOI.
- Make every manuscript number traceable to a frozen artifact and commit.
- Make QC fail closed on stale source hashes, missing diagnostics, placeholder values, or mismatched figures/tables.
- Conduct independent adversarial statistical, epidemiologic, privacy/disclosure, and Scientific Reports format reviews.
- Render and visually inspect every manuscript and supplement page.

**Final submission gate:** no submission until engine correctness, exact validation, rank analysis, corrected convergence, calibration, focused robustness, manuscript consistency, and reproducibility checks all pass.

## What is deliberately deferred

- No cosmetic rewrite before the corrected inference is frozen.
- No claim that Bayesian modeling of suppressed WONDER data is itself novel.
- No claim that individual suppressed counts have been recovered.
- No main-text county atlas unless it materially advances the argument and passes disclosure review.
- No SIAM-style theorem paper unless later work establishes a generalized Markov-basis/irreducibility theory; that would be a separate project.

## Publication positioning

The v2 paper will make two connected claims:

1. **Methodological:** bounded suppressed counts and compatible cross-scale public constraints can support uncertainty-aware regression inference when the constrained kernel is validated and remaining uncertainty is propagated.
2. **Applied:** in the corrected epilepsy/status epilepticus analysis, suppression handling materially affects rurality estimates, and the validated constrained model provides the final association estimates.

The broad rural mortality disparity will be presented as corroboration/refinement of prior literature, not a first discovery.
