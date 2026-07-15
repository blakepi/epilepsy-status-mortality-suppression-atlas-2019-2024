# Suppression-aware county-level epilepsy and status epilepticus mortality in the United States, 2019-2024

## Abstract

### Objective

To quantify how CDC WONDER county-level suppression shapes national county-level analyses of epilepsy/status epilepticus-related mortality and to evaluate rurality-associated patterns using suppression-aware methods.

### Methods

We analyzed the CDC WONDER Multiple Cause of Death, 2018-2024 Single Race database for 2019-2024. The primary outcome was multiple-cause mortality with ICD-10 G40 (epilepsy) or G41 (status epilepticus) listed anywhere on the death certificate. Underlying-cause G40/G41 and COVID-19 co-mention (U07.1) were evaluated as contextual analyses. County-period and county-year extracts were linked to county rurality and social vulnerability covariates. Suppressed county cells were coded as interval counts of 1-9 deaths and were not treated as zero. We compared observed-only models with bias-bounding scenarios, residual-allocation analyses, and interval-likelihood negative binomial models.

### Results

National multiple-cause G40/G41 mortality totaled 58,380 deaths. The county-period extract reconciled to this total but contained 51,388 exact county deaths, 1,722 suppressed county rows, and 335 explicit zero rows. County-year exact deaths totaled 33,217. Rurality-associated estimates varied meaningfully across suppression assumptions: the nonmetro nonadjacent estimate ranged from below unity in observed-only and conservative scenarios to elevated under suppressed-equals-5, suppressed-equals-9, and pro-rural allocation scenarios. Phase 10 stress testing classified the rurality finding as suppression-sensitive. COVID co-mention totaled 1,936 deaths, and underlying-cause G40/G41 mortality totaled 22,306 deaths.

### Conclusion

County-level epilepsy/status epilepticus mortality inference in CDC WONDER is strongly shaped by outcome-dependent suppression. Suppression-aware bounding and interval-likelihood approaches provide a more transparent framework for interpreting rurality-associated, social, temporal, and geographic mortality patterns.

## Keywords

Epilepsy; status epilepticus; mortality; CDC WONDER; suppression-aware analysis; rurality; county-level surveillance; multiple-cause mortality.

## Introduction

Epilepsy and status epilepticus contribute to mortality burden in the United States and may appear on death certificates as underlying or contributing conditions. Multiple-cause mortality data are therefore useful for surveillance because they capture deaths in which epilepsy or status epilepticus was mentioned anywhere on the death certificate, rather than only deaths for which these diagnoses were selected as the underlying cause.

Rurality, social vulnerability, and health-system context are plausible contributors to geographic variation in epilepsy-related mortality. Rural communities may differ from metropolitan areas in specialist availability, emergency medical services, travel time, comorbidity burden, medication access, and death-certificate certification context. These factors are best interpreted as contextual hypotheses in aggregate mortality data, not as demonstrated mechanisms in county-level ecological analyses.

National county-level mortality analyses are difficult for epilepsy/status epilepticus because CDC WONDER suppresses small death counts. Suppressed county cells generally represent 1-9 deaths. This creates outcome-dependent data visibility: counties with exact counts are partly selected by population size and mortality burden, while many rural and low-population counties are represented only by bounded intervals or explicit zero counts. Exact-count counties are therefore not a random subset of all counties.

This issue is especially consequential for rare or moderately rare outcomes, rural counties, and county-level ecological models. Observed-only county models can overstate, attenuate, or mischaracterize rurality-associated mortality patterns because they exclude or simplify a large portion of the county universe. Treating suppressed cells as zero is also inappropriate because suppression indicates a positive interval, not absence of mortality.

This study uses a suppression-aware extraction and modeling framework to map county-level epilepsy/status epilepticus mortality, quantify suppression patterns, bound rurality-associated estimates, and provide temporal, COVID co-mention, and underlying-cause context. The major contribution is not a strong rurality claim; it is a national suppression-aware atlas and a methodological caution for county-level WONDER mortality research.

The aims were:

