# Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024

## Abstract

## Objective

To quantify how CDC WONDER county-level small-cell suppression shapes national county-level analyses of epilepsy/status epilepticus-related mortality and to evaluate rurality-associated patterns using suppression-aware methods.

## Methods

We analyzed CDC WONDER Multiple Cause of Death data for 2019-2024. The primary outcome was multiple-cause mortality with ICD-10 G40 (epilepsy) or G41 (status epilepticus) listed anywhere on the death certificate. County-period and county-year extracts were linked to county rurality and social vulnerability covariates. Suppressed county cells were preserved as 1-9 death intervals and were not treated as zero. We compared observed-only models with fixed-value stress tests, total-preserving residual allocations, and interval-likelihood negative binomial models.

## Results

National multiple-cause G40/G41 mortality totaled 58,380 deaths. The county-period extract comprised 1,085 counties with exact counts (51,388 deaths), 1,722 suppressed county rows (1-9 deaths each), and 335 explicit-zero rows. The reconciled residual within suppressed counties was 6,992 deaths, or ≈4.1 deaths per suppressed county. In the rurality plus SVI model, nonmetro nonadjacent IRRs were 0.97 for observed exact-positive counties and 0.91 after adding explicit zero counties. Total-preserving residual-allocation scenarios gave IRRs from 0.97 to 1.13, and the interval-likelihood model estimated 1.07 with wide approximate uncertainty. Constant-count and high fixed-value stress tests gave larger estimates, but these were interpreted as distributional or non-total-preserving stress tests rather than primary estimates. COVID-19 co-mention totaled 1,936 deaths, and underlying-cause G40/G41 mortality totaled 22,306 deaths.

## Conclusion

County-level epilepsy/status epilepticus mortality inference in CDC WONDER is strongly shaped by outcome-dependent suppression. Preserving suppressed cells as intervals, reconciling county extracts to aggregate totals, and separating total-preserving allocations from fixed-value stress tests provide a more transparent framework for county-level mortality surveillance.

## Keywords

Epilepsy; status epilepticus; mortality; CDC WONDER; small-cell suppression; rural health; ecological study.

## Introduction

Epilepsy and status epilepticus contribute to mortality burden in the United States and may appear on death certificates as underlying or contributing conditions. Multiple-cause mortality data are therefore useful for surveillance because they capture deaths in which epilepsy or status epilepticus was mentioned anywhere on the death certificate, rather than only deaths for which these diagnoses were selected as the underlying cause.

Rurality, social vulnerability, and health-system context are plausible contributors to geographic variation in epilepsy-related mortality. Rural communities may differ from metropolitan areas in specialist availability, emergency medical services, travel time, comorbidity burden, medication access, and death-certificate certification context. These factors are best interpreted as contextual hypotheses in aggregate mortality data, not as demonstrated mechanisms in county-level ecological analyses.

National county-level mortality analyses are difficult for epilepsy/status epilepticus because CDC WONDER suppresses small death counts. Suppressed county cells generally represent 1-9 deaths. This creates outcome-dependent data visibility: counties with exact counts are partly selected by population size and mortality burden, while many rural and low-population counties are represented only by bounded intervals or explicit zero counts. Exact-count counties are therefore not a random subset of all counties.

Prior work has addressed closely related censoring problems in CDC WONDER. Quick modeled county-level mortality rates from highly censored WONDER data using a hierarchical Bayesian framework that borrows strength across counties to produce smoothed estimates. The present study is complementary rather than duplicative: it emphasizes transparent reconciliation to known aggregate totals, bias-bounding, and interval representation instead of attempting to recover a single best county count for every suppressed cell. The trade-off is deliberate. Hierarchical smoothing can improve precision when the model is accepted, whereas the present workflow foregrounds assumption visibility and sensitivity for readers who need to understand how much the conclusion depends on hidden cells.

This study uses a suppression-aware extraction and modeling framework to map county-level epilepsy/status epilepticus mortality, quantify suppression patterns, bound rurality-associated estimates, and provide temporal, COVID co-mention, and underlying-cause context. The major contribution is not a strong rurality claim; it is a national suppression-aware atlas and a methodological caution for county-level WONDER mortality research.

The aims were:

1. Describe county-level exact, suppressed, and zero mortality-count patterns for epilepsy/status epilepticus-related mortality.
2. Estimate rurality-associated mortality patterns under observed-only, fixed-value stress-test, residual-allocation, and interval-likelihood approaches.
3. Characterize temporal, urbanization, COVID co-mention, and underlying-cause sensitivity patterns.
4. Produce a suppression-aware geographic atlas to guide interpretation of county-level epilepsy mortality surveillance.

