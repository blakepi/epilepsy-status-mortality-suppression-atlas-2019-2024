# Suppression-Aware Bayesian Analysis of County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024

## Abstract

**Objective:** To estimate rurality-associated multiple-cause mortality mentions of epilepsy or status epilepticus in the United States while respecting CDC WONDER small-cell suppression and public aggregate constraints.

**Methods:** We analyzed public CDC WONDER multiple-cause mortality data for ICD-10 G40/G41 mentions from 2019–2024. The final model frame included 18,852 county-year rows from 3,142 counties. County-year exact counts, explicit zeros, suppressed 1–9 intervals, county-period constraints, state-year totals, national-year totals, and the known national total of 58,380 deaths defined a constrained latent-count system. A negative-binomial Bayesian mortality model estimated mortality rate ratios for rurality and SVI while adjusting for county age and sex composition, population offset, year effects, and state-level structure.

**Results:** The final Wahab HPC production run completed 8 independent constrained Bayesian chains. The primary nonmetro nonadjacent versus large metropolitan mortality rate ratio was 1.23 (95% credible interval [CrI], 1.17–1.30); the posterior probability that the mortality rate ratio exceeded 1 was 1.00. All 69 retained parameters passed rank-normalized split R-hat (maximum, 1.0086), bulk effective sample size (ESS; minimum, 1437.2), and 5%/95% tail ESS (minimum, 3199.4) criteria. All 36,000 saved latent-count draws passed county-year, county-period, state-year, national-year, and grand-total constraint validation.

**Conclusions:** A constrained Bayesian latent-count model provides model-based evidence of higher epilepsy/status epilepticus mortality mention rates in nonmetro nonadjacent counties while preserving the public WONDER suppression structure. Posterior county summaries are model-derived ecological estimates, not recovered suppressed counts or person-level risks.

## Introduction

County-level mortality analyses can inform geographic health surveillance, but CDC WONDER small-cell suppression complicates rare-outcome modeling. Epilepsy and status epilepticus mortality mentions are particularly affected because many county-year cells are small. Visible-only analyses may understate mortality in sparsely populated counties, whereas arbitrary fixed assignments to suppressed cells can distort rurality-associated estimates.

Prior CDC WONDER and epilepsy mortality studies have described rising mortality and geographic disparities, but public county-level suppression limits direct small-area inference [1–3,12–16]. Rurality, social vulnerability, age structure, and sex composition are also geographically patterned, making suppression-aware adjustment essential [4–7]. This study uses public aggregate constraints to model latent county-year mortality counts without using restricted microdata.

The scenario framework remains useful for transparency and sensitivity analysis. The primary inferential layer in this submission is a constrained Bayesian latent-count model that conditions on exact cells, suppressed intervals, county-period constraints, state-year totals, national-year totals, and the reconciled national total.

## Methods

### Data sources and outcome

The outcome was any mention of ICD-10 G40 epilepsy or G41 status epilepticus on the death certificate in CDC WONDER multiple-cause mortality data, 2019–2024 [1,2]. This is interpreted as epilepsy/status epilepticus-related mortality mention, not definitive etiologic attribution. Underlying-cause G40/G41 extracts were retained as contextual analyses [3].

### Rurality, SVI, and covariates

County rurality was collapsed from Rural-Urban Continuum Codes as large metropolitan (RUCC 1), other metropolitan (RUCC 2–3), nonmetropolitan adjacent (RUCC 4, 6, and 8), and nonmetropolitan nonadjacent (RUCC 5, 7, and 9), with large metropolitan counties as the reference category. Social Vulnerability Index (SVI) quartile was included with Q1 as the reference category [4]. County percentage aged ≥65 years, county percentage male, and population offsets were assembled from public county covariates and standardized for modeling [5–7]. Eleven counties without matched covariates were retained and imputed with state medians or modes when available and national values otherwise. Twenty-four Connecticut county-year population offsets missing from the county-year extract were imputed as county-period person-years divided by six; both imputation types were flagged in the model frame.

### Suppression-aware constraint system

Suppressed county-year cells were treated as known-positive integer intervals from 1 to 9, not as zeros. Exact county-year counts and explicit zero cells were fixed. County-period rows imposed exact, zero, or 1–9 interval constraints on six-year county sums. State-year and national-year aggregate totals were enforced exactly, and the 2019–2024 national total was fixed at 58,380 deaths. Counties without direct covariate matches were retained in the latent-count system so aggregate reconciliation was not broken.

### Bayesian constrained model

Latent county-year counts were modeled with a negative-binomial-2 mean linked to the log population offset, rurality, SVI quartile, standardized percentage aged ≥65 years, standardized percentage male, six centered year effects, and 51 centered state/DC effects. The intercept had a normal prior centered on the crude national log rate with standard deviation 5; nonintercept fixed effects had independent normal(0, 1.5) priors. State and year effects had zero-centered normal priors with separate half-normal(0, 1) scale priors, and the negative-binomial shape parameter had a log-normal prior with log mean log(10) and standard deviation 1.5. Posterior county-level summaries are constrained model-derived quantities, not observed or recovered suppressed counts.