1. Describe county-level exact, suppressed, and zero mortality-count patterns for epilepsy/status epilepticus-related mortality.
2. Estimate rurality-associated mortality patterns under observed-only, bias-bounded, residual-allocation, and interval-likelihood approaches.
3. Characterize temporal, urbanization, COVID co-mention, and underlying-cause sensitivity patterns.
4. Produce a suppression-aware geographic atlas to guide interpretation of county-level epilepsy mortality surveillance.

## Methods

### Study design and data sources

We conducted a national ecological county-level mortality analysis using public aggregate mortality and county covariate data. Mortality data came from CDC WONDER Current Final Multiple Cause of Death Data, 2018-2024, Single Race. The analytic years were 2019-2024. County covariates were imported from the prior feasibility project and included CDC/ATSDR Social Vulnerability Index (SVI) 2022, U.S. Department of Agriculture Rural-Urban Continuum Codes (RUCC) 2023, National Center for Health Statistics (NCHS) 2023 urban-rural classification, and American Community Survey (ACS) 2019-2023 county variables.

### Case definition

The primary outcome was multiple-cause mortality with ICD-10 G40 or G41 listed anywhere on the death certificate. The confirmed CDC WONDER cause syntax was:

```text
G40 (Epilepsy)
G41 (Status epilepticus)
```

The secondary sensitivity outcome was underlying-cause mortality with ICD-10 G40 or G41. COVID-19 co-mention analyses used the confirmed multiple-cause syntax:

```text
U07.1 (COVID-19)
```

Multiple-cause mortality is interpreted as epilepsy/status epilepticus-related mortality mention, not as definitive attribution of death to epilepsy or status epilepticus.

### CDC WONDER extraction and validation

The analysis used the validated Q001-Q015 extraction set from the CDC WONDER extraction project. Q001 provided county-period multiple-cause G40/G41 mortality for 2019-2024 with zero and suppressed values requested. Q002 provided county-year multiple-cause G40/G41 mortality. Q003, Q004, and Q005 provided national-year, state-year, and urbanization-year multiple-cause totals. Q006-Q009B and Q013-Q015 provided descriptive, age, race/ethnicity, state-period, and sensitivity context. Q010 provided urbanization-year multiple-cause G40/G41 and U07.1 COVID-19 co-mention. Q011, Q012, and Q014 provided underlying-cause sensitivity outputs.

The extraction validation confirmed that Q001, Q003, Q004, and Q005 reconciled to 58,380 multiple-cause G40/G41 deaths for 2019-2024. Q002 county-year exact-plus-suppressed intervals contained Q003 national-year totals. Q010 was bounded by Q005 by urbanization and year. Q012 and Q014 underlying-cause aggregate totals agreed at 22,306 deaths.

### Suppression status definitions

County death counts were coded as exact, suppressed_1_9, zero, missing_unreturned, aggregate_total, or invalid_noncounty. Exact cells were coded as [death, death]. Suppressed cells were coded as [1, 9] with midpoint 5 for descriptive summaries. Explicit zero cells were coded as [0, 0]. Suppressed cells were not treated as zero. Missing or unreturned cells, if present, were not treated as zero. Aggregate total rows were retained for reconciliation but excluded from county models.

### County covariates and rurality measures

County Federal Information Processing Standards (FIPS) codes were preserved as 5-character strings. The county merge included 3,142 WONDER Q001 county rows and 3,144 combined covariate county rows. The FIPS merge matched 3,131 counties, leaving 11 WONDER counties without covariates and 13 covariate counties without WONDER Q001 rows.

The primary collapsed RUCC rurality variable used:

- metro_large: RUCC 1
- metro_other: RUCC 2-3
- nonmetro_adjacent: RUCC 4, 6, 8
- nonmetro_nonadjacent: RUCC 5, 7, 9

Sensitivity rurality definitions included binary RUCC 1-3 versus 4-9 and NCHS six-level urban-rural classification.

### Social vulnerability and component covariates