## Methods

### Study Design And Data Sources

We conducted a national ecological county-level mortality analysis using public aggregate mortality and county covariate data. Mortality data came from CDC WONDER Current Final Multiple Cause of Death Data, 2018-2024, Single Race. The analytic years were 2019-2024. County covariates included CDC/ATSDR Social Vulnerability Index 2022, U.S. Department of Agriculture Rural-Urban Continuum Codes 2023, National Center for Health Statistics 2023 urban-rural classification, and American Community Survey 2019-2023 county variables.

### Case Definition

The primary outcome was multiple-cause mortality with ICD-10 G40 or G41 listed anywhere on the death certificate. The confirmed CDC WONDER cause syntax was G40 (Epilepsy) and G41 (Status epilepticus). The secondary sensitivity outcome was underlying-cause mortality with ICD-10 G40 or G41. COVID-19 co-mention analyses used U07.1 (COVID-19) in the second multiple-cause box. Multiple-cause mortality is interpreted as epilepsy/status epilepticus-related mortality mention, not as definitive attribution of death to epilepsy or status epilepticus.

### CDC WONDER Extraction And Validation

The analysis used the validated Q001-Q015 extraction set from the CDC WONDER extraction project. Q001 provided county-period multiple-cause G40/G41 mortality for 2019-2024 with zero and suppressed values requested. Q002 provided county-year multiple-cause G40/G41 mortality. Q003, Q004, and Q005 provided national-year, state-year, and urbanization-year multiple-cause totals. Q010 provided urbanization-year multiple-cause G40/G41 and U07.1 COVID-19 co-mention. Q011, Q012, and Q014 provided underlying-cause sensitivity outputs.

The extraction validation confirmed that Q001, Q003, Q004, and Q005 reconciled to 58,380 multiple-cause G40/G41 deaths for 2019-2024. Q002 county-year exact-plus-suppressed intervals contained Q003 national-year totals. Q010 was bounded by Q005 by urbanization and year. Q012 and Q014 underlying-cause aggregate totals agreed at 22,306 deaths.

### Suppression Status Definitions

County death counts were coded as exact, suppressed_1_9, zero, missing/unreturned, aggregate total, or invalid noncounty. Exact cells were coded as [death, death]. Suppressed cells were coded as [1, 9] with midpoint 5 for descriptive summaries. Explicit zero cells were coded as [0, 0]. Suppressed cells were not treated as zero. Missing or unreturned cells were not treated as zero. Aggregate total rows were retained for reconciliation but excluded from county models.

### County Covariates And Rurality Measures

County FIPS codes were preserved as 5-character strings. The county merge included 3,142 WONDER Q001 county rows and 3,144 combined covariate county rows. The FIPS merge matched 3,131 counties, leaving 11 WONDER counties without covariates and 13 covariate counties without WONDER Q001 rows. Alaska, Hawaii, and the District of Columbia were retained in analytic county files where present; territories were not present in the Q001 analytic county set.

The primary collapsed RUCC rurality variable used metro_large (RUCC 1), metro_other (RUCC 2-3), nonmetro_adjacent (RUCC 4, 6, 8), and nonmetro_nonadjacent (RUCC 5, 7, 9). Sensitivity rurality definitions included binary RUCC 1-3 versus 4-9 and NCHS six-level urban-rural classification.

### Social Vulnerability Covariates

SVI was modeled as a composite family using SVI quartile. ACS component models were modeled separately using poverty, household income, education, uninsurance, race/ethnicity composition, and age structure. SVI was not modeled together with its own component variables in the primary model family. Component-model variance inflation factors were modest, with a maximum of 2.92 for median household income and poverty-related component diagnostics (Table S4).

### Bias-Bounding Analyses

County-period models used a count-model framework with log person-years as the offset. Scenarios were tiered as visible-only analyses, fixed-value stress tests, total-preserving residual allocations, and interval-likelihood models. Visible-only analyses either retained exact positive counties only or added explicit zero counties. Fixed-value stress tests assigned suppressed cells to a constant value; these include suppressed=1, suppressed=5, suppressed=9, and a constant mean assignment of 4.06 deaths per suppressed row. The constant mean preserves the reconciled total but remains a distributional stress test because it gives the same hidden count to low- and high-exposure suppressed counties. Suppressed=5 and suppressed=9 exceed the known reconciled total and are therefore interpreted only as extreme stress tests, not plausible imputations.

