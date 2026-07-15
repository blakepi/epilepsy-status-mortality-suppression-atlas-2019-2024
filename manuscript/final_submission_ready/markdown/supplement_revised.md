# Supplementary Material

Manuscript: Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024

## Supplementary methods

This supplement accompanies the revised editorial-review package. The analysis uses the same frozen, reconciled CDC WONDER aggregate outputs and county covariate inputs as the prior package; CDC WONDER was not re-queried. The revision adds a constant-mean suppression stress test and reorganizes the scenario interpretation around reconciliation to the known county-period total.

This supplement is intended to be self-contained for editorial review. It embeds the full model table, interval-likelihood results, VIF diagnostics, descriptive age/sex/race/place-of-death context, county-year suppression profile, underlying-cause sensitivity profile, merge exceptions, and Connecticut geography note. Repository and archive links provide reproducibility materials, but the key tables and figures needed to interpret the manuscript are included below.

## Supplementary tables

## Table S1. County-year suppression profile by rurality

| Year | Primary Rurality | Death Status | Rows | Lower | Upper | Population |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | metro_large | exact | 115 | 3,008 | 3,008 | 140,748,867 |
| 2019 | metro_large | suppressed_1_9 | 231 | 231 | 2,079 | 41,234,422 |
| 2019 | metro_large | zero | 95 | 0 | 0 | 3,445,923 |
| 2019 | metro_other | exact | 53 | 815 | 815 | 25,046,886 |
| 2019 | metro_other | suppressed_1_9 | 475 | 475 | 4,275 | 61,771,174 |
| 2019 | metro_other | zero | 210 | 0 | 0 | 6,738,663 |
| 2019 | nonmetro_adjacent | exact | 1 | 13 | 13 | 82,124 |
| 2019 | nonmetro_adjacent | suppressed_1_9 | 501 | 501 | 4,509 | 20,241,430 |
| 2019 | nonmetro_adjacent | zero | 542 | 0 | 0 | 10,576,320 |
| 2019 | nonmetro_nonadjacent | suppressed_1_9 | 281 | 281 | 2,529 | 7,866,886 |
| 2019 | nonmetro_nonadjacent | zero | 627 | 0 | 0 | 6,889,848 |
| 2019 |  | exact | 3 | 55 | 55 | 2,689,809 |
| 2019 |  | suppressed_1_9 | 6 | 6 | 54 | 889,655 |
| 2019 |  | zero | 2 | 0 | 0 | 17,516 |
| 2020 | metro_large | exact | 118 | 3,770 | 3,770 | 143,387,980 |
| 2020 | metro_large | suppressed_1_9 | 242 | 242 | 2,178 | 39,902,579 |
| 2020 | metro_large | zero | 81 | 0 | 0 | 2,887,333 |
| 2020 | metro_other | exact | 82 | 1,233 | 1,233 | 34,971,655 |
| 2020 | metro_other | suppressed_1_9 | 472 | 472 | 4,248 | 53,147,585 |
| 2020 | metro_other | zero | 184 | 0 | 0 | 5,974,950 |
| 2020 | nonmetro_adjacent | exact | 2 | 25 | 25 | 146,665 |
| 2020 | nonmetro_adjacent | suppressed_1_9 | 549 | 549 | 4,941 | 21,356,660 |
| 2020 | nonmetro_adjacent | zero | 493 | 0 | 0 | 9,395,324 |
| 2020 | nonmetro_nonadjacent | exact | 2 | 23 | 23 | 151,244 |
| 2020 | nonmetro_nonadjacent | suppressed_1_9 | 328 | 328 | 2,952 | 8,686,768 |
| 2020 | nonmetro_nonadjacent | zero | 578 | 0 | 0 | 5,886,630 |
| 2020 |  | exact | 3 | 53 | 53 | 2,683,600 |
| 2020 |  | suppressed_1_9 | 6 | 6 | 54 | 774,540 |
| 2020 |  | zero | 2 | 0 | 0 | 130,610 |
| 2021 | metro_large | exact | 132 | 3,991 | 3,991 | 148,791,213 |
| 2021 | metro_large | suppressed_1_9 | 238 | 238 | 2,142 | 36,282,209 |
| 2021 | metro_large | zero | 71 | 0 | 0 | 2,529,831 |
| 2021 | metro_other | exact | 91 | 1,493 | 1,493 | 37,431,856 |
| 2021 | metro_other | suppressed_1_9 | 467 | 467 | 4,203 | 52,714,629 |
| 2021 | metro_other | zero | 180 | 0 | 0 | 4,869,246 |
| 2021 | nonmetro_adjacent | exact | 3 | 30 | 30 | 276,513 |
| 2021 | nonmetro_adjacent | suppressed_1_9 | 582 | 582 | 5,238 | 22,660,154 |
| 2021 | nonmetro_adjacent | zero | 459 | 0 | 0 | 7,978,187 |
| 2021 | nonmetro_nonadjacent | suppressed_1_9 | 314 | 314 | 2,826 | 8,612,535 |
| 2021 | nonmetro_nonadjacent | zero | 594 | 0 | 0 | 6,110,258 |
| 2021 |  | exact | 3 | 69 | 69 | 2,720,322 |
| 2021 |  | suppressed_1_9 | 7 | 7 | 63 | 907,221 |
| 2021 |  | zero | 1 | 0 | 0 | 9,571 |
| 2022 | metro_large | exact | 129 | 4,360 | 4,360 | 147,698,381 |
| 2022 | metro_large | suppressed_1_9 | 258 | 258 | 2,322 | 38,503,928 |
| 2022 | metro_large | zero | 54 | 0 | 0 | 2,063,361 |
| 2022 | metro_other | exact | 95 | 1,596 | 1,596 | 38,699,288 |
| 2022 | metro_other | suppressed_1_9 | 482 | 482 | 4,338 | 53,486,945 |
| 2022 | metro_other | zero | 161 | 0 | 0 | 3,517,720 |
| 2022 | nonmetro_adjacent | suppressed_1_9 | 604 | 604 | 5,436 | 23,459,545 |
| 2022 | nonmetro_adjacent | zero | 440 | 0 | 0 | 7,502,160 |
| 2022 | nonmetro_nonadjacent | exact | 1 | 10 | 10 | 82,959 |
| 2022 | nonmetro_nonadjacent | suppressed_1_9 | 351 | 351 | 3,159 | 9,055,408 |
| 2022 | nonmetro_nonadjacent | zero | 556 | 0 | 0 | 5,560,397 |
| 2022 |  | exact | 3 | 72 | 72 | 0 |
| 2022 |  | suppressed_1_9 | 6 | 6 | 54 | 22,982 |
| 2022 |  | zero | 2 | 0 | 0 | 8,278 |
| 2023 | metro_large | exact | 135 | 4,285 | 4,285 | 150,582,340 |
| 2023 | metro_large | suppressed_1_9 | 233 | 233 | 2,097 | 36,032,252 |
| 2023 | metro_large | zero | 73 | 0 | 0 | 2,536,487 |
| 2023 | metro_other | exact | 110 | 1,762 | 1,762 | 42,752,551 |
| 2023 | metro_other | suppressed_1_9 | 464 | 464 | 4,176 | 49,559,549 |
| 2023 | metro_other | zero | 164 | 0 | 0 | 4,040,327 |
| 2023 | nonmetro_adjacent | exact | 3 | 33 | 33 | 315,073 |
| 2023 | nonmetro_adjacent | suppressed_1_9 | 607 | 607 | 5,463 | 23,062,675 |
| 2023 | nonmetro_adjacent | zero | 434 | 0 | 0 | 7,686,701 |
| 2023 | nonmetro_nonadjacent | exact | 1 | 14 | 14 | 66,127 |
| 2023 | nonmetro_nonadjacent | suppressed_1_9 | 347 | 347 | 3,123 | 9,139,814 |
| 2023 | nonmetro_nonadjacent | zero | 560 | 0 | 0 | 5,492,945 |
| 2023 |  | exact | 3 | 85 | 85 | 0 |
| 2023 |  | suppressed_1_9 | 6 | 6 | 54 | 8,001 |
| 2023 |  | zero | 2 | 0 | 0 | 22,877 |
| 2024 | metro_large | exact | 139 | 4,440 | 4,440 | 156,893,458 |
| 2024 | metro_large | suppressed_1_9 | 243 | 243 | 2,187 | 34,039,633 |
| 2024 | metro_large | zero | 59 | 0 | 0 | 1,895,305 |
| 2024 | metro_other | exact | 113 | 1,812 | 1,812 | 44,210,601 |
| 2024 | metro_other | suppressed_1_9 | 461 | 461 | 4,149 | 49,397,283 |
| 2024 | metro_other | zero | 164 | 0 | 0 | 3,985,074 |
| 2024 | nonmetro_adjacent | exact | 5 | 58 | 58 | 693,171 |
| 2024 | nonmetro_adjacent | suppressed_1_9 | 596 | 596 | 5,364 | 22,869,666 |
| 2024 | nonmetro_adjacent | zero | 443 | 0 | 0 | 7,682,746 |
| 2024 | nonmetro_nonadjacent | exact | 1 | 12 | 12 | 66,410 |
| 2024 | nonmetro_nonadjacent | suppressed_1_9 | 332 | 332 | 2,988 | 8,716,130 |
| 2024 | nonmetro_nonadjacent | zero | 575 | 0 | 0 | 5,955,901 |
| 2024 |  | exact | 4 | 100 | 100 | 0 |
| 2024 |  | suppressed_1_9 | 6 | 6 | 54 | 21,306 |
| 2024 |  | zero | 1 | 0 | 0 | 9,235 |