SVI was modeled as a composite family using SVI quartile. ACS component models were modeled separately using poverty, household income, education, uninsurance, race/ethnicity composition, and age structure. SVI was not modeled together with its own component variables in the primary model family. Component-model variance inflation factors were modest in the Phase 9 diagnostics, with all reported values below 3.

### County-period analytic dataset

Q001 was the primary county-period mortality source. The model exposure denominator used summed Q002 annual county populations where available. Q001 county population values exactly matched the summed Q002 county-year populations for all 3,142 counties, supporting interpretation as 2019-2024 person-years for the period count models.

### County-year and temporal datasets

Q002 provided county-year intervals and suppression status for 2019-2024. Because county-year rows were sparse and heavily affected by suppression, county-year outputs were used primarily for suppression profiling and reconciliation. Q003, Q004, Q005, and Q010 provided the primary aggregate temporal and urbanization context.

### Bias-bounding analyses

County-period models used a count-model framework with log person-years as the offset. The primary bias-bounding scenarios were: observed exact-positive only; exact plus explicit zero; suppressed cells assigned 1 death; suppressed cells assigned 5 deaths; suppressed cells assigned 9 deaths; population-scaled residual allocation; conservative anti-rural allocation; and pro-rural allocation. The residual allocation used the difference between the Q001 total row and the exact county death sum, constrained to the 1-9 death range for suppressed counties.

### Interval-likelihood negative binomial model

An interval-likelihood negative binomial model was attempted after bias-bounding analyses. Exact rows contributed P(Y = y), zero rows contributed P(Y = 0), and suppressed rows contributed P(1 <= Y <= 9). The interval-likelihood models included rurality-only and rurality plus SVI specifications. Approximate standard errors used optimizer inverse-Hessian estimates, so bias-bounding analyses remained the primary suppression-aware results when interval uncertainty was unstable.

### Temporal, COVID co-mention, and underlying-cause analyses

Temporal analyses used Q003 national-year, Q004 state-year, Q005 urbanization-year, Q010 COVID co-mention, Q013 age-year, and Q002 county-year data. COVID co-mention was evaluated using multiple-cause G40/G41 in the first multiple-cause box and U07.1 in the second multiple-cause box. Underlying-cause sensitivity used Q011, Q012, and Q014 with G40/G41 in the underlying-cause field.

### Mapping and atlas methods

Maps used local county geometry copied from the prior feasibility project. The atlas included county suppression/data-status maps, exact-county rates, residual-allocation rates, rural/high-SVI priority maps, state-period rates, and underlying-cause suppression maps. The static PNG map viewport emphasizes the contiguous United States for legibility; map-ready CSV files retain all copied county rows.

### Statistical software

Analyses were performed with reproducible Python scripts in the Phase 9/10 project. Modeling used pandas, NumPy, SciPy, statsmodels, matplotlib, and openpyxl where applicable. All tables and figures were generated from scripts rather than manual spreadsheet editing.

### Ethics

The analysis used public aggregate deidentified mortality and county covariate data. No person-level data were used. Final institutional wording should be checked before submission.

## Results

### Extraction validation and mortality totals

All Q001-Q015 exports were present, parsed, validated, and copied into the Option B analysis project with checksums. Q003 national-year multiple-cause G40/G41 mortality totaled 58,380 deaths from 2019-2024. Q001 county-period total row deaths also equaled 58,380, confirming reconciliation between the county-period and national-year extraction backbone.

Q004 state-year and Q005 urbanization-year outputs reconciled exactly to Q003. Q002 county-year exact-plus-suppressed intervals contained Q003 national-year totals. Suppressed values were preserved as suppressed_1_9 and were not parsed as zero.

### County suppression and data visibility profile

The Q001 county-period file contained 3,142 county rows. Among these, 1,085 counties had exact death counts, 1,722 were suppressed with 1-9 deaths, and 335 were explicit zero rows. The exact county death sum was 51,388, leaving a residual of 6,992 deaths represented within suppressed county intervals.

