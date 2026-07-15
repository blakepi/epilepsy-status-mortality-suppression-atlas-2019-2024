# Supplement

# Supplement Plan

## Supplemental Tables

1. County-year suppression summaries by year and rurality from Q002.
2. Full suppression-bounds model results across rurality-only, SVI composite, and ACS component families.
3. Interval-likelihood negative binomial fit summaries and diagnostics.
4. Component ACS model collinearity diagnostics.
5. Place-of-death by urbanization from Q006.
6. Age-group distribution by urbanization from Q007.
7. Sex distribution by urbanization from Q008.
8. Race and Hispanic-origin descriptive tables from Q009A and Q009B.
9. Underlying-cause county suppression profile from Q014.
10. County merge and unmatched FIPS details, including Connecticut geography caveat.

## Supplemental Figures

1. Observed exact-county multiple-cause mortality rate map.
2. Rural/high-SVI priority map under residual allocation.
3. State-period multiple-cause G40/G41 mortality rate map.
4. County underlying-cause G40/G41 suppression-status map.
5. National-year mortality trend.
6. Additional interval-model diagnostics if retained after human statistical review.

## Supplemental Methods

- Full CDC WONDER query inventory and confirmed cause syntax.
- Suppression interval definitions and scenario algorithms.
- Residual-allocation algorithm.
- Interval-likelihood negative binomial likelihood.
- RUCC, binary RUCC, and NCHS rurality sensitivity definitions.
- SVI composite versus ACS component model rationale.
- Connecticut county/county-equivalent warning and decision not to crosswalk in Phase 9.

## Materials Not Recommended for Main Text

- Race/ethnicity and place-of-death descriptive tables should remain supplemental unless the final journal target requests more descriptive context.
- State-period maps are useful context but are less central than the county suppression atlas.
- UCD county suppression maps support sensitivity interpretation but should not crowd the main suppression-aware MCOD story.


## Table and Figure Legends

# Tables and Figure Legends

## Main-Text Tables

**Table 1. County characteristics by Q001 death-count status.**  
County characteristics are summarized for exact, suppressed_1_9, and explicit zero county-period rows from the Q001 multiple-cause G40/G41 extract, 2019-2024. Columns include county count, person-years, exact deaths, lower and upper death bounds, percent nonmetro, mean SVI, mean poverty, mean uninsurance, and mean percentage age 65 years or older. Suppressed rows are represented as 1-9 deaths and are not treated as zero.

**Table 2. Mortality totals and bounded rates by rurality and SVI category.**  
County-period multiple-cause G40/G41 deaths are summarized by primary collapsed RUCC rurality and SVI quartile. Lower, midpoint, and upper bounds reflect exact, zero, and suppressed county intervals. Rates use 2019-2024 person-years derived from summed Q002 county-year populations.

**Table 3. Suppression-aware rurality and SVI model results.**  
Primary model table showing incidence rate ratios and 95% confidence intervals across observed-only, exact plus zero, suppressed-equals-1, suppressed-equals-5, suppressed-equals-9, population-scaled residual allocation, conservative anti-rural allocation, pro-rural allocation, and interval-likelihood sensitivity scenarios. The key interpretive point is that rurality-associated estimates are suppression-sensitive.

**Table 4. Temporal, urbanization, and COVID co-mention context.**  
National-year and urbanization-year multiple-cause G40/G41 deaths and rates for 2019-2024, with Q010 COVID co-mention context where applicable. County-year suppression summaries may be included in the supplement if the main table becomes too dense.

**Table 5. Underlying-cause sensitivity and UC/MC comparison.**  
Underlying-cause G40/G41 suppression profile and urbanization-year comparison with multiple-cause G40/G41. Phase 10 triage placed this table in the supplement, but it may be retained in the main text if the target journal favors a compact sensitivity table.

## Main-Text Figures

**Figure 1. County multiple-cause G40/G41 death-count status, 2019-2024.**  
Map of county-period death-count status from Q001. Counties are classified as exact, suppressed_1_9, explicit zero, or missing/unmatched. The figure shows the geographic structure of data visibility and highlights why exact-count counties are not the full county universe.

**Figure 2. Suppression-bounds model estimates.**  
Forest plot of incidence rate ratios across suppression scenarios for rurality and SVI terms in the rurality plus SVI composite model family. The nonmetro nonadjacent estimates cross interpretive categories across scenarios, supporting the conclusion that rurality-associated estimates are suppression-sensitive.

**Figure 3. Suppression-aware residual-allocation county mortality rate.**  
Map of one bounded residual-allocation scenario in which the residual deaths between the Q001 total and exact county death sum are distributed across suppressed counties while preserving the 1-9 interval constraint. This map is an illustrative bounded scenario rather than a recovered true county rate.

**Figure 4. Urbanization-year trend and COVID co-mention context.**  
Trend figure showing urbanization-year multiple-cause G40/G41 mortality patterns and COVID co-mention context for 2019-2024. COVID co-mention totaled 1,936 deaths and remained bounded by Q005 urbanization-year totals.

## Supplemental Figures

**Figure S1. Observed exact-county multiple-cause G40/G41 rate.**  
Map restricted to counties with exact death counts. Suppressed counties are not silently included as zero.

**Figure S2. Rural/high-SVI priority map under residual allocation.**  
Map identifying counties classified as nonmetro, high SVI, and high residual-allocation predicted mortality. This is a planning/context display, not a definitive risk map.

**Figure S3. State-period multiple-cause G40/G41 rate.**  
State-level rates using Q015 state-period multiple-cause G40/G41, 2019-2024.

**Figure S4. County underlying-cause G40/G41 death-count status.**  
County-period underlying-cause suppression status from Q014, showing exact, suppressed_1_9, and explicit zero county rows.


## Extraction and Source Trail

See Phase 9/10 reports in the source project for the checksummed extraction source trail. Raw CDC WONDER exports are not included in this submission package.