Note. County-year rows preserve exact, suppressed, and zero death-count statuses.
## Table S2. Full suppression-aware model results

| Scenario | Model Family | Model Type | Term | Irr | Ci Low | Ci High | P Value | N Rows | Events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| observed_exact_positive_only | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.942 | 0.864 | 1.026 | 0.169 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.877 | 0.790 | 0.974 | 0.014 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.905 | 0.769 | 1.065 | 0.231 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.146 | 1.105 | 1.189 | 0.000 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.012 | 0.981 | 1.044 | 0.459 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.985 | 0.869 | 1.117 | 0.812 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.936 | 0.812 | 1.078 | 0.356 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.974 | 0.799 | 1.189 | 0.798 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 0.960 | 0.818 | 1.128 | 0.624 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 0.975 | 0.860 | 1.105 | 0.689 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 0.862 | 0.750 | 0.990 | 0.036 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.144 | 1.103 | 1.186 | 0.000 | 1,077 | 50,833 |
| observed_exact_positive_only | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.012 | 0.980 | 1.045 | 0.458 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.950 | 0.878 | 1.027 | 0.198 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.893 | 0.817 | 0.975 | 0.011 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.978 | 0.816 | 1.173 | 0.813 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 0.982 | 0.938 | 1.027 | 0.424 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.831 | 0.796 | 0.868 | 0.000 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 0.895 | 0.860 | 0.931 | 0.000 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 0.992 | 0.961 | 1.023 | 0.598 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 0.998 | 0.970 | 1.027 | 0.891 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 0.915 | 0.886 | 0.946 | 0.000 | 1,077 | 50,833 |
| observed_exact_positive_only | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.077 | 1.042 | 1.113 | 0.000 | 1,077 | 50,833 |
| observed_exact_plus_zero | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.932 | 0.849 | 1.022 | 0.135 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.776 | 0.692 | 0.870 | 0.000 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.912 | 0.799 | 1.041 | 0.173 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 0.984 | 0.947 | 1.022 | 0.394 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.817 | 0.762 | 0.876 | 0.000 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.915 | 0.812 | 1.031 | 0.144 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.766 | 0.662 | 0.886 | 0.000 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.908 | 0.777 | 1.062 | 0.227 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 0.982 | 0.861 | 1.119 | 0.783 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 1.045 | 0.910 | 1.200 | 0.534 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 1.024 | 0.885 | 1.184 | 0.753 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 0.984 | 0.947 | 1.022 | 0.399 | 1,412 | 50,833 |
| observed_exact_plus_zero | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.817 | 0.763 | 0.875 | 0.000 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.936 | 0.855 | 1.024 | 0.147 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.809 | 0.724 | 0.905 | 0.000 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.936 | 0.830 | 1.056 | 0.281 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 1.065 | 0.992 | 1.144 | 0.080 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.890 | 0.844 | 0.938 | 0.000 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 0.967 | 0.907 | 1.030 | 0.299 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 0.931 | 0.887 | 0.977 | 0.004 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 1.053 | 1.017 | 1.090 | 0.003 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 0.978 | 0.938 | 1.021 | 0.311 | 1,412 | 50,833 |
| observed_exact_plus_zero | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 0.966 | 0.926 | 1.007 | 0.099 | 1,412 | 50,833 |
| suppressed_equals_1 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.039 | 0.934 | 1.156 | 0.484 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.008 | 0.909 | 1.118 | 0.876 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.999 | 0.897 | 1.112 | 0.984 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 0.960 | 0.929 | 0.991 | 0.011 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.855 | 0.816 | 0.895 | 0.000 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.028 | 0.924 | 1.143 | 0.615 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.988 | 0.891 | 1.096 | 0.825 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.985 | 0.884 | 1.096 | 0.776 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 1.032 | 0.940 | 1.133 | 0.513 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 1.050 | 0.955 | 1.153 | 0.312 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 1.114 | 1.014 | 1.225 | 0.025 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 0.962 | 0.932 | 0.993 | 0.016 | 3,131 | 52,552 |
| suppressed_equals_1 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.859 | 0.820 | 0.900 | 0.000 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.031 | 0.925 | 1.149 | 0.582 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.003 | 0.903 | 1.113 | 0.960 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.965 | 0.866 | 1.075 | 0.520 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 1.065 | 1.003 | 1.132 | 0.040 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.953 | 0.910 | 0.998 | 0.041 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 1.170 | 1.107 | 1.238 | 0.000 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 0.983 | 0.942 | 1.025 | 0.419 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 1.122 | 1.079 | 1.167 | 0.000 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 1.134 | 1.090 | 1.180 | 0.000 | 3,131 | 52,552 |
| suppressed_equals_1 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 0.983 | 0.947 | 1.020 | 0.354 | 3,131 | 52,552 |
| suppressed_equals_mean_4_06 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.100 | 1.013 | 1.195 | 0.023 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.143 | 1.055 | 1.238 | 0.001 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.248 | 1.145 | 1.360 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.214 | 1.173 | 1.257 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.080 | 1.038 | 1.123 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.097 | 1.010 | 1.193 | 0.028 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.136 | 1.048 | 1.232 | 0.002 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.243 | 1.140 | 1.355 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 0.937 | 0.865 | 1.016 | 0.115 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 0.997 | 0.917 | 1.084 | 0.945 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 1.011 | 0.932 | 1.097 | 0.791 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.215 | 1.174 | 1.259 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.080 | 1.038 | 1.124 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.050 | 0.972 | 1.135 | 0.212 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.088 | 1.009 | 1.174 | 0.029 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.201 | 1.105 | 1.306 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 1.014 | 0.956 | 1.074 | 0.649 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.864 | 0.824 | 0.906 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 1.030 | 0.977 | 1.086 | 0.272 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 1.070 | 1.028 | 1.114 | 0.001 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 1.010 | 0.982 | 1.039 | 0.477 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 1.041 | 1.005 | 1.079 | 0.025 | 3,131 | 57,813 |
| suppressed_equals_mean_4_06 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.192 | 1.147 | 1.239 | 0.000 | 3,131 | 57,813 |
| suppressed_equals_5 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.110 | 1.018 | 1.210 | 0.019 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.167 | 1.073 | 1.270 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.294 | 1.182 | 1.417 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.259 | 1.212 | 1.307 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.110 | 1.065 | 1.156 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.109 | 1.016 | 1.211 | 0.021 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.163 | 1.067 | 1.267 | 0.001 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.291 | 1.178 | 1.415 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 0.922 | 0.846 | 1.004 | 0.062 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 0.988 | 0.903 | 1.081 | 0.790 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 0.995 | 0.912 | 1.086 | 0.917 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.259 | 1.213 | 1.308 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.110 | 1.065 | 1.157 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.054 | 0.972 | 1.142 | 0.203 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.103 | 1.019 | 1.194 | 0.016 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.244 | 1.139 | 1.359 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 1.004 | 0.945 | 1.068 | 0.887 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.847 | 0.804 | 0.891 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 1.013 | 0.957 | 1.072 | 0.663 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 1.087 | 1.041 | 1.136 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 0.992 | 0.963 | 1.022 | 0.588 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 1.027 | 0.989 | 1.067 | 0.164 | 3,131 | 59,428 |
| suppressed_equals_5 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.229 | 1.179 | 1.281 | 0.000 | 3,131 | 59,428 |
| suppressed_equals_9 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.133 | 1.013 | 1.267 | 0.029 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.232 | 1.106 | 1.373 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.420 | 1.265 | 1.594 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.372 | 1.307 | 1.439 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.180 | 1.126 | 1.238 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.137 | 1.015 | 1.274 | 0.026 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.234 | 1.105 | 1.378 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.423 | 1.266 | 1.598 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 0.879 | 0.789 | 0.978 | 0.018 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 0.964 | 0.860 | 1.081 | 0.530 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 0.955 | 0.856 | 1.067 | 0.418 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.370 | 1.306 | 1.437 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.180 | 1.125 | 1.238 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.063 | 0.960 | 1.177 | 0.240 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.140 | 1.033 | 1.259 | 0.009 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.359 | 1.217 | 1.517 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 0.979 | 0.912 | 1.052 | 0.566 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.797 | 0.747 | 0.850 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 0.974 | 0.910 | 1.043 | 0.449 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 1.136 | 1.077 | 1.198 | 0.000 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 0.944 | 0.911 | 0.978 | 0.001 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 0.992 | 0.947 | 1.040 | 0.742 | 3,131 | 66,304 |
| suppressed_equals_9 | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.326 | 1.260 | 1.395 | 0.000 | 3,131 | 66,304 |
| population_scaled_residual_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.024 | 0.968 | 1.084 | 0.402 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.036 | 0.982 | 1.092 | 0.193 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.045 | 0.988 | 1.105 | 0.122 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.053 | 1.033 | 1.073 | 0.000 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.977 | 0.954 | 1.001 | 0.063 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.017 | 0.962 | 1.076 | 0.555 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.025 | 0.971 | 1.081 | 0.373 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.037 | 0.981 | 1.096 | 0.203 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 1.009 | 0.962 | 1.059 | 0.717 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 1.025 | 0.975 | 1.077 | 0.332 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 1.062 | 1.011 | 1.116 | 0.016 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.055 | 1.035 | 1.075 | 0.000 | 3,131 | 57,817 |
| population_scaled_residual_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.979 | 0.956 | 1.004 | 0.094 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.994 | 0.943 | 1.048 | 0.819 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.003 | 0.954 | 1.054 | 0.913 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.008 | 0.956 | 1.062 | 0.768 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 1.001 | 0.971 | 1.033 | 0.928 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.889 | 0.865 | 0.914 | 0.000 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 1.016 | 0.988 | 1.044 | 0.268 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 1.003 | 0.981 | 1.026 | 0.779 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 1.025 | 1.004 | 1.045 | 0.017 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 1.013 | 0.993 | 1.032 | 0.206 | 3,131 | 57,817 |
| population_scaled_residual_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.030 | 1.009 | 1.051 | 0.004 | 3,131 | 57,817 |
| conservative_anti_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.023 | 0.950 | 1.101 | 0.550 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.006 | 0.939 | 1.078 | 0.872 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.976 | 0.908 | 1.049 | 0.509 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.030 | 1.005 | 1.055 | 0.017 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.967 | 0.935 | 1.000 | 0.049 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.012 | 0.940 | 1.089 | 0.758 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.992 | 0.925 | 1.064 | 0.821 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.966 | 0.899 | 1.038 | 0.346 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 1.046 | 0.981 | 1.117 | 0.171 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 1.050 | 0.983 | 1.122 | 0.147 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 1.088 | 1.019 | 1.162 | 0.011 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.033 | 1.008 | 1.058 | 0.009 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 0.970 | 0.937 | 1.003 | 0.073 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 0.998 | 0.929 | 1.072 | 0.951 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 0.988 | 0.923 | 1.056 | 0.717 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 0.963 | 0.898 | 1.034 | 0.301 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 0.962 | 0.922 | 1.003 | 0.070 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.926 | 0.891 | 0.964 | 0.000 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 0.986 | 0.949 | 1.023 | 0.450 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 0.999 | 0.969 | 1.029 | 0.934 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 1.062 | 1.035 | 1.089 | 0.000 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 0.964 | 0.939 | 0.989 | 0.006 | 3,131 | 57,812 |
| conservative_anti_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.015 | 0.987 | 1.044 | 0.295 | 3,131 | 57,812 |
| pro_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.062 | 0.994 | 1.135 | 0.075 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.091 | 1.024 | 1.161 | 0.007 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.132 | 1.061 | 1.209 | 0.000 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.097 | 1.074 | 1.120 | 0.000 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_only | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.001 | 0.975 | 1.027 | 0.951 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.056 | 0.988 | 1.129 | 0.106 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.080 | 1.014 | 1.151 | 0.017 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.125 | 1.054 | 1.201 | 0.000 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q2 | 0.986 | 0.933 | 1.042 | 0.617 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q3 | 1.011 | 0.956 | 1.069 | 0.703 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | svi_quartile_Q4_highest | 1.049 | 0.992 | 1.109 | 0.091 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.099 | 1.076 | 1.122 | 0.000 | 3,131 | 57,819 |
| pro_rural_allocation | rurality_svi_composite | GLM_negative_binomial_alpha1_robust | acs_pct_male_z | 1.003 | 0.977 | 1.029 | 0.847 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_metro_other | 1.021 | 0.959 | 1.086 | 0.521 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_adjacent | 1.040 | 0.981 | 1.104 | 0.189 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | primary_rurality_nonmetro_nonadjacent | 1.075 | 1.012 | 1.143 | 0.019 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_poverty_z | 1.022 | 0.987 | 1.058 | 0.219 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_median_household_income_z | 0.855 | 0.828 | 0.882 | 0.000 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_high_school_grad_or_higher_z | 1.020 | 0.990 | 1.051 | 0.200 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_uninsured_z | 1.013 | 0.989 | 1.038 | 0.291 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_non_hispanic_black_z | 1.000 | 0.979 | 1.022 | 0.978 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_hispanic_z | 1.035 | 1.013 | 1.058 | 0.002 | 3,131 | 57,819 |
| pro_rural_allocation | acs_component_family | GLM_negative_binomial_alpha1_robust | acs_pct_age_65_plus_z | 1.064 | 1.041 | 1.089 | 0.000 | 3,131 | 57,819 |
| interval_likelihood | interval_nb_rurality_only | interval_likelihood_negative_binomial | primary_rurality_metro_other | 1.062 | 0.523 | 2.158 |  | 3,131 |  |
| interval_likelihood | interval_nb_rurality_only | interval_likelihood_negative_binomial | primary_rurality_nonmetro_adjacent | 1.042 | 0.719 | 1.512 |  | 3,131 |  |
| interval_likelihood | interval_nb_rurality_only | interval_likelihood_negative_binomial | primary_rurality_nonmetro_nonadjacent | 1.078 | 0.618 | 1.879 |  | 3,131 |  |
| interval_likelihood | interval_nb_rurality_svi | interval_likelihood_negative_binomial | primary_rurality_metro_other | 1.053 | 0.458 | 2.424 |  | 3,131 |  |
| interval_likelihood | interval_nb_rurality_svi | interval_likelihood_negative_binomial | primary_rurality_nonmetro_adjacent | 1.027 | 0.473 | 2.233 |  | 3,131 |  |
| interval_likelihood | interval_nb_rurality_svi | interval_likelihood_negative_binomial | primary_rurality_nonmetro_nonadjacent | 1.068 | 0.634 | 1.798 |  | 3,131 |  |
| interval_likelihood | interval_nb_rurality_svi | interval_likelihood_negative_binomial | svi_quartile_Q4_highest | 1.077 | 0.460 | 2.526 |  | 3,131 |  |