The residual allocation used the difference between the Q001 total row and the exact county death sum. This residual was 6,992 deaths across 1,722 suppressed counties. Population-scaled, conservative anti-rural, and pro-rural residual allocations were constrained to the 1-9 death range with an iterative water-filling allocator. After clipping, all three residual allocation scenarios still summed exactly to 58,380 deaths.

Bias-bounding generalized linear models used a negative-binomial mean model with alpha fixed at 1 and robust sandwich standard errors as a stable common working variance specification across scenarios. Pearson ratios from the fitted models and the interval model's smaller dispersion estimate indicate that alpha=1 is conservative as a variance assumption. The primary interpretation therefore rests on scenario-specific IRRs and bounds rather than on unadjusted p-values.

### Interval-Likelihood Negative Binomial Model

An interval-likelihood negative binomial model was attempted after bias-bounding analyses. Exact rows contributed P(Y = y), zero rows contributed P(Y = 0), and suppressed rows contributed P(1 <= Y <= 9), treated independently across counties. This specification does not impose the known suppressed-cell total of 6,992 deaths; the residual-allocation analyses use that marginal information directly. Approximate standard errors used optimizer inverse-Hessian estimates, so bias-bounding analyses remained the primary suppression-aware results when interval uncertainty was unstable.

### Multiplicity

The scenario models were designed for sensitivity analysis and bounding, not for selecting statistically significant terms from many comparisons. P-values are reported descriptively, are not adjusted for multiple comparisons, and are not the basis for the main inference.

### Temporal, COVID Co-Mention, And Underlying-Cause Analyses

Temporal analyses used Q003 national-year, Q004 state-year, Q005 urbanization-year, Q010 COVID co-mention, Q013 age-year, and Q002 county-year data. COVID co-mention was evaluated using multiple-cause G40/G41 in the first multiple-cause box and U07.1 in the second multiple-cause box. Underlying-cause sensitivity used Q011, Q012, and Q014 with G40/G41 in the underlying-cause field.

### Mapping And Atlas Methods

Maps used local county geometry copied from the prior feasibility project. Static maps display a contiguous-U.S. viewport for legibility; Alaska and Hawaii are excluded from the static map panels but retained in analytic files and models where present. The District of Columbia is retained. Continuous rate color scales use the 5th and 95th percentile of mapped nonmissing values for display, with out-of-range counties shown at the nearest color-scale endpoint. Map-ready CSV files retain all copied county rows. Connecticut county/county-equivalent warnings from CDC WONDER remain a geographic limitation; no crosswalk correction was applied.

### Statistical Software

Analyses were performed with reproducible Python scripts archived in the public analysis repository. Modeling used pandas, NumPy, SciPy, statsmodels, matplotlib, and openpyxl where applicable. All tables and figures were generated from scripts rather than manual spreadsheet editing.

### Ethics

This study used public, aggregate, deidentified data and was deemed not human-subjects research.

## Results

### Extraction Validation And Mortality Totals

All Q001-Q015 exports were present, parsed, validated, and staged in the analysis repository with checksums. Q003 national-year multiple-cause G40/G41 mortality totaled 58,380 deaths from 2019-2024. Q001 county-period total row deaths also equaled 58,380, confirming reconciliation between the county-period and national-year extraction backbone. Q004 state-year and Q005 urbanization-year outputs reconciled exactly to Q003. Q010 COVID co-mention totaled 1,936 deaths and was bounded by Q005 by urbanization and year. Q012 and Q014 underlying-cause aggregate totals agreed at 22,306 deaths.

### County Suppression And Data Visibility Profile

The Q001 county-period file contained 3,142 county rows. Among these, 1,085 counties had exact death counts, 1,722 were suppressed with 1-9 deaths, and 335 were explicit zero rows (Table 1). The exact county death sum was 51,388, leaving a residual of 6,992 deaths within the 1,722 suppressed counties - a mean of ≈4.1 deaths per suppressed county. Exact-count counties accounted for 1.75 billion person-years and were 30.2% nonmetro. Suppressed counties accounted for 226.8 million person-years and were 77.1% nonmetro. Explicit zero counties accounted for 11.0 million person-years and were 88.7% nonmetro.

### County Covariates And Suppression Status

