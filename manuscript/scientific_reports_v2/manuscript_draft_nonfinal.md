<!--
SCIENTIFIC REPORTS V2 WORKING DRAFT

This file is intentionally nonfinal. Any token enclosed in double braces must be
populated only from a passed corrected eight-chain production gate or a completed
prespecified robustness analysis. Pilot estimates must not be copied here.
-->

# Suppression-aware Bayesian estimation of county mortality using public aggregate constraints: U.S. epilepsy, 2019–2024

**Running title:** Bayesian inference under mortality-data suppression

**Article type:** Article

**Authors and affiliations:** {{AUTHOR_BLOCK}}

## Abstract

Small-cell suppression protects confidentiality in public mortality data but complicates small-area inference when hidden counts are discarded or assigned arbitrary values. We developed a Bayesian framework that represents suppressed CDC WONDER county-year counts as bounded latent integers and constrains their joint configuration using compatible county-period and geographic aggregate information. We applied the framework to U.S. deaths mentioning epilepsy or status epilepticus (ICD-10 G40/G41) during 2019–2024, comprising 18,852 county-year observations from 3,142 counties. A negative-binomial model estimated rurality and social-vulnerability associations while accounting for population, county age and sex composition, year, and state-level heterogeneity. Exact finite-state tests established stationarity and detailed balance for the repaired constrained-count kernel, and the full constraint system contained 9,695 latent variables with 1,256 independent equalities. In corrected production inference, nonmetro nonadjacent counties had a mortality rate ratio of {{PRIMARY_IRR}} (95% credible interval, {{PRIMARY_CRI}}) relative to large metropolitan counties. {{ONE_SENTENCE_ROBUSTNESS_RESULT}} The framework propagates uncertainty without treating suppressed cells as zero or interpreting posterior latent quantities as recovered confidential counts, and may be transferable to other rare-outcome surveillance settings with analogous public suppression and aggregation structures.

**Keywords:** Bayesian hierarchical modeling; small-area estimation; data suppression; CDC WONDER; epilepsy mortality; rural health

## Introduction

County-level mortality surveillance can reveal geographic heterogeneity that is obscured by national or state summaries. Public mortality systems must also protect confidentiality. In CDC WONDER, positive county-year counts below the reporting threshold are suppressed, so an analyst knows that a hidden cell lies within a bounded positive range but does not observe its value. This is not ordinary missingness: the disclosure rule supplies interval information, while higher-level public tables may supply additional constraints on the joint configuration of hidden cells. Analyses that delete suppressed cells or assign every hidden value the same constant can therefore change both the effective study population and the estimated association between mortality and geographically patterned covariates.

Previous work has treated suppressed CDC WONDER counts as censored observations and used Bayesian data augmentation, including spatial hierarchical models, to propagate their uncertainty [11]. That literature establishes that Bayesian treatment of suppression is not itself new. The present contribution addresses a distinct information structure. Public mortality products can contain county-year bounds, longitudinal county-period information, state-year totals, and higher-level reconciliation totals that jointly restrict the feasible integer configurations. We developed a constrained latent-count approach that conditions on those public restrictions while estimating covariate-associated mortality rates. The objective is not to reconstruct protected values. It is to characterize epidemiologic associations and county-level uncertainty over the set of latent configurations compatible with the public releases and the statistical model.

Epilepsy and status epilepticus provide a stringent application. Mortality mentions are uncommon at the county-year level, suppression is frequent, and both rurality and social vulnerability are geographically structured. Prior studies have documented rising epilepsy-related mortality, demographic disparities, and disadvantages affecting rural populations [12–15]. A visible-only county analysis could nevertheless preferentially omit the smallest and most rural populations, while fixed substitution could impose an artificial rurality pattern through the chosen value itself.

We therefore evaluated a suppression-aware Bayesian framework for multiple-cause mortality mentions of ICD-10 G40 or G41 during 2019–2024. We hypothesized that suppression handling would materially influence estimated rural–urban associations. Before interpreting the epidemiologic model, we audited the algebraic constraint geometry, corrected and exactly validated the constrained-count transition kernel, tested deliberately dispersed feasible starts, and prespecified truth-known calibration, prior, temporal, model-family, and spatial sensitivity analyses.

## Results

### Public data structure and constraint geometry