Note. Includes all scenario, family, and term rows used to support main Table 3.
## Table S3. Interval-likelihood model estimates

| Model Family | Term | Coef | Se Approx | Irr | Ci Low Approx | Ci High Approx | N Rows | Interval Log Likelihood | Converged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| interval_nb_rurality_only | primary_rurality_metro_other | 0.060 | 0.362 | 1.062 | 0.523 | 2.158 | 3,131 | -5,172 | 1 |
| interval_nb_rurality_only | primary_rurality_nonmetro_adjacent | 0.042 | 0.190 | 1.042 | 0.719 | 1.512 | 3,131 | -5,172 | 1 |
| interval_nb_rurality_only | primary_rurality_nonmetro_nonadjacent | 0.075 | 0.284 | 1.078 | 0.618 | 1.879 | 3,131 | -5,172 | 1 |
| interval_nb_rurality_svi | primary_rurality_metro_other | 0.052 | 0.425 | 1.053 | 0.458 | 2.424 | 3,131 | -5,169 | 1 |
| interval_nb_rurality_svi | primary_rurality_nonmetro_adjacent | 0.027 | 0.396 | 1.027 | 0.473 | 2.233 | 3,131 | -5,169 | 1 |
| interval_nb_rurality_svi | primary_rurality_nonmetro_nonadjacent | 0.065 | 0.266 | 1.068 | 0.634 | 1.798 | 3,131 | -5,169 | 1 |
| interval_nb_rurality_svi | svi_quartile_Q2 | 0.030 | 0.866 | 1.030 | 0.189 | 5.622 | 3,131 | -5,169 | 1 |
| interval_nb_rurality_svi | svi_quartile_Q3 | 0.042 | 0.457 | 1.043 | 0.426 | 2.555 | 3,131 | -5,169 | 1 |
| interval_nb_rurality_svi | svi_quartile_Q4_highest | 0.075 | 0.435 | 1.077 | 0.460 | 2.526 | 3,131 | -5,169 | 1 |

