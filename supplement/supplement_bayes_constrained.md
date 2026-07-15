# Supplementary Material

## Supplementary Methods

### Data extracts and constraint construction

The constrained Bayesian workflow modeled county-year latent counts while preserving public CDC WONDER suppression intervals and aggregate totals. Exact cells, zero cells, suppressed 1–9 cells, county-period constraints, state-year totals, national-year totals, and the reconciled 2019–2024 total of 58,380 deaths defined the feasible latent-count space.

### Model specification

The primary model used a negative-binomial-2 mortality model with log population offset, rurality, SVI quartile, standardized percentage aged ≥65 years, standardized percentage male, centered year effects, and centered state/DC effects. Large metropolitan counties and SVI Q1 were reference categories. Prior distributions were normal for fixed and random effects, half-normal for state/year scale parameters, and log-normal for the negative-binomial shape parameter, as specified in the main Methods.

### Sampler and validation

Latent counts were updated only through moves that preserved the hard public constraints. Eight chains used seeds 18291–18298, ran 300,000 iterations, discarded 75,000 burn-in iterations, and retained every 50th iteration. Saved latent-count draws were validated against county-year bounds, county-period constraints, state-year totals, national-year totals, and the grand total. Proposal acceptance fractions for some parameter blocks were outside the nominal 0.20–0.45 tuning target (approximately 0.082–0.085 for beta and 0.65–0.94 for log-scale hyperparameters); these are reported as efficiency limitations rather than convergence failures because all rank-normalized R-hat and bulk/tail ESS criteria passed.

### Convergence gate

The final Wahab HPC production run completed 8 independent constrained Bayesian chains and reported 36,000 saved draws per retained parameter. The original primary gate passed. Release-time diagnostics covered all 69 parameters: maximum rank-normalized split R-hat 1.008554, minimum bulk ESS 1437.2, and minimum 5%/95% tail ESS 3199.4.

### Sensitivity and contextual analyses

Sensitivity analyses included visible-only, fixed-value, residual-allocation, and interval-likelihood comparisons. COVID-19 co-mention and underlying-cause extracts were retained as contextual analyses rather than primary Bayesian outcomes.

## Supplementary Results

### Constraint validation

All 36,000 saved latent-count draws passed county-year, county-period, state-year, national-year, and grand-total validation checks. Supplementary Table S2 summarizes 489,696 validation records across eight chains.

### Diagnostics

All-parameter convergence diagnostics are reported in Supplementary Table S1. Per-chain parameter draws, chain configurations/statuses, compressed validation evidence, and derived posterior outputs are archived in the reproducibility release; large latent arrays are represented by their cryptographic hashes and complete validation summaries. Supplementary Figure S1 summarizes the final all-parameter verification.

### Sensitivity analyses

Supplementary Tables S3 and S4 provide scenario and sensitivity results. The scenario comparison clarifies which methods preserve the reconciled total, treat suppressed cells as latent positive counts, and provide posterior uncertainty.

### COVID co-mention context

COVID-19 co-mention analyses were contextual and interpreted using CDC death-certificate coding context [17]. The 2020–2022 lower-bound COVID co-mention total was 1,575 deaths. The broader 2020–2024 bounded urbanization-year context was 1,923–1,963 deaths. These are different summaries because they use different calendar windows and lower-bound versus bounded definitions.

### Underlying-cause context

Underlying-cause G40/G41 data were retained as contextual summaries because the staged public extracts did not support an equivalently constrained county-year primary Bayesian model.

## Supplementary Tables

Supplementary tables S1–S8 are included below or as accompanying CSV/XLSX files. The full county posterior summary is supplied as CSV/XLSX. Supplementary Table S5 is a data dictionary for the county posterior file rather than a printed county listing.

## Supplementary Figures

Supplementary Figures S1–S4 provide the convergence gate summary, posterior mortality-rate-ratio summary, posterior probability and uncertainty maps, and final latent-count constraint validation.