The data visibility pattern differed sharply across county groups. Exact-count counties accounted for 1.75 billion person-years and were 30.2% nonmetro. Suppressed counties accounted for 226.8 million person-years and were 77.1% nonmetro. Explicit zero counties accounted for 11.0 million person-years and were 88.7% nonmetro. This pattern illustrates why observed-only county analyses are vulnerable to outcome-dependent visibility.

### County covariates and suppression status

Mean SVI was 0.552 among exact-count counties, 0.496 among suppressed counties, and 0.352 among explicit zero counties. Mean poverty was 13.3%, 15.1%, and 13.1%, respectively. Mean age 65 years or older was 18.2% among exact counties, 20.6% among suppressed counties, and 23.2% among explicit zero counties. These differences show that suppression status was related to county population and rurality structure and should not be treated as a simple random missingness problem.

### Suppression-aware rurality and SVI model results

Rurality-associated estimates varied meaningfully across suppression assumptions. In the rurality plus SVI composite family, the nonmetro nonadjacent incidence rate ratio (IRR) was 0.97 (95% CI, 0.80-1.19) in the observed exact-positive model and 0.91 (95% CI, 0.78-1.06) in the exact plus explicit zero model. Assigning suppressed cells to 1 death yielded an IRR of 0.98 (95% CI, 0.88-1.10). Assigning suppressed cells to 5 deaths yielded an IRR of 1.29 (95% CI, 1.18-1.42), and assigning suppressed cells to 9 deaths yielded an IRR of 1.42 (95% CI, 1.27-1.60).

Population-scaled residual allocation produced a nonmetro nonadjacent IRR of 1.04 (95% CI, 0.98-1.10). The conservative anti-rural allocation produced an IRR of 0.97 (95% CI, 0.90-1.04), whereas the pro-rural allocation produced an IRR of 1.13 (95% CI, 1.05-1.20). Phase 10 stress testing therefore classified the rurality finding as SUPPRESSION_SENSITIVE_SIGNAL. In manuscript terms, the apparent rurality pattern was sensitive to the handling of suppressed county cells.

The SVI Q4 versus Q1 estimate was also scenario-dependent. In the rurality plus SVI composite family, SVI Q4 was below unity in the observed exact-positive model (IRR, 0.86; 95% CI, 0.75-0.99), near unity under several midpoint and high-suppression scenarios, and modestly elevated under the population-scaled and conservative allocation scenarios. These findings support cautious interpretation of social vulnerability patterns in the presence of suppression.

### Interval-likelihood model results

The interval-likelihood negative binomial model converged in rurality-only and rurality plus SVI specifications. The nonmetro nonadjacent estimate was 1.08 (approximate 95% CI, 0.62-1.88) in the rurality-only interval model and 1.07 (approximate 95% CI, 0.63-1.80) in the rurality plus SVI interval model. These interval results were consistent with uncertainty around the direction and magnitude of the rurality association and supported the Phase 10 suppression-sensitive classification.

### Temporal and urbanization trends

National multiple-cause G40/G41 deaths increased from 7,583 in 2019 to 10,796 in 2024. The national crude rate increased from 2.31 per 100,000 in 2019 to 3.17 per 100,000 in 2024. Urbanization-year trends provided aggregate context because county-year rows were sparse and suppression-heavy. These temporal analyses are descriptive and should not be interpreted as identifying pandemic mechanisms.

### COVID co-mention

Q010 COVID co-mention totaled 1,936 deaths and was bounded by Q005 urbanization-year multiple-cause G40/G41 totals. COVID co-mention provides important temporal context for the 2020-2024 period but does not fully explain the county suppression problem or the instability of rurality estimates.

### Underlying-cause sensitivity

Underlying-cause G40/G41 mortality totaled 22,306 deaths in Q012/Q014, substantially lower than the multiple-cause total of 58,380. Q014 county-period underlying-cause output contained 16,650 exact county deaths, 1,866 suppressed county rows, and 772 explicit zero county rows. The UCD findings support interpretation of MCOD as a broader epilepsy/status epilepticus-related mortality construct and reinforce that suppression remains substantial under either case definition.