Note. Approximate confidence intervals use optimizer inverse-Hessian estimates; suppressed rows contribute interval probabilities.
## Table S4. Component-model VIF diagnostics

| Variable | Vif | R Squared | N |
| --- | --- | --- | --- |
| acs_pct_poverty | 2.912 | 0.657 | 3,129 |
| acs_median_household_income | 2.916 | 0.657 | 3,129 |
| acs_pct_high_school_grad_or_higher | 2.391 | 0.582 | 3,129 |
| acs_pct_uninsured | 1.547 | 0.354 | 3,129 |
| acs_pct_non_hispanic_black | 1.345 | 0.257 | 3,129 |
| acs_pct_hispanic | 1.631 | 0.387 | 3,129 |
| acs_pct_age_65_plus | 1.367 | 0.269 | 3,129 |

Note. Maximum VIF was approximately 2.92 for median household income/poverty-related component diagnostics.
## Table S5. Place of death by urbanization

| Table | Urbanization | Place Of Death | Death Count Status | Rows | Lower | Upper |
| --- | --- | --- | --- | --- | --- | --- |
| place of death by urbanization | Large Central Metro | Decedent's home | exact | 1 | 4,880 | 4,880 |
| place of death by urbanization | Large Central Metro | Hospice facility | exact | 1 | 788 | 788 |
| place of death by urbanization | Large Central Metro | Medical Facility - Dead on Arrival | exact | 1 | 18 | 18 |
| place of death by urbanization | Large Central Metro | Medical Facility - Inpatient | exact | 1 | 7,321 | 7,321 |
| place of death by urbanization | Large Central Metro | Medical Facility - Outpatient or ER | exact | 1 | 1,043 | 1,043 |
| place of death by urbanization | Large Central Metro | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Large Central Metro | Nursing home/long term care | exact | 1 | 1,747 | 1,747 |
| place of death by urbanization | Large Central Metro | Other | exact | 1 | 821 | 821 |
| place of death by urbanization | Large Central Metro | Place of death unknown | suppressed_1_9 | 1 | 1 | 9 |
| place of death by urbanization | Large Fringe Metro | Decedent's home | exact | 1 | 3,252 | 3,252 |
| place of death by urbanization | Large Fringe Metro | Hospice facility | exact | 1 | 834 | 834 |
| place of death by urbanization | Large Fringe Metro | Medical Facility - Dead on Arrival | exact | 1 | 38 | 38 |
| place of death by urbanization | Large Fringe Metro | Medical Facility - Inpatient | exact | 1 | 5,185 | 5,185 |
| place of death by urbanization | Large Fringe Metro | Medical Facility - Outpatient or ER | exact | 1 | 673 | 673 |
| place of death by urbanization | Large Fringe Metro | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Large Fringe Metro | Nursing home/long term care | exact | 1 | 1,479 | 1,479 |
| place of death by urbanization | Large Fringe Metro | Other | exact | 1 | 541 | 541 |
| place of death by urbanization | Large Fringe Metro | Place of death unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Medium Metro | Decedent's home | exact | 1 | 3,830 | 3,830 |
| place of death by urbanization | Medium Metro | Hospice facility | exact | 1 | 895 | 895 |
| place of death by urbanization | Medium Metro | Medical Facility - Dead on Arrival | exact | 1 | 19 | 19 |
| place of death by urbanization | Medium Metro | Medical Facility - Inpatient | exact | 1 | 5,148 | 5,148 |
| place of death by urbanization | Medium Metro | Medical Facility - Outpatient or ER | exact | 1 | 612 | 612 |
| place of death by urbanization | Medium Metro | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Medium Metro | Nursing home/long term care | exact | 1 | 1,853 | 1,853 |
| place of death by urbanization | Medium Metro | Other | exact | 1 | 640 | 640 |
| place of death by urbanization | Medium Metro | Place of death unknown | suppressed_1_9 | 1 | 1 | 9 |
| place of death by urbanization | Micropolitan (Nonmetro) | Decedent's home | exact | 1 | 1,820 | 1,820 |
| place of death by urbanization | Micropolitan (Nonmetro) | Hospice facility | exact | 1 | 318 | 318 |
| place of death by urbanization | Micropolitan (Nonmetro) | Medical Facility - Dead on Arrival | exact | 1 | 29 | 29 |
| place of death by urbanization | Micropolitan (Nonmetro) | Medical Facility - Inpatient | exact | 1 | 2,330 | 2,330 |
| place of death by urbanization | Micropolitan (Nonmetro) | Medical Facility - Outpatient or ER | exact | 1 | 351 | 351 |
| place of death by urbanization | Micropolitan (Nonmetro) | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Micropolitan (Nonmetro) | Nursing home/long term care | exact | 1 | 1,121 | 1,121 |
| place of death by urbanization | Micropolitan (Nonmetro) | Other | exact | 1 | 279 | 279 |
| place of death by urbanization | Micropolitan (Nonmetro) | Place of death unknown | suppressed_1_9 | 1 | 1 | 9 |
| place of death by urbanization | NonCore (Nonmetro) | Decedent's home | exact | 1 | 1,205 | 1,205 |
| place of death by urbanization | NonCore (Nonmetro) | Hospice facility | exact | 1 | 159 | 159 |
| place of death by urbanization | NonCore (Nonmetro) | Medical Facility - Dead on Arrival | exact | 1 | 16 | 16 |
| place of death by urbanization | NonCore (Nonmetro) | Medical Facility - Inpatient | exact | 1 | 1,638 | 1,638 |
| place of death by urbanization | NonCore (Nonmetro) | Medical Facility - Outpatient or ER | exact | 1 | 291 | 291 |
| place of death by urbanization | NonCore (Nonmetro) | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | NonCore (Nonmetro) | Nursing home/long term care | exact | 1 | 723 | 723 |
| place of death by urbanization | NonCore (Nonmetro) | Other | exact | 1 | 177 | 177 |
| place of death by urbanization | NonCore (Nonmetro) | Place of death unknown | suppressed_1_9 | 1 | 1 | 9 |
| place of death by urbanization | Not Available | Decedent's home | exact | 1 | 88 | 88 |
| place of death by urbanization | Not Available | Hospice facility | exact | 1 | 22 | 22 |
| place of death by urbanization | Not Available | Medical Facility - Dead on Arrival | suppressed_1_9 | 1 | 1 | 9 |
| place of death by urbanization | Not Available | Medical Facility - Inpatient | exact | 1 | 313 | 313 |
| place of death by urbanization | Not Available | Medical Facility - Outpatient or ER | exact | 1 | 24 | 24 |
| place of death by urbanization | Not Available | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Not Available | Nursing home/long term care | exact | 1 | 88 | 88 |
| place of death by urbanization | Not Available | Other | exact | 1 | 17 | 17 |
| place of death by urbanization | Not Available | Place of death unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Small Metro | Decedent's home | exact | 1 | 1,715 | 1,715 |
| place of death by urbanization | Small Metro | Hospice facility | exact | 1 | 382 | 382 |
| place of death by urbanization | Small Metro | Medical Facility - Dead on Arrival | suppressed_1_9 | 1 | 1 | 9 |
| place of death by urbanization | Small Metro | Medical Facility - Inpatient | exact | 1 | 2,211 | 2,211 |
| place of death by urbanization | Small Metro | Medical Facility - Outpatient or ER | exact | 1 | 284 | 284 |
| place of death by urbanization | Small Metro | Medical Facility - Status unknown | zero | 1 | 0 | 0 |
| place of death by urbanization | Small Metro | Nursing home/long term care | exact | 1 | 877 | 877 |
| place of death by urbanization | Small Metro | Other | exact | 1 | 269 | 269 |
| place of death by urbanization | Small Metro | Place of death unknown | zero | 1 | 0 | 0 |