Mean SVI was 0.552 among exact-count counties, 0.496 among suppressed counties, and 0.352 among explicit zero counties (Table 1). Mean poverty was 13.3%, 15.1%, and 13.1%, respectively. Mean age 65 years or older was 18.2% among exact counties, 20.6% among suppressed counties, and 23.2% among explicit zero counties. Bounded mortality rates by rurality and SVI category are shown in Table 2.

### Suppression-Aware Rurality And SVI Model Results

Scenario tiering changed the interpretation of the rurality signal (Table 3; Figure 2). In the rurality plus SVI composite model, the nonmetro nonadjacent IRR was 0.97 (95% CI, 0.80-1.19) in the observed exact-positive model and 0.91 (95% CI, 0.78-1.06) after adding explicit zero counties. Assigning each suppressed cell to 1 death yielded an IRR of 0.98 (95% CI, 0.88-1.10) but fell 5,270 deaths short of the reconciled total.

Among total-preserving residual allocations, the population-scaled residual allocation produced a nonmetro nonadjacent IRR of 1.04 (95% CI, 0.98-1.10), the conservative anti-rural allocation produced 0.97 (95% CI, 0.90-1.04), and the pro-rural allocation produced 1.13 (95% CI, 1.05-1.20). These residual-allocation scenarios preserve the reconciled total and define the primary bounded interpretation.

The constant mean stress test assigned 4.06 deaths to every suppressed county, preserved the total, and yielded an IRR of 1.24 (95% CI, 1.14-1.36). This result is interpreted as a distributional stress test rather than a primary estimate because equal counts across all suppressed counties concentrate rate influence in lower-population suppressed counties. Suppressed=5 and suppressed=9 yielded IRRs of 1.29 and 1.42, respectively, but exceeded the reconciled total by 1,618 and 8,506 deaths. They are therefore retained only as extreme non-total-preserving stress tests.

### Interval-Likelihood Model Results

The interval-likelihood negative binomial model converged in rurality-only and rurality plus SVI specifications. The nonmetro nonadjacent estimate was 1.08 (approximate 95% CI, 0.62-1.88) in the rurality-only interval model and 1.07 (approximate 95% CI, 0.63-1.80) in the rurality plus SVI interval model. These interval results were consistent with uncertainty around the direction and magnitude of the rurality association and supported the suppression-sensitive classification.

### Temporal, COVID Co-Mention, And Underlying-Cause Context

National multiple-cause G40/G41 deaths increased from 7,583 in 2019 to 10,796 in 2024. The national crude rate increased from 2.31 per 100,000 in 2019 to 3.17 per 100,000 in 2024 (Table 4). COVID co-mention was concentrated in 2020-2022 and totaled 1,936 deaths across 2019-2024. Figure 4 displays urbanization-year MCOD death counts through 2024 and annual COVID co-mention context.

Underlying-cause G40/G41 mortality totaled 22,306 deaths, substantially lower than the multiple-cause total of 58,380 (Table 5). Q014 county-period underlying-cause output contained 16,650 exact county deaths, 1,866 suppressed county rows, and 772 explicit zero county rows. The UCD findings support interpretation of MCOD as a broader epilepsy/status epilepticus-related mortality construct and reinforce that suppression remains substantial under either case definition.

### Geographic Atlas Findings

The atlas demonstrates the geographic structure of data visibility. The main county suppression map distinguishes exact, suppressed, and explicit zero counties with enhanced gray contrast and hatching for zero and missing categories (Figure 1). Exact-county rate maps show observed mortality only where counts were visible, while residual-allocation maps display one bounded approach to assigning hidden deaths within suppressed intervals (Figure 3). The atlas is intended to guide interpretation, not to imply that a single mapped rate is the recovered truth for suppressed counties.

## Discussion

### Principal Findings

In this national county-level analysis of epilepsy/status epilepticus-related mortality, CDC WONDER small-cell suppression was central to the scientific interpretation. The national multiple-cause total was 58,380 deaths, and the county-period extract reconciled exactly to that total. However, only 51,388 deaths were visible as exact county counts, while 1,722 county rows were suppressed and 335 were explicit zero rows. More than half of county-period rows were therefore not exact positive counts.

The rurality-associated mortality pattern was suppression-sensitive. Visible-only models did not support a stable elevated nonmetro nonadjacent estimate. Residual-allocation scenarios that preserved the reconciled total placed the nonmetro nonadjacent IRR in a bounded range of 0.97-1.13, while interval-likelihood models estimated approximately 1.07 with wide uncertainty. Larger estimates arose under constant-count or high fixed-value stress tests, especially scenarios that assign similar hidden counts to many lower-population suppressed counties or exceed the known total. The appropriate interpretation is not that rurality was definitively associated with higher epilepsy/status epilepticus-related mortality; rather, county-level inference depends strongly on how outcome-dependent suppression is handled.

