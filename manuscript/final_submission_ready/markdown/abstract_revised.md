# Abstract

## Objective

To quantify how CDC WONDER county-level small-cell suppression shapes national county-level analyses of epilepsy/status epilepticus-related mortality and to evaluate rurality-associated patterns using suppression-aware methods.

## Methods

We analyzed CDC WONDER Multiple Cause of Death data for 2019-2024. The primary outcome was multiple-cause mortality with ICD-10 G40 (epilepsy) or G41 (status epilepticus) listed anywhere on the death certificate. County-period and county-year extracts were linked to county rurality, social vulnerability, age-structure, and sex-composition covariates. Suppressed county cells were preserved as 1-9 death intervals and were not treated as zero. Primary county models included standardized county percentages aged >=65 years and male; direct county age standardization was not used because county age-stratified death cells are heavily suppressed. We compared observed-only models with fixed-value stress tests, total-preserving residual allocations, and interval-likelihood negative binomial models.

## Results

National multiple-cause G40/G41 mortality totaled 58,380 deaths. The county-period extract comprised 1,085 counties with exact counts (51,388 deaths), 1,722 suppressed county rows (1-9 deaths each), and 335 explicit-zero rows. The reconciled residual within suppressed counties was 6,992 deaths, or ≈4.1 deaths per suppressed county. In the rurality plus SVI model, nonmetro nonadjacent IRRs were 0.97 for observed exact-positive counties and 0.91 after adding explicit zero counties. The population-scaled residual allocation, treated as the primary total-preserving scenario, estimated an IRR of 1.04, and the interval-likelihood model estimated 1.07 with wide approximate uncertainty. Other total-preserving residual allocations ranged from 0.97 to 1.13. A total-preserving but exposure-ignoring uniform allocation estimated 1.24, showing that the within-suppressed distribution matters; high fixed-value stress tests were interpreted as non-primary stress tests. COVID-19 co-mention totaled 1,936 deaths, and underlying-cause G40/G41 mortality totaled 22,306 deaths.

## Conclusion

County-level epilepsy/status epilepticus mortality inference in CDC WONDER is strongly shaped by outcome-dependent suppression. Preserving suppressed cells as intervals, reconciling county extracts to aggregate totals, and separating total-preserving allocations from fixed-value stress tests provide a more transparent framework for county-level mortality surveillance.