Note. Descriptive place-of-death context is aggregate and subject to WONDER suppression.
## Table S6. Age group by urbanization

| Table | Urbanization | Age Group | Death Count Status | Rows | Lower | Upper |
| --- | --- | --- | --- | --- | --- | --- |
| age group by urbanization | Large Central Metro | 1-4 years | exact | 1 | 203 | 203 |
| age group by urbanization | Large Central Metro | 15-24 years | exact | 1 | 954 | 954 |
| age group by urbanization | Large Central Metro | 25-34 years | exact | 1 | 1,217 | 1,217 |
| age group by urbanization | Large Central Metro | 35-44 years | exact | 1 | 1,226 | 1,226 |
| age group by urbanization | Large Central Metro | 45-54 years | exact | 1 | 1,593 | 1,593 |
| age group by urbanization | Large Central Metro | 5-14 years | exact | 1 | 489 | 489 |
| age group by urbanization | Large Central Metro | 55-64 years | exact | 1 | 2,688 | 2,688 |
| age group by urbanization | Large Central Metro | 65-74 years | exact | 1 | 3,511 | 3,511 |
| age group by urbanization | Large Central Metro | 75-84 years | exact | 1 | 2,743 | 2,743 |
| age group by urbanization | Large Central Metro | 85+ years | exact | 1 | 1,854 | 1,854 |
| age group by urbanization | Large Central Metro | < 1 year | exact | 1 | 143 | 143 |
| age group by urbanization | Large Central Metro | Not Stated | zero | 1 | 0 | 0 |
| age group by urbanization | Large Fringe Metro | 1-4 years | exact | 1 | 156 | 156 |
| age group by urbanization | Large Fringe Metro | 15-24 years | exact | 1 | 637 | 637 |
| age group by urbanization | Large Fringe Metro | 25-34 years | exact | 1 | 740 | 740 |
| age group by urbanization | Large Fringe Metro | 35-44 years | exact | 1 | 790 | 790 |
| age group by urbanization | Large Fringe Metro | 45-54 years | exact | 1 | 995 | 995 |
| age group by urbanization | Large Fringe Metro | 5-14 years | exact | 1 | 332 | 332 |
| age group by urbanization | Large Fringe Metro | 55-64 years | exact | 1 | 1,933 | 1,933 |
| age group by urbanization | Large Fringe Metro | 65-74 years | exact | 1 | 2,578 | 2,578 |
| age group by urbanization | Large Fringe Metro | 75-84 years | exact | 1 | 2,246 | 2,246 |
| age group by urbanization | Large Fringe Metro | 85+ years | exact | 1 | 1,501 | 1,501 |
| age group by urbanization | Large Fringe Metro | < 1 year | exact | 1 | 94 | 94 |
| age group by urbanization | Large Fringe Metro | Not Stated | zero | 1 | 0 | 0 |
| age group by urbanization | Medium Metro | 1-4 years | exact | 1 | 140 | 140 |
| age group by urbanization | Medium Metro | 15-24 years | exact | 1 | 600 | 600 |
| age group by urbanization | Medium Metro | 25-34 years | exact | 1 | 782 | 782 |
| age group by urbanization | Medium Metro | 35-44 years | exact | 1 | 878 | 878 |
| age group by urbanization | Medium Metro | 45-54 years | exact | 1 | 1,177 | 1,177 |
| age group by urbanization | Medium Metro | 5-14 years | exact | 1 | 337 | 337 |
| age group by urbanization | Medium Metro | 55-64 years | exact | 1 | 2,251 | 2,251 |
| age group by urbanization | Medium Metro | 65-74 years | exact | 1 | 2,762 | 2,762 |
| age group by urbanization | Medium Metro | 75-84 years | exact | 1 | 2,458 | 2,458 |
| age group by urbanization | Medium Metro | 85+ years | exact | 1 | 1,524 | 1,524 |
| age group by urbanization | Medium Metro | < 1 year | exact | 1 | 88 | 88 |
| age group by urbanization | Medium Metro | Not Stated | suppressed_1_9 | 1 | 1 | 9 |
| age group by urbanization | Micropolitan (Nonmetro) | 1-4 years | exact | 1 | 63 | 63 |
| age group by urbanization | Micropolitan (Nonmetro) | 15-24 years | exact | 1 | 253 | 253 |
| age group by urbanization | Micropolitan (Nonmetro) | 25-34 years | exact | 1 | 336 | 336 |
| age group by urbanization | Micropolitan (Nonmetro) | 35-44 years | exact | 1 | 445 | 445 |
| age group by urbanization | Micropolitan (Nonmetro) | 45-54 years | exact | 1 | 615 | 615 |
| age group by urbanization | Micropolitan (Nonmetro) | 5-14 years | exact | 1 | 138 | 138 |
| age group by urbanization | Micropolitan (Nonmetro) | 55-64 years | exact | 1 | 1,155 | 1,155 |
| age group by urbanization | Micropolitan (Nonmetro) | 65-74 years | exact | 1 | 1,364 | 1,364 |
| age group by urbanization | Micropolitan (Nonmetro) | 75-84 years | exact | 1 | 1,159 | 1,159 |
| age group by urbanization | Micropolitan (Nonmetro) | 85+ years | exact | 1 | 680 | 680 |
| age group by urbanization | Micropolitan (Nonmetro) | < 1 year | exact | 1 | 41 | 41 |
| age group by urbanization | Micropolitan (Nonmetro) | Not Stated | zero | 1 | 0 | 0 |
| age group by urbanization | NonCore (Nonmetro) | 1-4 years | exact | 1 | 49 | 49 |
| age group by urbanization | NonCore (Nonmetro) | 15-24 years | exact | 1 | 174 | 174 |
| age group by urbanization | NonCore (Nonmetro) | 25-34 years | exact | 1 | 206 | 206 |
| age group by urbanization | NonCore (Nonmetro) | 35-44 years | exact | 1 | 283 | 283 |
| age group by urbanization | NonCore (Nonmetro) | 45-54 years | exact | 1 | 402 | 402 |
| age group by urbanization | NonCore (Nonmetro) | 5-14 years | exact | 1 | 103 | 103 |
| age group by urbanization | NonCore (Nonmetro) | 55-64 years | exact | 1 | 767 | 767 |
| age group by urbanization | NonCore (Nonmetro) | 65-74 years | exact | 1 | 985 | 985 |
| age group by urbanization | NonCore (Nonmetro) | 75-84 years | exact | 1 | 790 | 790 |
| age group by urbanization | NonCore (Nonmetro) | 85+ years | exact | 1 | 429 | 429 |
| age group by urbanization | NonCore (Nonmetro) | < 1 year | exact | 1 | 22 | 22 |
| age group by urbanization | NonCore (Nonmetro) | Not Stated | zero | 1 | 0 | 0 |
| age group by urbanization | Not Available | 1-4 years | suppressed_1_9 | 1 | 1 | 9 |
| age group by urbanization | Not Available | 15-24 years | exact | 1 | 20 | 20 |
| age group by urbanization | Not Available | 25-34 years | exact | 1 | 35 | 35 |
| age group by urbanization | Not Available | 35-44 years | exact | 1 | 25 | 25 |
| age group by urbanization | Not Available | 45-54 years | exact | 1 | 40 | 40 |
| age group by urbanization | Not Available | 5-14 years | exact | 1 | 13 | 13 |
| age group by urbanization | Not Available | 55-64 years | exact | 1 | 76 | 76 |
| age group by urbanization | Not Available | 65-74 years | exact | 1 | 122 | 122 |
| age group by urbanization | Not Available | 75-84 years | exact | 1 | 125 | 125 |
| age group by urbanization | Not Available | 85+ years | exact | 1 | 89 | 89 |
| age group by urbanization | Not Available | < 1 year | suppressed_1_9 | 1 | 1 | 9 |
| age group by urbanization | Not Available | Not Stated | zero | 1 | 0 | 0 |
| age group by urbanization | Small Metro | 1-4 years | exact | 1 | 77 | 77 |
| age group by urbanization | Small Metro | 15-24 years | exact | 1 | 287 | 287 |
| age group by urbanization | Small Metro | 25-34 years | exact | 1 | 341 | 341 |
| age group by urbanization | Small Metro | 35-44 years | exact | 1 | 403 | 403 |
| age group by urbanization | Small Metro | 45-54 years | exact | 1 | 562 | 562 |
| age group by urbanization | Small Metro | 5-14 years | exact | 1 | 138 | 138 |
| age group by urbanization | Small Metro | 55-64 years | exact | 1 | 984 | 984 |
| age group by urbanization | Small Metro | 65-74 years | exact | 1 | 1,241 | 1,241 |
| age group by urbanization | Small Metro | 75-84 years | exact | 1 | 1,014 | 1,014 |
| age group by urbanization | Small Metro | 85+ years | exact | 1 | 648 | 648 |
| age group by urbanization | Small Metro | < 1 year | exact | 1 | 50 | 50 |
| age group by urbanization | Small Metro | Not Stated | zero | 1 | 0 | 0 |