### Interpretation Relative To Prior Censored-WONDER Methods

This study is most directly related to prior work modeling highly censored CDC WONDER county mortality data. Quick's hierarchical Bayesian approach aims to estimate county rates by borrowing strength across geography and covariates, producing smoothed point estimates under an explicit model. The present framework serves a different use case: it preserves the observed reconciliation structure, exposes the residual death mass, and asks whether substantive conclusions survive transparent scenario bounds. The advantage is interpretability and assumption visibility; the cost is less precision and no claim to recover the true count in every suppressed county. For investigators seeking county estimates for downstream mapping or prediction, hierarchical modeling may be preferable. For investigators testing whether a county-level conclusion is robust to suppression, reconciliation and bounding provide an assumption-light starting point.

### What Observed-Only Analysis Would Have Missed Or Overstated

An observed-only analysis would have focused on counties with exact counts and would have excluded most suppressed counties. That approach would have produced a cleaner statistical table but a narrower and potentially misleading view of the county universe. It would have underemphasized the fact that many nonmetro counties contribute positive but hidden intervals and that these hidden intervals can materially affect rurality-associated estimates.

### Temporal And COVID Context

The 2019-2024 period included substantial temporal variation, with national multiple-cause G40/G41 deaths rising from 7,583 in 2019 to 10,796 in 2024. COVID co-mention accounted for 1,936 deaths. These findings support including pandemic-era context, but they do not eliminate the need for suppression-aware county-level inference. The county suppression structure remains important across the study period.

### Underlying-Cause Sensitivity

Underlying-cause G40/G41 mortality totaled 22,306 deaths, compared with 58,380 multiple-cause deaths. This difference is expected because MCOD captures death-certificate mentions beyond the underlying-cause field. UCD sensitivity therefore helps define the scope of the primary outcome: the manuscript studies epilepsy/status epilepticus-related mortality mentions rather than only deaths assigned to epilepsy or status epilepticus as the underlying cause.

### Implications For CDC WONDER County-Level Research

The study illustrates a general issue for county-level mortality research using CDC WONDER: for outcomes subject to small-cell suppression, exact-count county datasets are not a complete analytic universe. Researchers should report suppression profiles, preserve suppressed intervals, reconcile county extracts to aggregate totals, and test whether substantive conclusions change under plausible suppression assumptions. Fixed-value imputations should be labeled according to whether they preserve known aggregate totals, and distributional assumptions should be stated rather than hidden inside a single sensitivity table.

### Strengths

Strengths include a validated Q001-Q015 extraction set, reconciliation across county, national, state, and urbanization outputs, preservation of suppressed and zero cells as distinct statuses, explicit bias-bounding scenarios, an interval-likelihood sensitivity model, UCD and COVID co-mention context, and a national atlas of data visibility and bounded mortality patterns.

## Limitations

This was an ecological county-level analysis and does not support person-level inference. Multiple-cause mortality reflects death-certificate mention and not necessarily direct etiologic attribution. CDC WONDER suppression requires interval assumptions, and suppression-aware bounding cannot recover the true suppressed counts. The interval-likelihood model treats suppressed counties independently and does not condition on the known suppressed-cell total; a constrained interval model could be more efficient and is an important future methodological extension. The fixed alpha=1 GLM specification is a robust working-variance approach for scenario contrasts, not a claim that alpha=1 is the best dispersion estimate.

Death-certificate coding may vary by place, certifier, comorbidity, and time. COVID-era certification and mortality disruption may affect temporal patterns. County-level covariate timing differs across SVI, RUCC, NCHS, ACS, and mortality files. The Connecticut county/county-equivalent warning from CDC WONDER remains a limitation for county-level geography and rate interpretation; no crosswalk correction was applied, and the 2022 transition to planning regions could affect comparability for Connecticut county-equivalent units across the study period.

Rurality classification is imperfect, and RUCC/NCHS categories may not capture all dimensions of access, remoteness, or healthcare context. SVI and ACS component collinearity was handled by separate model families but remains a conceptual issue because social vulnerability domains overlap. Race/ethnicity and place-of-death descriptive analyses are limited by aggregation and small-cell suppression and are best interpreted as contextual summaries.

## Conclusions