### Geographic atlas findings

The atlas demonstrates the geographic structure of data visibility. The main county suppression map distinguishes exact, suppressed, and explicit zero counties. Exact-county rate maps show observed mortality only where counts were visible, while residual-allocation maps display one bounded approach to assigning hidden deaths within suppressed intervals. The atlas is intended to guide interpretation, not to imply that a single mapped rate is the recovered truth for suppressed counties.

## Discussion

### Principal findings

In this national county-level analysis of epilepsy/status epilepticus-related mortality, CDC WONDER small-cell suppression was central to the scientific interpretation. The national multiple-cause total was 58,380 deaths, and the county-period extract reconciled exactly to that total. However, only 51,388 deaths were visible as exact county counts, while 1,722 county rows were suppressed and 335 were explicit zero rows. More than half of county-period rows were therefore not exact positive counts.

The rurality-associated mortality pattern was suppression-sensitive. Observed-only models and conservative allocation scenarios did not support a stable elevated nonmetro nonadjacent estimate, whereas midpoint and high-suppression assumptions did. Interval-likelihood models estimated modest elevation with wide approximate uncertainty. The appropriate interpretation is not that rurality was definitively associated with higher epilepsy/status epilepticus-related mortality; rather, county-level inference depends strongly on how outcome-dependent suppression is handled.

### Interpretation of suppression-sensitive rurality pattern

Suppression is not a simple nuisance feature in this setting. It is directly related to death counts and indirectly related to county population size, which is strongly patterned by rurality. Counties with exact counts are a selected group with larger population exposure and more visible deaths. Suppressed and zero counties are disproportionately nonmetro. Excluding these counties, or handling them as if their hidden counts were known, changes the rurality estimand.

The bias-bounding results show that rurality-associated estimates can move across null and elevated ranges depending on the assumed distribution of suppressed deaths. This result is scientifically important even without a stable rurality claim because it clarifies the limits of observed-only county mortality analyses for epilepsy/status epilepticus and similar outcomes.

### What observed-only analysis would have missed or overstated

An observed-only analysis would have focused on counties with exact counts and would have excluded most suppressed counties. That approach would have produced a cleaner statistical table but a narrower and potentially misleading view of the county universe. It would have underemphasized the fact that many nonmetro counties contribute positive but hidden intervals and that these hidden intervals can materially affect rurality-associated estimates.

### Temporal and COVID context

The 2019-2024 period included substantial temporal variation, with national multiple-cause G40/G41 deaths rising from 7,583 in 2019 to 10,796 in 2024. COVID co-mention accounted for 1,936 deaths. These findings support including pandemic-era context, but they do not eliminate the need for suppression-aware county-level inference. The county suppression structure remains important across the study period.

### Underlying-cause sensitivity

Underlying-cause G40/G41 mortality totaled 22,306 deaths, compared with 58,380 multiple-cause deaths. This difference is expected because MCOD captures death-certificate mentions beyond the underlying-cause field. UCD sensitivity therefore helps define the scope of the primary outcome: the manuscript studies epilepsy/status epilepticus-related mortality mentions rather than only deaths assigned to epilepsy or status epilepticus as the underlying cause.

### Implications for epilepsy mortality surveillance

The findings support a surveillance framework that treats county-level small-cell suppression as information about uncertainty, not merely as missing data. For epilepsy/status epilepticus, suppression-aware intervals, bounded estimates, and atlas maps can help investigators distinguish visible mortality patterns from patterns that depend on hidden county intervals. This approach is especially relevant when rurality and low population are central to the scientific question.

### Implications for CDC WONDER county-level research

The study illustrates a general issue for county-level mortality research using CDC WONDER: for outcomes subject to small-cell suppression, exact-count county datasets are not a complete analytic universe. Researchers should report suppression profiles, preserve suppressed intervals, reconcile county extracts to aggregate totals, and test whether substantive conclusions change under plausible suppression assumptions.

### Strengths