Note. Age group descriptive context is aggregate and not a person-level risk estimate.
## Table S7. Sex by urbanization

| Table | Urbanization | Sex | Death Count Status | Rows | Lower | Upper |
| --- | --- | --- | --- | --- | --- | --- |
| sex by urbanization | Large Central Metro | Female | exact | 1 | 7,983 | 7,983 |
| sex by urbanization | Large Central Metro | Male | exact | 1 | 8,638 | 8,638 |
| sex by urbanization | Large Fringe Metro | Female | exact | 1 | 6,022 | 6,022 |
| sex by urbanization | Large Fringe Metro | Male | exact | 1 | 5,980 | 5,980 |
| sex by urbanization | Medium Metro | Female | exact | 1 | 6,388 | 6,388 |
| sex by urbanization | Medium Metro | Male | exact | 1 | 6,610 | 6,610 |
| sex by urbanization | Micropolitan (Nonmetro) | Female | exact | 1 | 3,096 | 3,096 |
| sex by urbanization | Micropolitan (Nonmetro) | Male | exact | 1 | 3,153 | 3,153 |
| sex by urbanization | NonCore (Nonmetro) | Female | exact | 1 | 2,020 | 2,020 |
| sex by urbanization | NonCore (Nonmetro) | Male | exact | 1 | 2,190 | 2,190 |
| sex by urbanization | Not Available | Female | exact | 1 | 271 | 271 |
| sex by urbanization | Not Available | Male | exact | 1 | 284 | 284 |
| sex by urbanization | Small Metro | Female | exact | 1 | 2,803 | 2,803 |
| sex by urbanization | Small Metro | Male | exact | 1 | 2,942 | 2,942 |