In this national county-level analysis of epilepsy/status epilepticus-related mortality, more than half of county-period rows were suppressed despite full reconciliation to national totals. Apparent rurality-associated mortality patterns were sensitive to suppression assumptions, and total-preserving residual allocations supported a cautious bounded interpretation rather than a conclusive rurality claim. Suppression-aware bounding and interval-likelihood approaches provide a more transparent framework for county-level mortality surveillance and for interpreting rural epilepsy/status epilepticus mortality patterns.

## Data Availability

The analysis used public, aggregate, deidentified mortality data from CDC WONDER and public county-level covariate sources. Processed aggregate query outputs, derived analytic datasets, tables, figures, and documentation supporting this study are available at https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024. The archived release is available at https://doi.org/10.5281/zenodo.20691623. No person-level data are included.

## Code Availability

Analysis code used to import validated CDC WONDER outputs, construct suppression-aware analytic datasets, run bias-bounding and interval-likelihood models, and generate tables and figures is available at https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024. The archived release is available at https://doi.org/10.5281/zenodo.20691623.

## Ethics Statement

This study used public, aggregate, deidentified data and was deemed not human-subjects research.

## Funding

No external funding was received for this work.

## Conflicts Of Interest

The author declares no competing interests.

## Author Contributions

Gregory Pierpoint: Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Software, Validation, Visualization, Writing – original draft, Writing – review & editing.

## Acknowledgments

None.

## Declaration Of Generative AI And AI-Assisted Technologies In The Writing Process

Generative AI tools were used to assist with code generation, analysis organization, drafting, editing, and quality-control checks. The author reviewed and verified the analysis, scientific interpretation, references, and manuscript content and is responsible for the final work.

## References

1. CDC WONDER Multiple Cause of Death, 2018-2024, Single Race database. Available from: https://wonder.cdc.gov/mcd-icd10-expanded.html
2. Centers for Disease Control and Prevention. Multiple Cause of Death 2018-2024 by Single Race: CDC WONDER help documentation. Available from: https://wonder.cdc.gov/wonder/help/mcd-expanded.html
3. CDC WONDER Underlying Cause of Death, 2018-2024, Single Race database. Available from: https://wonder.cdc.gov/ucd-icd10-expanded.html
4. Centers for Disease Control and Prevention/Agency for Toxic Substances and Disease Registry. CDC/ATSDR Social Vulnerability Index data and documentation. Available from: https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html
5. U.S. Department of Agriculture Economic Research Service. Rural-Urban Continuum Codes documentation. Available from: https://www.ers.usda.gov/data-products/rural-urban-continuum-codes/documentation
6. National Center for Health Statistics. Urban-Rural Classification Scheme for Counties. Available from: https://www.cdc.gov/nchs/data-analysis-tools/urban-rural.html
7. U.S. Census Bureau. American Community Survey 5-Year Data documentation. Available from: https://www.census.gov/data/developers/data-sets/acs-5year.html
8. Vandenbroucke JP, von Elm E, Altman DG, et al. Strengthening the Reporting of Observational Studies in Epidemiology: explanation and elaboration. PLoS Med. 2007;4:e297. Available from: https://pmc.ncbi.nlm.nih.gov/articles/PMC2034723/
9. STROBE Statement. STROBE checklists for observational studies. Available from: https://www.strobe-statement.org/checklists/
10. Elsevier. Generative AI policies for journals. Available from: https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals
11. Pierpoint G. Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024. Version 1.0.0. Zenodo. https://doi.org/10.5281/zenodo.20691623 Available from: https://doi.org/10.5281/zenodo.20691623
12. Quick H. Estimating County-Level Mortality Rates Using Highly Censored Data From CDC WONDER. Prev Chronic Dis. 2019;16:180441. doi:10.5888/pcd16.180441. Available from: https://www.cdc.gov/pcd/issues/2019/18_0441.htm
13. DeGiorgio CM, Curtis A, Carapetian A, Hovsepian D, Krishnadasan A, Markovic D. Why are epilepsy mortality rates rising in the United States? A population-based multiple cause-of-death study. BMJ Open. 2020;10:e035767. doi:10.1136/bmjopen-2019-035767. Available from: https://pubmed.ncbi.nlm.nih.gov/32839157/
14. Tian N, Kobau R, Friedman D, Liu Y, Eke PI, Greenlund KJ. Mortality and mortality disparities among people with epilepsy in the United States, 2011-2021. Epilepsy Behav. 2024;155:109770. doi:10.1016/j.yebeh.2024.109770. Available from: https://pubmed.ncbi.nlm.nih.gov/38636143/
15. Duke SM, González Otárula KA, Canales T, Lu E, Stout A, Ghearing GR, Sajatovic M. A systematic literature review of health disparities among rural people with epilepsy in the United States and Canada. Epilepsy Behav. 2021;122:108181. doi:10.1016/j.yebeh.2021.108181. Available from: https://pubmed.ncbi.nlm.nih.gov/34252832/
16. Iqbal J, Shafique MA, Rangwala BS, et al. Demographic and regional patterns of epilepsy-related mortality in the USA: insights from CDC WONDER data. Surg Neurol Int. 2024;15:450. doi:10.25259/SNI_592_2024. Available from: https://pubmed.ncbi.nlm.nih.gov/39777187/
17. Centers for Disease Control and Prevention. Reporting and Coding Deaths Due to COVID-19. Available from: https://www.cdc.gov/nchs/covid19/coding-and-reporting.htm



