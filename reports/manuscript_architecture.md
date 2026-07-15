# Manuscript Architecture

Generated: 2026-06-13

## Working Title

Suppression-aware county-level epilepsy and status epilepticus mortality in the United States, 2019-2024

## Structured Abstract Skeleton

- Background: County-level epilepsy/status epilepticus mortality analyses are limited by CDC WONDER suppression of 1-9 death cells.
- Objective: Estimate suppression-aware county-level mortality burden and rurality-associated patterns.
- Methods: MCOD G40/G41 CDC WONDER 2019-2024, county-period and county-year extracts, RUCC/NCHS/SVI/ACS covariates, bias-bounding and interval-likelihood models.
- Results: Report Q001/Q003 totals, suppression profile, rurality model signal, temporal/COVID context, and UCD sensitivity.
- Conclusions: Suppression-aware inference changes the evidentiary basis for county-level rurality-associated mortality claims.

## Introduction Flow

1. Epilepsy/status epilepticus mortality is clinically important.
2. Rural mortality disparities are plausible but hard to quantify.
3. CDC WONDER county suppression creates outcome-dependent visibility bias.
4. This study explicitly models and bounds that suppression while mapping national patterns.

## Methods Outline

- Data sources and CDC WONDER syntax
- Case definition: MCOD ICD-10 G40/G41
- County-period and county-year extraction
- Suppression status definitions
- Covariates and rurality definitions
- SVI composite vs ACS component model families
- Bias-bounding methods
- Interval-likelihood method
- Temporal/COVID analyses
- Mapping/atlas methods

## Results Outline

- Extraction reconciliation and suppression profile
- County characteristics by death status
- Suppression-aware rurality models
- Temporal/urbanization/COVID findings
- UCD sensitivity
- Atlas findings

## Discussion Outline

- Principal findings
- What suppression-aware analysis changes
- Rurality interpretation
- Temporal/COVID context
- Clinical/public-health implications
- Limitations
- Conclusions

## Availability and Statements

- Data/code availability: CDC WONDER outputs and reproducible scripts in this analysis project.
- Ethics: public deidentified aggregate data; no IRB expected, but confirm local policy.
- AI disclosure: disclose Codex-assisted code/report generation if required by target journal.