Note. Sex-stratified descriptive context sums to the reconciled national multiple-cause total where rows are exact.
## Table S8. Race and Hispanic-origin descriptive summaries

| Descriptive Domain | Table | Urbanization | Race | Death Count Status | Rows | Lower | Upper | Hispanic Origin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| race | race by urbanization | Large Central Metro | American Indian or Alaska Native | exact | 1 | 105 | 105 |  |
| race | race by urbanization | Large Central Metro | Asian | exact | 1 | 626 | 626 |  |
| race | race by urbanization | Large Central Metro | Black or African American | exact | 1 | 5,074 | 5,074 |  |
| race | race by urbanization | Large Central Metro | More than one race | exact | 1 | 206 | 206 |  |
| race | race by urbanization | Large Central Metro | Native Hawaiian or Other Pacific Islander | exact | 1 | 50 | 50 |  |
| race | race by urbanization | Large Central Metro | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Large Central Metro | White | exact | 1 | 10,560 | 10,560 |  |
| race | race by urbanization | Large Fringe Metro | American Indian or Alaska Native | exact | 1 | 49 | 49 |  |
| race | race by urbanization | Large Fringe Metro | Asian | exact | 1 | 291 | 291 |  |
| race | race by urbanization | Large Fringe Metro | Black or African American | exact | 1 | 2,491 | 2,491 |  |
| race | race by urbanization | Large Fringe Metro | More than one race | exact | 1 | 89 | 89 |  |
| race | race by urbanization | Large Fringe Metro | Native Hawaiian or Other Pacific Islander | exact | 1 | 13 | 13 |  |
| race | race by urbanization | Large Fringe Metro | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Large Fringe Metro | White | exact | 1 | 9,069 | 9,069 |  |
| race | race by urbanization | Medium Metro | American Indian or Alaska Native | exact | 1 | 91 | 91 |  |
| race | race by urbanization | Medium Metro | Asian | exact | 1 | 188 | 188 |  |
| race | race by urbanization | Medium Metro | Black or African American | exact | 1 | 2,482 | 2,482 |  |
| race | race by urbanization | Medium Metro | More than one race | exact | 1 | 112 | 112 |  |
| race | race by urbanization | Medium Metro | Native Hawaiian or Other Pacific Islander | exact | 1 | 36 | 36 |  |
| race | race by urbanization | Medium Metro | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Medium Metro | White | exact | 1 | 10,089 | 10,089 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | American Indian or Alaska Native | exact | 1 | 122 | 122 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | Asian | exact | 1 | 28 | 28 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | Black or African American | exact | 1 | 809 | 809 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | More than one race | exact | 1 | 60 | 60 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | Native Hawaiian or Other Pacific Islander | suppressed_1_9 | 1 | 1 | 9 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Micropolitan (Nonmetro) | White | exact | 1 | 5,222 | 5,222 |  |
| race | race by urbanization | NonCore (Nonmetro) | American Indian or Alaska Native | exact | 1 | 163 | 163 |  |
| race | race by urbanization | NonCore (Nonmetro) | Asian | exact | 1 | 10 | 10 |  |
| race | race by urbanization | NonCore (Nonmetro) | Black or African American | exact | 1 | 548 | 548 |  |
| race | race by urbanization | NonCore (Nonmetro) | More than one race | exact | 1 | 17 | 17 |  |
| race | race by urbanization | NonCore (Nonmetro) | Native Hawaiian or Other Pacific Islander | suppressed_1_9 | 1 | 1 | 9 |  |
| race | race by urbanization | NonCore (Nonmetro) | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | NonCore (Nonmetro) | White | exact | 1 | 3,468 | 3,468 |  |
| race | race by urbanization | Not Available | American Indian or Alaska Native | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Not Available | Asian | exact | 1 | 10 | 10 |  |
| race | race by urbanization | Not Available | Black or African American | exact | 1 | 97 | 97 |  |
| race | race by urbanization | Not Available | More than one race | suppressed_1_9 | 1 | 1 | 9 |  |
| race | race by urbanization | Not Available | Native Hawaiian or Other Pacific Islander | suppressed_1_9 | 1 | 1 | 9 |  |
| race | race by urbanization | Not Available | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Not Available | White | exact | 1 | 442 | 442 |  |
| race | race by urbanization | Small Metro | American Indian or Alaska Native | exact | 1 | 85 | 85 |  |
| race | race by urbanization | Small Metro | Asian | exact | 1 | 40 | 40 |  |
| race | race by urbanization | Small Metro | Black or African American | exact | 1 | 756 | 756 |  |
| race | race by urbanization | Small Metro | More than one race | exact | 1 | 51 | 51 |  |
| race | race by urbanization | Small Metro | Native Hawaiian or Other Pacific Islander | suppressed_1_9 | 1 | 1 | 9 |  |
| race | race by urbanization | Small Metro | Not Available | zero | 1 | 0 | 0 |  |
| race | race by urbanization | Small Metro | White | exact | 1 | 4,808 | 4,808 |  |
| hispanic_origin | Hispanic origin by urbanization | Large Central Metro |  | exact | 1 | 3,032 | 3,032 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Large Central Metro |  | exact | 1 | 13,487 | 13,487 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Large Central Metro |  | exact | 1 | 102 | 102 | Not Stated |
| hispanic_origin | Hispanic origin by urbanization | Large Fringe Metro |  | exact | 1 | 987 | 987 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Large Fringe Metro |  | exact | 1 | 10,992 | 10,992 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Large Fringe Metro |  | exact | 1 | 23 | 23 | Not Stated |
| hispanic_origin | Hispanic origin by urbanization | Medium Metro |  | exact | 1 | 1,324 | 1,324 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Medium Metro |  | exact | 1 | 11,631 | 11,631 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Medium Metro |  | exact | 1 | 43 | 43 | Not Stated |
| hispanic_origin | Hispanic origin by urbanization | Micropolitan (Nonmetro) |  | exact | 1 | 340 | 340 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Micropolitan (Nonmetro) |  | exact | 1 | 5,894 | 5,894 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Micropolitan (Nonmetro) |  | exact | 1 | 15 | 15 | Not Stated |
| hispanic_origin | Hispanic origin by urbanization | NonCore (Nonmetro) |  | exact | 1 | 168 | 168 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | NonCore (Nonmetro) |  | exact | 1 | 4,033 | 4,033 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | NonCore (Nonmetro) |  | suppressed_1_9 | 1 | 1 | 9 | Not Stated |
| hispanic_origin | Hispanic origin by urbanization | Not Available |  | exact | 1 | 66 | 66 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Not Available |  | exact | 1 | 488 | 488 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Not Available |  | suppressed_1_9 | 1 | 1 | 9 | Not Stated |
| hispanic_origin | Hispanic origin by urbanization | Small Metro |  | exact | 1 | 360 | 360 | Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Small Metro |  | exact | 1 | 5,365 | 5,365 | Not Hispanic or Latino |
| hispanic_origin | Hispanic origin by urbanization | Small Metro |  | exact | 1 | 20 | 20 | Not Stated |