## Tables

Table 1. County characteristics by Q001 death-count status.

| Death-count status | Counties | Person-years, millions | Exact deaths | Death interval | Nonmetro, % | Mean SVI | Poverty, % | Uninsured, % | Age >=65, % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Exact | 1,085 | 1749.2 | 51,388 | 51,388-51,388 | 30.2 | 0.552 | 13.3 | 8.5 | 18.2 |
| Suppressed 1-9 | 1,722 | 226.8 | 0 | 1,722-15,498 | 77.1 | 0.496 | 15.1 | 9.6 | 20.6 |
| Explicit zero | 335 | 11.0 | 0 | 0-0 | 88.7 | 0.352 | 13.1 | 9.9 | 23.2 |

Table 2. Mortality totals and bounded rates by rurality and SVI category.

| Rurality | SVI | Counties | Deaths lower-mid-upper | Supp/zero rows | Rate lower-mid-upper |
| --- | --- | --- | --- | --- | --- |
| Metro Large | Q1 lowest | 156 | 3,490-3,730-3,970 | 60/2 | 2.12-2.26-2.41 |
| Metro Large | Q2 | 120 | 5,983-6,123-6,263 | 35/1 | 2.38-2.43-2.49 |
| Metro Large | Q3 | 90 | 7,143-7,231-7,319 | 22/2 | 2.59-2.63-2.66 |
| Metro Large | Q4 highest | 75 | 11,785-11,829-11,873 | 11/0 | 2.69-2.70-2.71 |
| Metro Other | Q1 lowest | 167 | 1,657-2,013-2,369 | 89/18 | 2.34-2.84-3.34 |
| Metro Other | Q2 | 187 | 3,848-4,152-4,456 | 76/4 | 2.84-3.06-3.29 |
| Metro Other | Q3 | 205 | 6,424-6,632-6,840 | 52/8 | 3.25-3.36-3.46 |
| Metro Other | Q4 highest | 179 | 5,614-5,802-5,990 | 47/3 | 3.33-3.44-3.56 |
| Nonmetro Adjacent | Q1 lowest | 213 | 600-1,224-1,848 | 156/29 | 1.94-3.97-5.99 |
| Nonmetro Adjacent | Q2 | 245 | 1,053-1,729-2,405 | 169/17 | 2.25-3.69-5.13 |
| Nonmetro Adjacent | Q3 | 275 | 1,352-2,108-2,864 | 189/16 | 2.55-3.97-5.40 |
| Nonmetro Adjacent | Q4 highest | 311 | 1,760-2,576-3,392 | 204/15 | 3.19-4.67-6.14 |
| Nonmetro Nonadjacent | Q1 lowest | 248 | 239-783-1,327 | 136/104 | 1.60-5.25-8.90 |
| Nonmetro Nonadjacent | Q2 | 231 | 381-997-1,613 | 154/61 | 1.76-4.60-7.44 |
| Nonmetro Nonadjacent | Q3 | 211 | 566-1,198-1,830 | 158/29 | 2.27-4.80-7.33 |
| Nonmetro Nonadjacent | Q4 highest | 218 | 657-1,301-1,945 | 161/26 | 2.45-4.85-7.26 |
| Unmatched Covariates | Unmatched | 11 | 558-570-582 | 3/0 | 5.11-5.22-5.33 |

Table 3. Suppression-aware nonmetro nonadjacent model results, rurality plus SVI specification.