The analytic frame contained 18,852 county-year observations from 3,142 counties. Of these cells, 1,350 contained exact positive counts, 7,807 were explicit zeros, and 9,695 were suppressed positive counts bounded from 1 through 9. The six-year county-period tables contributed 1,420 nominal equality constraints and 1,722 interval constraints. State-year tables contributed 306 nominal equalities. Six national-year totals and one grand total were retained as reconciliation checks.

The reduced equality system on the 9,695 latent variables contained 1,259 nonzero rows and rank 1,256, leaving an equality-nullity of 8,439 before cell bounds and county-period inequalities were applied. Three dependencies were intrinsic to the connected margin system. The six national-year equalities and grand-total equality were algebraically implied by lower-level margins and were therefore treated as validation checks rather than additional identifying information. These results distinguish deterministic information in the public releases from information supplied by the likelihood and priors.

### Exact validation of the constrained-count kernel

The legacy 2×2-only move family was not connected on an adversarial chordless six-cycle support: the two feasible configurations formed two strongly connected components. Adding a general alternating-cycle move produced one strongly connected component. For that finite state space, the repaired transition matrix had row-sum error below 5×10−16, detailed-balance error below 2×10−17, and stationarity error below 2×10−16. Its empirical state probabilities after simulation differed from the exact posterior probabilities by at most 0.0023. A second finite-state example requiring a cross-year interval path also passed exact transition-matrix, detailed-balance, stationarity, connectivity, and empirical-frequency checks. Randomly generated small feasible systems provided an additional automated exact-validation layer (Supplementary Methods).

### Truth-known calibration

The calibration study generated complete negative-binomial county-year counts under prespecified rurality, SVI, age-composition, sex-composition, state, year, and dispersion parameters; imposed the same 1–9 disclosure rule; reconstructed compatible county-period, state-year, national-year, and grand-total public constraints; and reran the complete constrained analysis from dispersed feasible starts. Twenty independently seeded replicates—five under each of four prespecified event-rate and overdispersion conditions—completed their computational gates without constraint-validation failures. Of 120 prespecified coefficient intervals, 114 contained the true IRR (95.0%; exact binomial 95% Monte Carlo interval, 89.4%–98.1%); contrast-specific coverage ranged from 90% to 100%. Across 4,337 suppressed cells, cell-weighted 95% interval coverage was 99.38% and posterior-mean RMSE was 1.01 deaths. These results authorize descriptive calibration reporting but do not establish that coverage has been estimated precisely or proven equal to the nominal 95% level.

### Corrected production diagnostics

Eight corrected production chains were initialized from independently seeded feasible allocations and run for 300,000 iterations per chain, with 75,000 iterations discarded and every 50th subsequent state retained. {{PRODUCTION_DIAGNOSTIC_SUMMARY}} Every retained latent state satisfied integrality, nonnegativity, county-year bounds, county-period restrictions, state-year equalities, national-year reconciliation, and the grand total. Representative stochastic latent summaries met the prespecified between-chain and effective-sample-size thresholds. Parameter-block and count-move acceptance rates are reported in Supplementary Table {{SUPPLEMENT_ACCEPTANCE_TABLE}}.

### Primary rurality and social-vulnerability associations

Relative to large metropolitan counties, the corrected posterior mortality rate ratios were {{RURALITY_RESULTS_SENTENCE}}. Social vulnerability showed {{SVI_RESULTS_SENTENCE}}. The primary nonmetro nonadjacent contrast was {{PRIMARY_IRR}} (95% credible interval, {{PRIMARY_CRI}}), with posterior probability {{PRIMARY_POSTERIOR_PROBABILITY_STATEMENT}}. Complete posterior summaries, rank-normalized split R-hat, bulk ESS, tail ESS, and Monte Carlo standard errors for all 69 monitored parameters are provided in Supplementary Table {{SUPPLEMENT_PARAMETER_TABLE}}.

### Consequences of alternative suppression handling

The primary constrained model was compared with visible-only analysis, fixed assignments of 1, 5, or 9 to every suppressed cell, and a population-favoring feasible allocation. {{SUPPRESSION_SENSITIVITY_RESULT}} These analyses are interpreted as demonstrations of handling dependence rather than competing reconstructions of the hidden counts.

### Model-derived county summaries and residual spatial dependence

County-period posterior mortality summaries are ecological model quantities, not observed or recovered suppressed counts. {{COUNTY_SUMMARY_RESULT}} Residual spatial dependence was evaluated using the U.S. Census Bureau county-adjacency file and a prespecified permutation Moran statistic applied to posterior-mean county-period residuals. {{SPATIAL_DIAGNOSTIC_RESULT}} If the prespecified residual-spatial threshold was met, a structured county spatial-effect sensitivity model was fitted and compared with the primary state-effect model: {{SPATIAL_MODEL_RESULT}}.