### Computation, convergence, and validation

The custom Metropolis-within-Gibbs sampler began from independently seeded feasible allocations generated by mixed-integer linear programming. Constraint-preserving transfer, interval-exploration, swap, and blocked-refresh moves updated latent counts; random-walk Metropolis proposals updated parameter blocks. Eight production chains used seeds 18291–18298 and each ran 300,000 iterations, discarded 75,000 burn-in iterations, and retained every 50th iteration, yielding 4,500 draws per chain and 36,000 draws per parameter. The original primary convergence gate passed. A release-time verification then evaluated all 69 retained parameters using rank-normalized split R-hat, bulk ESS, 5%/95% tail ESS, and Monte Carlo standard errors. All parameters met R-hat ≤1.01 and bulk/tail ESS ≥400; the maximum R-hat was 1.008554, minimum bulk ESS was 1437.2, and minimum tail ESS was 3199.4. Supplementary Table S1 reports all parameter diagnostics. Per-chain parameter draws, chain metadata, compressed validation evidence, and derived posterior outputs are included in the reproducibility release. All 36,000 saved latent-count draws passed county-year, county-period, state-year, national-year, and grand-total constraint validation.

### Sensitivity and contextual analyses

Visible-only, fixed-value, residual-allocation, and interval-likelihood analyses were retained as sensitivity comparisons. COVID-19 co-mention analyses and underlying-cause analyses were retained as contextual summaries rather than components of the primary Bayesian outcome. Reporting follows observational-study transparency principles, including STROBE guidance [8,9], and a completed STROBE checklist is included in the submission package.

## Results

### Public data structure and constraints

The model frame contained 18,852 county-year rows from 3,142 counties. The county-year extract included 1,350 exact cells, 9,695 suppressed 1–9 cells, and 7,807 explicit zero cells (Table 1; Figure 1). Constraint validation confirmed that saved latent-count draws preserved county-year bounds, county-period constraints, state-year totals, national-year totals, and the 58,380-death grand total.

### Final Bayesian rurality and SVI associations

The final primary nonmetro nonadjacent versus large metropolitan mortality rate ratio was 1.23 (95% CrI, 1.17–1.30), with posterior probability that the mortality rate ratio exceeded 1 of 1.00 (Table 2; Figure 2). Nonmetro adjacent counties also had elevated posterior mortality (1.27, 95% CrI 1.22–1.33). SVI showed a graded association, with SVI Q4 versus Q1 mortality rate ratio 1.43 (95% CrI 1.37–1.50).

### Model-based mortality rates by rurality

Model-derived posterior mortality rates were higher in nonmetro categories than in large metropolitan counties under both conditional and standardized summaries (Table 3). These rates are posterior summaries per 100,000 person-years and should be interpreted as ecological model estimates.

### Comparison with alternative suppression handling

Alternative suppression approaches produced a wide range of estimates (Table 4; Figure 3). Visible-only models and fixed-value stress tests were sensitive to how suppressed positive cells were handled. The final Bayesian constrained model moved beyond fixed assignments by jointly conditioning on county-year intervals, county-period constraints, and public aggregate totals.

### Posterior county atlas and uncertainty

The posterior atlas maps county-period mortality rates and uncertainty (Figure 4). The maps identify spatial heterogeneity in model-derived mortality mention rates while preserving the distinction between posterior estimates and observed public counts.

### Temporal and contextual analyses

National multiple-cause G40/G41 deaths totaled 58,380 during 2019–2024 and increased from 7,583 in 2019 to 10,796 in 2024. COVID-19 co-mention analyses were retained as contextual sensitivity summaries rather than part of the primary Bayesian outcome and were interpreted using CDC death-certificate coding context [17]. Underlying-cause G40/G41 extracts were also retained as context because equivalent public county-year constraints were not available for a parallel primary model.

## Discussion

The principal finding is model-based evidence of higher epilepsy/status epilepticus mortality mention rates in nonmetro nonadjacent counties compared with large metropolitan counties after adjustment for SVI, age structure, sex composition, population offset, year effects, and state-level structure. The posterior estimate was precise in the final constrained Bayesian model, passed the original primary gate, and met the release-time all-parameter convergence criteria.

Suppression handling matters because public county-level mortality data contain many known-positive but hidden small cells. Treating these cells as zero or assigning a single arbitrary value changes the denominator-adjusted rurality pattern and can make sensitivity results look more certain than the public data support.