| Tier | Scenario | Assigned deaths | IRR | 95% CI | Interpretation note |
| --- | --- | --- | --- | --- | --- |
| Visible-only | Observed exact-positive only | 51,388 | 0.97 | 0.80-1.19 | Falls short of reconciled total by 6,992 deaths. |
| Visible-only | Observed exact plus explicit zero | 51,388 | 0.91 | 0.78-1.06 | Falls short of reconciled total by 6,992 deaths. |
| Fixed-value stress test, not total-preserving | Suppressed = 1 | 53,110 | 0.98 | 0.88-1.10 | Falls short of reconciled total by 5,270 deaths. |
| Constant-count stress test, total-preserving | Suppressed = 4.06 (constant mean) | 58,380 | 1.24 | 1.14-1.36 | Preserves total as a constant-count stress test; equal assignment concentrates rate influence in lower-population suppressed counties. |
| Fixed-value stress test, not total-preserving | Suppressed = 5 | 59,998 | 1.29 | 1.18-1.42 | Exceeds reconciled total by 1,618 deaths. |
| Fixed-value stress test, not total-preserving | Suppressed = 9 | 66,886 | 1.42 | 1.27-1.60 | Exceeds reconciled total by 8,506 deaths. |
| Residual-allocation, total-preserving | Population-scaled residual allocation | 58,380 | 1.04 | 0.98-1.10 | Preserves the reconciled national total. |
| Residual-allocation, total-preserving | Conservative anti-rural residual allocation | 58,380 | 0.97 | 0.90-1.04 | Preserves the reconciled national total. |
| Residual-allocation, total-preserving | Pro-rural residual allocation | 58,380 | 1.13 | 1.05-1.20 | Preserves the reconciled national total. |
| Interval model | Interval-likelihood negative binomial | Not assigned | 1.07 | 0.63-1.80 | Uses interval likelihood; known suppressed-cell total not imposed. |

Table 4. National temporal and COVID-19 co-mention context.

| Year | MCOD deaths | Population | National rate per 100,000 | COVID co-mention interval | COVID midpoint, % of MCOD |
| --- | --- | --- | --- | --- | --- |
| 2019 | 7,583 | 328,239,523 | 2.31 | 0-0 | 0.0 |
| 2020 | 9,147 | 329,484,123 | 2.78 | 548-556 | 6.0 |
| 2021 | 9,733 | 331,893,745 | 2.93 | 549-557 | 5.7 |
| 2022 | 10,575 | 333,287,557 | 3.17 | 478-486 | 4.6 |
| 2023 | 10,546 | 334,914,895 | 3.15 | 198-206 | 1.9 |
| 2024 | 10,796 | 340,110,988 | 3.17 | 150-158 | 1.4 |

Table 5. Underlying-cause sensitivity and MCOD/UCD comparison.

| Measure | MCOD G40/G41 | UCD G40/G41 | Interpretation |
| --- | --- | --- | --- |
| National aggregate deaths | 58,380 | 22,306 | MCOD is the broader death-certificate mention construct. |
| Exact county deaths | 51,388 | 16,650 | Visible exact deaths are lower in UCD sensitivity. |
| Exact county rows | 1,085 | 504 | Rows are county-period rows. |
| Suppressed county rows | 1,722 | 1,866 | Suppressed rows remain 1-9 intervals, not zero. |
| Explicit-zero county rows | 335 | 772 | Explicit zeros are distinct from suppression. |

## Figure Legends

Figure 1. County multiple-cause G40/G41 death-count status, 2019-2024. Blue indicates exact counts, orange indicates suppressed 1-9 death cells, and hatched gray indicates explicit zero cells. Static map viewport displays the contiguous United States; Alaska and Hawaii are retained in analytic files and models where present but are not shown in the static panel.

Figure 2. Suppression-scenario sensitivity for the nonmetro nonadjacent incidence rate ratio in the rurality plus SVI model. Points are IRRs and whiskers are 95% CIs on a log scale. Scenario tiers distinguish visible-only models, total-preserving residual allocations, constant-count and fixed-value stress tests, and interval-likelihood modeling.

Figure 3. Suppression-aware residual-allocation county mortality rate. Color scale uses display clipping at the 5th and 95th percentile of mapped nonmissing rates, with out-of-range counties shown at the nearest color endpoint.

Figure 4. Urbanization-year multiple-cause G40/G41 death counts and COVID-19 co-mention context, 2019-2024. Panel A shows MCOD deaths by NCHS urbanization category; the Not Available category is a data-quality/availability category, not an urbanization level. Panel B shows COVID-19 co-mention death intervals aggregated across urbanization categories. National crude rates are reported in Table 4.