### Temporal and other prespecified robustness analyses

The primary rurality and SVI contrasts were re-estimated under broader and more regularizing prior profiles, an alternative count-model specification, exclusion of 2020–2021, and a rurality-by-pandemic-period interaction. {{ROBUSTNESS_RESULTS_PARAGRAPH}} Analyses using more granular age composition were performed if a reproducible public covariate source could be matched without changing the county universe; otherwise residual age-structure confounding was retained as an explicit limitation.

## Discussion

This study has two related contributions. Methodologically, it provides a constrained Bayesian framework that combines bounded suppressed counts with multiple levels of compatible public aggregate information. Substantively, the corrected model estimated {{DISCUSSION_PRIMARY_FINDING}} for deaths mentioning epilepsy or status epilepticus. The method retains the distinction between public observations and latent posterior quantities: exact and zero cells are observed, suppressed cells remain unknown within their public bounds, and county posterior summaries are model-derived ecological estimates.

The constraint analysis clarifies what the public data do and do not identify. Although the analysis records county-period, state-year, national-year, and grand-total relationships, higher-level totals that are algebraically implied by lower-level margins do not create new degrees of identification. After redundant and zero-information rows were removed, 8,439 equality-null directions remained before bounded inequalities were considered. Precision therefore arises from the combination of public restrictions, the negative-binomial likelihood, covariates, hierarchical structure, and priors—not from a claim that aggregate margins uniquely reveal individual protected cells.

Sampler validity required more than verifying that saved states obeyed the constraints. The original 2×2 move family could be trapped on structural-zero fibers. Exact enumeration exposed that failure, and the added alternating-cycle and interval-path moves restored connectivity in the adversarial finite examples while preserving detailed balance. The full-data chains were then required to show movement away from deliberately dispersed feasible starts, agreement in aggregate latent summaries, acceptable count-move and parameter acceptance, and convergence across every monitored parameter. These layers address different questions: feasibility checks detect illegal states, exact finite-state tests detect target or connectivity errors where enumeration is possible, and long-chain diagnostics evaluate practical exploration in the full system.

The suppression-handling comparisons show why disclosure control is not a clerical detail. {{DISCUSSION_SUPPRESSION_RESULT}} Visible-only analysis changes which county-years contribute outcome information, while fixed substitution imposes an unacknowledged point assumption on every hidden positive cell. The constrained model does not remove model dependence, but it makes the public information and remaining uncertainty explicit.

The applied result should be interpreted cautiously. Multiple-cause G40/G41 mentions are not equivalent to adjudicated epilepsy-attributable deaths. County covariates are ecological, residual age and comorbidity structure may remain, and death-certificate coding may vary geographically. State effects do not by themselves guarantee the absence of within-state spatial dependence; this motivated the residual-spatial diagnostic and prespecified spatial sensitivity. The period includes substantial pandemic disruption. County-equivalent geography and covariate imputation introduce additional uncertainty. None of the analyses estimates individual risk or a causal effect of rural residence.