Note. Race and Hispanic-origin outputs are descriptive aggregate summaries and are limited by suppression.
## Table S9. Underlying-cause county suppression profile

| Death Count Status | Rows | Lower | Upper |
| --- | --- | --- | --- |
| aggregate_total | 1 | 22,306 | 22,306 |
| exact | 504 | 16,650 | 16,650 |
| suppressed_1_9 | 1,866 | 1,866 | 16,794 |
| zero | 772 | 0 | 0 |

Note. Underlying-cause G40/G41 sensitivity profile preserves exact, suppressed, and explicit-zero status.
## Table S10. County merge and Connecticut geography details

| Merge Issue | County Fips | County | County Name | Notes |
| --- | --- | --- | --- | --- |
| WONDER county missing covariates | 02261 | Valdez-Cordova Census Area, AK |  |  |
| WONDER county missing covariates | 02270 | Wade Hampton Census Area, AK |  |  |
| WONDER county missing covariates | 09001 | Fairfield County, CT |  |  |
| WONDER county missing covariates | 09003 | Hartford County, CT |  |  |
| WONDER county missing covariates | 09005 | Litchfield County, CT |  |  |
| WONDER county missing covariates | 09007 | Middlesex County, CT |  |  |
| WONDER county missing covariates | 09009 | New Haven County, CT |  |  |
| WONDER county missing covariates | 09011 | New London County, CT |  |  |
| WONDER county missing covariates | 09013 | Tolland County, CT |  |  |
| WONDER county missing covariates | 09015 | Windham County, CT |  |  |
| WONDER county missing covariates | 46113 | Shannon County, SD |  |  |
| Covariate county missing WONDER | 02063 |  |  |  |
| Covariate county missing WONDER | 02066 |  |  |  |
| Covariate county missing WONDER | 02158 |  |  |  |
| Covariate county missing WONDER | 09110 |  |  |  |
| Covariate county missing WONDER | 09120 |  |  |  |
| Covariate county missing WONDER | 09130 |  |  |  |
| Covariate county missing WONDER | 09140 |  |  |  |
| Covariate county missing WONDER | 09150 |  |  |  |
| Covariate county missing WONDER | 09160 |  |  |  |
| Covariate county missing WONDER | 09170 |  |  |  |
| Covariate county missing WONDER | 09180 |  |  |  |
| Covariate county missing WONDER | 09190 |  |  |  |
| Covariate county missing WONDER | 46102 |  |  |  |
| Connecticut geography note | 00009 |  | Connecticut county/county-equivalent units | CDC WONDER county-equivalent warning retained; no crosswalk correction applied; 2022 planning-region transition may affect period comparability. |

Note. Merge exceptions and Connecticut geography cautions are documented for reproducibility.

## Revised scenario audit

The county-period extract reconciled to 58,380 multiple-cause G40/G41 deaths. Exact counties contributed 51,388 deaths, leaving 6,992 deaths in 1,722 suppressed rows, or ≈4.1 deaths per suppressed row. Population-scaled, conservative anti-rural, and pro-rural residual allocations each preserve the reconciled total after 1-9 clipping. Suppressed=5 and suppressed=9 exceed the reconciled total and are retained only as extreme stress tests. The constant-mean 4.06 scenario preserves the total but is treated as a distributional stress test because it assigns the same hidden count to every suppressed county.

## Supplementary figure inventory

- Figure S1: national-year mortality trend, 2019-2024.
- Figure S2: COVID co-mention by urbanization-year, 2019-2024.
- Figure S3: residual-allocation county rate map.

All supplementary tables and figures are embedded in the supplement DOCX and are also supplied as package files.