The Bayesian constrained model adds information by conditioning on public aggregate totals and interval constraints simultaneously. This provides stronger mortality inference than fixed allocation stress tests while retaining the public-data privacy structure. The tradeoff is greater model dependence, so posterior county summaries should be treated as uncertainty-aware ecological estimates rather than recovered suppressed counts.

Limitations include ecological design, death-certificate mention-based outcome definition, possible coding variation, residual confounding by age and comorbidity structure, model dependence, county-equivalent geography issues, and COVID-era disruption. These analyses do not estimate person-level risk or causal effects.

Public aggregate constraints plus constrained Bayesian modeling can extract more information from public CDC WONDER outputs without restricted microdata. The results support rurality-focused mortality surveillance while preserving careful language around suppression, uncertainty, and ecological inference.

## Data and Code Availability

All analyses use public aggregate CDC WONDER outputs and public county covariates. No person-level or restricted data were used. The archived repository release and DOI are cited in the reference list [11]. Posterior county summaries are constrained model-derived estimates and are not observed or recovered suppressed counts.

## Ethics

This study used public deidentified aggregate data and did not involve human-subjects interaction or identifiable private information.

## Generative AI Declaration

Generative AI assistance was used for coding, manuscript editing, and reproducibility package assembly under human direction and in accordance with journal policy expectations [10]. Scientific interpretation, data provenance, and final responsibility remain with the authors.

## References

1. CDC WONDER Multiple Cause of Death, 2018–2024, Single Race database. https://wonder.cdc.gov/mcd-icd10-expanded.html. Accessed June 19, 2026.
2. Centers for Disease Control and Prevention. Multiple Cause of Death 2018–2024 by Single Race: CDC WONDER help documentation. https://wonder.cdc.gov/wonder/help/mcd-expanded.html. Accessed June 19, 2026.
3. CDC WONDER Underlying Cause of Death, 2018–2024, Single Race database. https://wonder.cdc.gov/ucd-icd10-expanded.html. Accessed June 19, 2026.
4. Centers for Disease Control and Prevention/Agency for Toxic Substances and Disease Registry. CDC/ATSDR Social Vulnerability Index data and documentation. https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html. Accessed June 19, 2026.
5. U.S. Department of Agriculture Economic Research Service. Rural-Urban Continuum Codes documentation. https://www.ers.usda.gov/data-products/rural-urban-continuum-codes/documentation. Accessed June 19, 2026.
6. National Center for Health Statistics. Urban-Rural Classification Scheme for Counties. https://www.cdc.gov/nchs/data-analysis-tools/urban-rural.html. Accessed June 19, 2026.
7. U.S. Census Bureau. American Community Survey 5-Year Data documentation. https://www.census.gov/data/developers/data-sets/acs-5year.html. Accessed June 19, 2026.
8. Vandenbroucke JP, von Elm E, Altman DG, et al. Strengthening the Reporting of Observational Studies in Epidemiology: explanation and elaboration. PLoS Med. 2007;4:e297.
9. STROBE Statement. STROBE checklists for observational studies. https://www.strobe-statement.org/checklists/. Accessed June 19, 2026.
10. Elsevier. Generative AI policies for journals. https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals. Accessed June 19, 2026.
11. Pierpoint G. Suppression-Aware Bayesian Analysis of County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024. Version v1.1.0. Zenodo. https://doi.org/10.5281/zenodo.20691622. Accessed July 15, 2026.
12. Quick H. Estimating County-Level Mortality Rates Using Highly Censored Data From CDC WONDER. Prev Chronic Dis. 2019;16:180441. doi:10.5888/pcd16.180441.
13. DeGiorgio CM, Curtis A, Carapetian A, Hovsepian D, Krishnadasan A, Markovic D. Why are epilepsy mortality rates rising in the United States? A population-based multiple cause-of-death study. BMJ Open. 2020;10:e035767. doi:10.1136/bmjopen-2019-035767.
14. Tian N, Kobau R, Friedman D, Liu Y, Eke PI, Greenlund KJ. Mortality and mortality disparities among people with epilepsy in the United States, 2011–2021. Epilepsy Behav. 2024;155:109770. doi:10.1016/j.yebeh.2024.109770.
15. Duke SM, González Otárula KA, Canales T, Lu E, Stout A, Ghearing GR, Sajatovic M. A systematic literature review of health disparities among rural people with epilepsy in the United States and Canada. Epilepsy Behav. 2021;122:108181. doi:10.1016/j.yebeh.2021.108181.
16. Iqbal J, Shafique MA, Rangwala BS, et al. Demographic and regional patterns of epilepsy-related mortality in the USA: insights from CDC WONDER data. Surg Neurol Int. 2024;15:450. doi:10.25259/SNI_592_2024.
17. Centers for Disease Control and Prevention. Reporting and Coding Deaths Due to COVID-19. https://www.cdc.gov/nchs/covid19/coding-and-reporting.htm. Accessed June 19, 2026.
