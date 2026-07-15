# Portal Copy-Paste Fields

Title: Suppression-aware county-level epilepsy and status epilepticus mortality in the United States, 2019-2024

Short title: Suppression-aware epilepsy mortality mapping

## Abstract

To quantify how CDC WONDER county-level suppression shapes national county-level analyses of epilepsy/status epilepticus-related mortality and to evaluate rurality-associated patterns using suppression-aware methods.


We analyzed the CDC WONDER Multiple Cause of Death, 2018-2024 Single Race database for 2019-2024. The primary outcome was multiple-cause mortality with ICD-10 G40 (epilepsy) or G41 (status epilepticus) listed anywhere on the death certificate. Underlying-cause G40/G41 and COVID-19 co-mention (U07.1) were evaluated as contextual analyses. County-period and county-year extracts were linked to county rurality and social vulnerability covariates. Suppressed county cells were coded as interval counts of 1-9 deaths and were not treated as zero. We compared observed-only models with bias-bounding scenarios, residual-allocation analyses, and interval-likelihood negative binomial models.


National multiple-cause G40/G41 mortality totaled 58,380 deaths. The county-period extract reconciled to this total but contained 51,388 exact county deaths, 1,722 suppressed county rows, and 335 explicit zero rows. County-year exact deaths totaled 33,217. Rurality-associated estimates varied meaningfully across suppression assumptions: the nonmetro nonadjacent estimate ranged from below unity in observed-only and conservative scenarios to elevated under suppressed-equals-5, suppressed-equals-9, and pro-rural allocation scenarios. Phase 10 stress testing classified the rurality finding as suppression-sensitive. COVID co-mention totaled 1,936 deaths, and underlying-cause G40/G41 mortality totaled 22,306 deaths.


County-level epilepsy/status epilepticus mortality inference in CDC WONDER is strongly shaped by outcome-dependent suppression. Suppression-aware bounding and interval-likelihood approaches provide a more transparent framework for interpreting rurality-associated, social, temporal, and geographic mortality patterns.

Keywords: Epilepsy; status epilepticus; mortality; CDC WONDER; suppression-aware analysis; rural health; ecological study.

## Highlights

- County-level epilepsy/status epilepticus mortality estimates were suppression-sensitive.
- CDC WONDER county suppression affected 1,722 county-period MCOD rows.
- Observed-only rurality models did not provide a stable final rurality claim.
- Bias-bounding and interval-likelihood models made suppression uncertainty explicit.
- The study provides a national suppression-aware mortality atlas for 2019-2024.

## Cover letter

# Cover Letter

Dear Editors,

We are pleased to submit the manuscript, "Suppression-aware county-level epilepsy and status epilepticus mortality in the United States, 2019-2024," for consideration in Epilepsy & Behavior.

This manuscript provides a national suppression-aware county-level analysis and atlas of epilepsy/status epilepticus-related mortality in the United States from 2019-2024. Rather than treating CDC WONDER county suppression as a limitation only, the study explicitly models and bounds suppressed death counts and shows that observed rurality patterns are sensitive to suppression assumptions. The work is relevant to epilepsy outcomes research, rural health surveillance, and methods for using public mortality data responsibly.

The study uses validated CDC WONDER Multiple Cause of Death outputs, county covariates, bias-bounding scenarios, residual-allocation analyses, interval-likelihood negative binomial modeling, temporal and COVID co-mention context, and underlying-cause sensitivity. The central contribution is not a strong rural-disparity claim. Instead, the manuscript shows that county-level inference for epilepsy/status epilepticus mortality is strongly shaped by outcome-dependent small-cell suppression and should be interpreted using suppression-aware methods.

We believe this framing will be of interest to readers studying epilepsy outcomes, mortality surveillance, rural health, and public-use mortality data methods. The manuscript also provides practical guidance for investigators using CDC WONDER county-level data for outcomes in which small-cell suppression affects a large share of counties.

The analysis used public aggregate deidentified data. Submission declarations requiring final author verification are flagged in the package metadata, including funding, conflicts of interest, corresponding-author details, and any institutional wording.

This manuscript is not under consideration elsewhere. [VERIFY before submission]

Sincerely,

[VERIFY: corresponding author name and contact information]


Funding statement: [VERIFY: funding source or no external funding]

Conflict of interest statement: [VERIFY: author disclosures]

## Ethics statement

This study used public aggregate deidentified mortality data and public county-level covariate data. No person-level records were accessed or analyzed. The study is expected to be outside human-subjects review requirements because it uses public aggregate deidentified data, but final wording should be checked against institutional policy before submission.

## Data availability statement

The data used in this study are public, aggregate, and deidentified. Mortality data were obtained from CDC WONDER Multiple Cause of Death outputs. County covariates were derived from public sources including CDC/ATSDR Social Vulnerability Index, USDA Rural-Urban Continuum Codes, NCHS urban-rural classification, and American Community Survey data.

The Phase 9/10 analysis project contains copied and checksummed processed CDC WONDER outputs and derived analytic datasets at:

```text
C:\Research\EpilepsyMortalityOptionB
```

Before journal submission, the authors should decide whether to release derived tables and code through a public repository or archive. No repository URL or DOI has been assigned in Phase 11.

## Code availability statement

Reproducible analysis scripts are currently stored in:

```text
C:\Research\EpilepsyMortalityOptionB\src
```

The scripts copy validated WONDER outputs, import covariates, build analytic datasets, run suppression-aware models, generate tables and figures, and produce audit reports. A public code repository or archive should be prepared before journal submission if required by the target journal. No repository URL, accession, or DOI should be listed until it exists.

## AI disclosure statement

Generative AI tools were used to assist with code generation, analysis organization, drafting, editing, and quality-control checks. The authors are responsible for human review, scientific interpretation, verification of results, reference checking, and approval of the final manuscript. No AI-generated text should be submitted without author review and revision.

Author contributions / CRediT: [VERIFY]

Suggested reviewers: [Not provided]
Opposed reviewers: [None provided]