Strengths include a validated Q001-Q015 extraction set, reconciliation across county, national, state, and urbanization outputs, preservation of suppressed and zero cells as distinct statuses, explicit bias-bounding scenarios, an interval-likelihood sensitivity model, UCD and COVID co-mention context, and a national atlas of data visibility and bounded mortality patterns.

## Limitations

This was an ecological county-level analysis and does not support person-level inference. Multiple-cause mortality reflects death-certificate mention and not necessarily direct etiologic attribution. CDC WONDER suppression requires interval assumptions, and suppression-aware bounding cannot recover the true suppressed counts. Death-certificate coding may vary by place, certifier, comorbidity, and time. COVID-era certification and mortality disruption may affect temporal patterns. County-level covariate timing differs across SVI, RUCC, NCHS, ACS, and mortality files.

The Connecticut county/county-equivalent warning from CDC WONDER remains a limitation for county-level geography and rate interpretation; no crosswalk correction was applied in Phase 9. Rurality classification is imperfect, and RUCC/NCHS categories may not capture all dimensions of access, remoteness, or healthcare context. SVI and ACS component collinearity was handled by separate model families but remains a conceptual issue because social vulnerability domains overlap. Race/ethnicity and place-of-death descriptive analyses are limited by aggregation and small-cell suppression and are best interpreted as contextual summaries.

## Conclusions

In this national county-level analysis of epilepsy/status epilepticus-related mortality, more than half of county-period rows were suppressed despite full reconciliation to national totals. Apparent rurality-associated mortality patterns were sensitive to suppression assumptions, demonstrating that observed-only county analyses can misrepresent geographic patterns for outcomes subject to small-cell suppression. Suppression-aware bounding and interval-likelihood approaches provide a more transparent framework for county-level mortality surveillance and for interpreting rural epilepsy/status epilepticus mortality patterns.

## Data Availability

Data were derived from public aggregate CDC WONDER outputs and public county covariate sources. The Phase 9 project contains copied and checksummed processed WONDER inputs and derived analytic datasets. Public release of the derived dataset and code should be coordinated with final repository or archive planning; no repository DOI has been assigned in Phase 11.

## Code Availability

Analysis code is currently organized in the Phase 9/10 project at `C:\Research\EpilepsyMortalityOptionB\src`. A public repository or archival release should be prepared before submission if required by the target journal.

## Ethics Statement

This study used public aggregate deidentified mortality and county covariate data and did not use person-level records. The study is expected to be outside human-subjects review requirements, but final wording should be checked against institutional policy.

## AI Disclosure

Generative AI tools were used to assist with code generation, analysis organization, drafting, and editing. The authors are responsible for reviewing, verifying, and approving all scientific content, analyses, and final text.

## References placeholder/checklist

No final reference list is provided in this Phase 11 draft. Required categories include CDC WONDER documentation, CDC WONDER suppression documentation, ICD-10 cause-of-death documentation, SVI documentation, USDA RUCC documentation, NCHS urban-rural classification documentation, ACS documentation, prior epilepsy mortality literature, rural-urban epilepsy outcomes literature, ecological bias methods, interval-censored or suppressed-count modeling methods, and COVID mortality/certification context.

## Tables

Table 1. County characteristics by Q001 death-count status.

Table 2. Mortality totals and bounded rates by rurality and SVI category.

Table 3. Suppression-aware rurality and SVI model results.

Table 4. Temporal, urbanization, and COVID co-mention context.

Table 5. Underlying-cause sensitivity and UC/MC comparison. Proposed for supplement unless retained in main text after journal targeting.

## Figure Legends

Figure 1. County multiple-cause G40/G41 death-count status, 2019-2024.

Figure 2. Suppression-bounds model estimates.

Figure 3. Suppression-aware residual-allocation county mortality rate.

Figure 4. Urbanization-year trend and COVID co-mention context.

## Supplemental Material Plan

Supplemental material should include UCD county suppression maps, state-period maps, race/ethnicity and place-of-death descriptive tables, additional model specifications, county-year suppression summaries, interval-model diagnostics, and reference verification materials.