Public suppression need not force analysts to choose between discarding small-area information and assigning arbitrary values to hidden counts. Where bounded cell information and compatible aggregate totals are available, constrained Bayesian models can propagate remaining uncertainty while preserving the distinction between released observations and model-derived latent quantities. In this application, {{FINAL_DISCUSSION_SENTENCߏ-�G����ƭy�65 years or older and percentage male were standardized before modeling. Population entered as a log offset [7]. Counties without direct covariate matches were retained to preserve public-total reconciliation and imputed according to the frozen processing rules documented in the repository.

### Public suppression and feasible latent state space

Let \(Y_{it}\) denote the G40/G41 multiple-cause death count for county \(i\) in year \(t\). For an exact public cell, \(Y_{it}=y_{it}^{obs}\). For an explicit zero, \(Y_{it}=0\). For a suppressed positive cell,

\[
Y_{it}\in\{1,2,\ldots,9\}.
\]

Let \(L_i^{(P)}\) and \(U_i^{(P)}\) denote the public lower and upper bounds for the six-year county-period count. Every latent state was required to satisfy

\[
L_i^{(P)}\le \sum_{t=2019}^{2024}Y_{it}\le U_i^{(P)},
\]

with equality when the county-period total was public and exact. For each state or District of Columbia unit \(s\) and year \(t\), the county counts satisfied

\[
\sum_{i:s(i)=s}Y_{it}=M_{st},
\]

where \(M_{st}\) is the corresponding public state-year total. National-year and grand-total relationships were checked on every retained state. Because these higher-level rows were algebraically implied by the reconciled state-year rows in this dataset, they were validation identities rather than additional independent identifying equations.

The equality matrix was constructed after substituting fixed exact and zero cells. Zero-information rows were removed, and numerical rank was evaluated on the remaining sparse system. We report latent-variable count, nominal constraint counts, nonzero reduced rows, independent rank, nullity, intrinsic margin dependencies, and higher-level redundant equalities. Cell bounds and nonexact county-period restrictions remain inequalities and are not included in the equality-nullity calculation.

### Negative-binomial mortality model

Conditional on a feasible latent count and model parameters,

\[
Y_{it}\mid \mu_{it},\kappa \sim \operatorname{NegBin}_2(\mu_{it},\kappa),
\]

with

\[
E(Y_{it})=\mu_{it},\qquad
\operatorname{Var}(Y_{it})=\mu_{it}+\frac{\mu_{it}^{2}}{\kappa}.
\]

The linear predictor was

\[
\log \mu_{it}
=
\log N_{it}
+\beta_0
+\boldsymbol{x}_{it}^{\mathsf T}\boldsymbol{\beta}
+u_{s(i)}
+\gamma_t,
\]

where \(N_{it}\) is population; \(oldsymbol{x}_{it}\) contains indicators for three nonreference rurality categories, indicators for SVI Q2–Q4, standardized percentage aged 65 years or older, and standardized percentage male; \(u_s\) is a state/DC effect; and \(\gamma_t\) is a year effect. State and year effects were projected to sum zero, separating them from the intercept.

### Priors

The intercept prior was

\[
\beta_0\sim N\left(\log\frac{58{,}380}{\sum_{it}N_{it}},\;5^2\right).
\]

Each nonintercept fixed effect had

\[
\beta_j\sim N(0,1.5^2).
\]

On their identified sum-to-zero subspaces,

\[
\boldsymbol{u}\mid\sigma_{state}\sim N_{\sum u=0}(\boldsymbol{0},\sigma_{state}^2I),
\qquad
\boldsymbol{\gamma}\mid\sigma_{year}\sim N_{\sum\gamma=0}(\boldsymbol{0},\sigma_{year}^2I),
\]

with

\[
\sigma_{state}\sim\operatorname{HalfNormal}(1),
\qquad
\sigma_{year}\sim\operatorname{HalfNormal}(1).
\]

The normalizing powers use dimensions \(S-1\) and \(T-1\), respectively, because the effects live on constrained subspaces. Finally,

\[
\log\kappa\sim N(\log 10,1.5^2).
\]

Two prespecified prior sensitivities used a broader profile (nonintercept fixed-effect standard deviation 3.0; hierarchical-scale half-normal standard deviation 2.0; log-dispersion standard deviation 2.5) and a more regularizing profile (0.75, 0.5, and 0.75, respectively). The intercept standard deviations were 10.0 and 2.5 in the broader and regularizing profiles.

### Feasible initialization and constrained-count proposals

Four or eight deliberately dispersed initial allocations, depending on the analysis stage, were generated by mixed-integer linear programming under the complete set of cell bounds and aggregate restrictions. Randomized objectives produced distinct feasible starts. Pairwise L1 distances and numbers of differing free cells were recorded before sampling.

Given parameters, latent counts were updated with Metropolis–Hastings proposals that preserve or explicitly check the public constraints. The move family comprised state-year transfers, county-period interval exploration, cross-year interval-path transfers, 2×2 swaps, general alternating-cycle swaps up to a prespecified length, and periodic blocked refreshes. Proposal-specific forward and reverse probabilities were included where the selection mechanism was asymmetric. A proposed latent state was accepted with probability

\[
\min\left\{1,
\frac{p(\boldsymbol{Y}'\mid\boldsymbol{\theta})q(\boldsymbol{Y}\mid\boldsymbol{Y}')}
{p(\boldsymbol{Y}\mid\boldsymbol{\theta})q(\boldsymbol{Y}'\mid\boldsymbol{Y})}
\right\},
\]

and was rejected if any bound, integrality, period, or geographic-total restriction failed. Because local count moves mutate the latent vector, the joint log posterior was recomputed before parameter proposals were evaluated.

### Parameter updates and computation

Fixed effects, state effects, year effects, \(\log\sigma_{state}\), \(\log\sigma_{year}\), and \(\log\kappa\) were updated in random-walk Metropolis blocks. State and year vectors were reprojected to sum zero after proposal. Proposal scales and count-move weights were frozen from preproduction tuning before corrected production began. Checkpoints stored the complete latent state, parameter state, random-number-generator state, iteration, acceptance counters, and target value, permitting exact continuation after a scheduler signal or time limit.

The corrected primary analysis used eight chains, prespecified chain seeds 58291–58298, and independently generated initialization seeds 57291–57298. Each chain targeted 300,000 iterations, discarded 75,000 iterations, and retained every 50th subsequent state. No corrected result was released unless all chains completed and the fail-closed production gate passed.

### Exact kernel validation

For small systems where every feasible integer configuration could be enumerated, the code constructed the full transition matrix and exact normalized target distribution. Validation required row sums equal to one, stationarity of the target distribution, detailed balance, and a single strongly connected component for the repaired kernel. Long empirical simulations were compared with exact state probabilities. Randomly generated finite fibers supplemented two adversarial systems designed to expose disconnected 2×2 support and cross-year interval-path requirements.

### Convergence and latent-space exploration

Rank-normalized split R-hat, bulk ESS, tail ESS, and Monte Carlo standard errors were calculated for all 69 monitored parameters. The production gate required R-hat no greater than 1.01 and bulk and tail ESS of at least 400 for every parameter; primary fixed effects additionally required bulk and tail ESS of at least 1,000. Stochastic latent summaries included rurality totals, SVI totals, and representative county-period quantities selected before production. These summaries required R-hat no greater than 1.01 and bulk and tail ESS of at least 400. Deterministic summaries implied by hard totals were identified rather than assigned misleading convergence statistics. Every retained latent draw underwent independent constraint validation.

### Truth-known calibration

Synthetic calibration panels were selected deterministically from the real model frame to preserve rurality, population, SVI, state, and year variation while keeping computation tractable. Complete NB2 counts were generated under known parameters, the public 1–9 suppression rule was applied, and compatible longitudinal and geographic aggregates were constructed. The complete pipeline was then fit without access to the hidden truth. Prespecified outputs were coefficient bias, RMSE and 95% interval coverage; suppressed-cell posterior-mean RMSE and interval coverage; suppression fraction; convergence pass rate; and comparisons with visible-only, fixed-substitution, and feasible-allocation alternatives. Multi-replicate coverage was reported with exact binomial uncertainty.

### Prespecified robustness analyses

The robustness registry was frozen before corrected production results. It includes broader and regularizing priors; a Poisson or practically Poisson count-family sensitivity; exclusion of 2020–2021; rurality-by-pandemic-period interaction; more granular age-composition adjustment if a reproducible source can be matched; residual spatial autocorrelation; and a structured spatial random-effect model triggered by the prespecified diagnostic or reviewer request. All prespecified analyses are reported regardless of direction.

### Residual spatial diagnostic

County-period posterior-mean counts were compared with posterior-mean conditional expected counts. Raw and Pearson residuals were linked using the 2024 U.S. Census Bureau county-adjacency file [17]. Global Moran's I used row-standardized weights and 9,999 deterministic permutations; within-state statistics used 999 permutations where at least ten connected counties were available. A positive global statistic of at least 0.02 with two-sided permutation \(P\le0.05\), or analogous signals in at least three states, triggered the structured spatial sensitivity model. The test is a residual diagnostic, not evidence of a causal spatial process.

### Ethics, data availability, code availability, and generative AI

This study used public, deidentified aggregate data and no individual-level or restricted CDC data. The manuscript will report the exact institutional determination applicable to secondary analysis of public aggregate data: {{ETHICS_DETERMINATION}}.

**Data availability.** All analyses used publicly available aggregate data. CDC WONDER extracts, county covariate sources, machine-readable query metadata, processed inputs permitted for redistribution, and derived reproducibility outputs are documented in the frozen repository release {{REPOSITORY_DOI_AND_VERSION}}. Posterior county quantities are model-derived summaries and should not be interpreted as observed or recovered suppressed counts.

**Code availability.** The complete processing workflow, constraint-construction code, constrained Bayesian sampler, exact finite-state tests, calibration study, sensitivity scripts, and figure/table generation code are archived in {{REPOSITORY_DOI_AND_VERSION}} with environment specifications and reproducible execution instructions.

**Use of generative artificial intelligence.** Generative AI tools were used under author supervision for code development and debugging, language editing, and reproducibility-package assembly. All generated code, transformations, analyses, citations, and manuscript text were reviewed and validated by the authors. The authors retain full responsibility for the integrity, interpretation, and reproducibility of the work.

## References

1. CDC WONDER Multiple Cause of Death, 2018–2024, Single Race database. https://wonder.cdc.gov/mcd-icd10-expanded.html. Accessed 19 June 2026.
2. Centers for Disease Control and Prevention. Multiple Cause of Death 2018–2024 by Single Race: CDC WONDER help documentation. https://wonder.cdc.gov/wonder/help/mcd-expanded.html. Accessed 19 June 2026.
3. CDC WONDER Underlying Cause of Death, 2018–2024, Single Race database. https://wonder.cdc.gov/ucd-icd10-expanded.html. Accessed 19 June 2026.
4. Centers for Disease Control and Prevention/Agency for Toxic Substances and Disease Registry. CDC/ATSDR Social Vulnerability Index data and documentation. https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html. Accessed 19 June 2026.
5. U.S. Department of Agriculture Economic Research Service. Rural–Urban Continuum Codes documentation. https://www.ers.usda.gov/data-products/rural-urban-continuum-codes/documentation. Accessed 19 June 2026.
6. National Center for Health Statistics. Urban–Rural Classification Scheme for Counties. https://www.cdc.gov/nchs/data-analysis-tools/urban-rural.html. Accessed 19 June 2026.
7. U.S. Census Bureau. American Community Survey 5-Year Data documentation. https://www.census.gov/data/developers/data-sets/acs-5year.html. Accessed 19 June 2026.
8. Vandenbroucke, J. P. et al. Strengthening the Reporting of Observational Studies in Epidemiology (STROBE): explanation and elaboration. PLoS Med. 4, e297 (2007). doi:10.1371/journal.pmed.0040297.
9. STROBE Statement. STROBE checklists for observational studies. https://www.strobe-statement.org/checklists/. Accessed 19 June 2026.
10. Pierpoint, G. Suppression-Aware Bayesian Analysis of County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024. Zenodo, version {{REPOSITORY_VERSION}}, {{REPOSITORY_DOI}}.
11. Quick, H. Estimating county-level mortality rates using highly censored data from CDC WONDER. Prev. Chronic Dis. 16, E76 (2019). doi:10.5888/pcd16.180441.
12. DeGiorgio, C. M. et al. Why are epilepsy mortality rates rising in the United States? A population-based multiple cause-of-death study. BMJ Open 10, e035767 (2020). doi:10.1136/bmjopen-2019-035767.
13. Tian, N. et al. Mortality and mortality disparities among people with epilepsy in the United States, 2011–2021. Epilepsy Behav. 155, 109770 (2024). doi:10.1016/j.yebeh.2024.109770.
14. Duke, S. M. et al. A systematic literature review of health disparities among rural people with epilepsy (RPWE) in the United States and Canada. Epilepsy Behav. 122, 108181 (2021). doi:10.1016/j.yebeh.2021.108181.
15. Iqbal, J. et al. Demographic and regional patterns of epilepsy-related mortality in the USA: insights from CDC WONDER data. Surg. Neurol. Int. 15, 450 (2024). doi:10.25259/SNI_592_2024.
16. Centers for Disease Control and Prevention. Reporting and coding deaths due to COVID-19. https://www.cdc.gov/nchs/covid19/coding-and-reporting.htm. Accessed 19 June 2026.
17. U.S. Census Bureau. 2024 County Adjacency File. https://www2.census.gov/geo/docs/reference/county_adjacency/county_adjacency2024.txt. Accessed {{ADJACENCY_ACCESS_DATE}}.

## Locked placeholders

The following placeholders must remain unresolved until their stated gate passes:

- `{{PRIMARY_IRR}}`, `{{PRIMARY_CRI}}`, all primary and SVI result fields: corrected eight-chain production gate.
- `{{SPATIAL_DIAGNOSTIC_RESULT}}`: post-production spatial residual diagnostic.
- `{{SPATIAL_MODEL_RESULT}}`: prespecified spatial sensitivity, if triggered.
- `{{ROBUSTNESS_RESULTS_PARAGRAPH}}`: completed prior, temporal, model-family, and age-structure sensitivities.
- `{{REPOSITORY_DOI_AND_VERSION}}`: immutable release created from the final manuscript result freeze.
