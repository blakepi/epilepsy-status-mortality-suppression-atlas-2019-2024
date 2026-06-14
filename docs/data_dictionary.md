# Data Dictionary

This data dictionary summarizes the primary processed aggregate datasets and manuscript tables included in the release. It is intended as a practical column guide; source-specific definitions should be checked against the relevant CDC WONDER, SVI, RUCC, NCHS, ACS, and geography documentation.

## Key status variables

- `death_status` / `death_count_status`: distinguishes exact, suppressed_1_9, explicit zero, aggregate total, and other noncounty or missing statuses where applicable.
- `lower` and `upper`: lower and upper bounded death-count values. Suppressed cells use lower=1 and upper=9.
- `midpoint`: descriptive midpoint used for summaries, not a recovered true count.
- `person_years` / population fields: denominator exposure used for period or annual rate calculations.
- `primary_rurality`: collapsed RUCC category used in primary county-period models.
- `svi_quartile`: county Social Vulnerability Index quartile.

## `data/processed/county_period_analysis.csv`

| Column | Inferred type |
| --- | --- |
| `query_id` | `str` |
| `row_type` | `str` |
| `year` | `float64` |
| `state` | `float64` |
| `state_fips` | `float64` |
| `county` | `str` |
| `county_fips` | `int64` |
| `urbanization` | `float64` |
| `age_group` | `float64` |
| `sex` | `float64` |
| `race` | `float64` |
| `hispanic_origin` | `float64` |
| `place_of_death` | `float64` |
| `deaths_raw` | `str` |
| `deaths` | `float64` |
| `death_count_status` | `str` |
| `death_count_known` | `bool` |
| `death_count_suppressed` | `bool` |
| `death_count_zero` | `bool` |
| `population` | `float64` |
| `crude_rate` | `float64` |
| `rate_status` | `str` |
| `notes` | `float64` |
| `deaths_exact` | `float64` |
| `death_lower` | `float64` |
| `death_upper` | `float64` |
| `death_midpoint` | `float64` |
| `suppressed_indicator` | `bool` |
| `zero_indicator` | `bool` |
| `exact_indicator` | `bool` |
| `aggregate_total_indicator` | `bool` |
| `county_name_from_wonder` | `str` |
| `state_abbrev_from_wonder` | `str` |
| `population_or_person_years_wonder_q001` | `float64` |
| `person_years_from_q002` | `float64` |
| `q001_minus_q002_person_years` | `float64` |
| `model_exposure_person_years` | `float64` |
| `annualized_rate_per_100k_midpoint` | `float64` |
| `annualized_rate_per_100k_exact_or_zero` | `float64` |
| `cbsa_title` | `str` |
| `nchs_code_2023` | `float64` |
| `nchs_urban_rural_6` | `str` |
| `nchs_collapsed_3` | `str` |
| `state_fips_cov` | `int64` |
| `state_cov` | `str` |
| `state_abbrev` | `str` |
| `county_name` | `str` |
| `svi_overall` | `float64` |
| `svi_theme1` | `float64` |
| `svi_theme2` | `float64` |
| `svi_theme3` | `float64` |
| `svi_theme4` | `float64` |
| `svi_total_flags` | `float64` |
| `svi_ep_poverty_150` | `float64` |
| `svi_ep_uninsured` | `float64` |
| `svi_ep_age65` | `float64` |
| `svi_ep_minority` | `float64` |
| `svi_ep_black` | `float64` |
| `svi_ep_hispanic` | `float64` |
| `svi_e_totpop` | `float64` |
| `svi_quartile` | `str` |
| `rucc_code` | `float64` |
| `rucc_description` | `str` |
| `rucc_population_2020` | `float64` |
| `rucc_collapsed` | `str` |
| `metro_nonmetro` | `str` |
| `rucc_nonmetro_binary` | `float64` |
| `acs_total_population` | `float64` |
| `acs_pct_male` | `float64` |
| `acs_pct_age_65_plus` | `float64` |
| `acs_pct_non_hispanic_black` | `float64` |
| `acs_pct_hispanic` | `float64` |
| `acs_pct_poverty` | `float64` |
| `acs_pct_uninsured` | `float64` |
| `acs_pct_high_school_grad_or_higher` | `float64` |
| `acs_pct_bachelors_or_higher` | `float64` |
| `acs_median_household_income` | `float64` |
| `primary_rurality` | `str` |
| `rurality_binary` | `str` |
| `rucc_1_3_vs_4_9` | `str` |
| `death_status` | `str` |
| `invalid_noncounty_indicator` | `bool` |
| `rate_reliability_flag` | `str` |
| `collapsed_RUCC` | `str` |
| `NCHS_urban_rural` | `str` |
| `SVI_overall` | `float64` |
| `SVI_quartile` | `str` |
| `geometry_key` | `int64` |

## `data/processed/county_year_analysis.csv`

| Column | Inferred type |
| --- | --- |
| `query_id` | `str` |
| `row_type` | `str` |
| `year` | `int64` |
| `state` | `float64` |
| `state_fips` | `float64` |
| `county` | `str` |
| `county_fips` | `int64` |
| `urbanization` | `float64` |
| `age_group` | `float64` |
| `sex` | `float64` |
| `race` | `float64` |
| `hispanic_origin` | `float64` |
| `place_of_death` | `float64` |
| `deaths_raw` | `str` |
| `deaths` | `float64` |
| `death_count_status` | `str` |
| `death_count_known` | `bool` |
| `death_count_suppressed` | `bool` |
| `death_count_zero` | `bool` |
| `population` | `float64` |
| `crude_rate` | `float64` |
| `rate_status` | `str` |
| `notes` | `float64` |
| `deaths_exact` | `float64` |
| `death_lower` | `float64` |
| `death_upper` | `float64` |
| `death_midpoint` | `float64` |
| `suppressed_indicator` | `bool` |
| `zero_indicator` | `bool` |
| `exact_indicator` | `bool` |
| `aggregate_total_indicator` | `bool` |
| `county_name_from_wonder` | `str` |
| `state_abbrev_from_wonder` | `str` |
| `annual_rate_per_100k_midpoint` | `float64` |
| `annual_rate_per_100k_exact_or_zero` | `float64` |
| `cbsa_title` | `str` |
| `nchs_code_2023` | `float64` |
| `nchs_urban_rural_6` | `str` |
| `nchs_collapsed_3` | `str` |
| `state_fips_cov` | `int64` |
| `state_cov` | `str` |
| `state_abbrev` | `str` |
| `county_name` | `str` |
| `svi_overall` | `float64` |
| `svi_theme1` | `float64` |
| `svi_theme2` | `float64` |
| `svi_theme3` | `float64` |
| `svi_theme4` | `float64` |
| `svi_total_flags` | `float64` |
| `svi_ep_poverty_150` | `float64` |
| `svi_ep_uninsured` | `float64` |
| `svi_ep_age65` | `float64` |
| `svi_ep_minority` | `float64` |
| `svi_ep_black` | `float64` |
| `svi_ep_hispanic` | `float64` |
| `svi_e_totpop` | `float64` |
| `svi_quartile` | `str` |
| `rucc_code` | `float64` |
| `rucc_description` | `str` |
| `rucc_population_2020` | `float64` |
| `rucc_collapsed` | `str` |
| `metro_nonmetro` | `str` |
| `rucc_nonmetro_binary` | `float64` |
| `acs_total_population` | `float64` |
| `acs_pct_male` | `float64` |
| `acs_pct_age_65_plus` | `float64` |
| `acs_pct_non_hispanic_black` | `float64` |
| `acs_pct_hispanic` | `float64` |
| `acs_pct_poverty` | `float64` |
| `acs_pct_uninsured` | `float64` |
| `acs_pct_high_school_grad_or_higher` | `float64` |
| `acs_pct_bachelors_or_higher` | `float64` |
| `acs_median_household_income` | `float64` |
| `primary_rurality` | `str` |
| `rurality_binary` | `str` |
| `rucc_1_3_vs_4_9` | `str` |
| `death_status` | `str` |
| `collapsed_RUCC` | `str` |
| `NCHS` | `str` |
| `SVI` | `float64` |

## `data/processed/county_covariates.csv`

| Column | Inferred type |
| --- | --- |
| `county_fips` | `int64` |
| `cbsa_title` | `str` |
| `nchs_code_2023` | `int64` |
| `nchs_urban_rural_6` | `str` |
| `nchs_collapsed_3` | `str` |
| `state_fips` | `int64` |
| `state` | `str` |
| `state_abbrev` | `str` |
| `county_name` | `str` |
| `svi_overall` | `float64` |
| `svi_theme1` | `float64` |
| `svi_theme2` | `float64` |
| `svi_theme3` | `float64` |
| `svi_theme4` | `float64` |
| `svi_total_flags` | `int64` |
| `svi_ep_poverty_150` | `float64` |
| `svi_ep_uninsured` | `float64` |
| `svi_ep_age65` | `float64` |
| `svi_ep_minority` | `float64` |
| `svi_ep_black` | `float64` |
| `svi_ep_hispanic` | `float64` |
| `svi_e_totpop` | `int64` |
| `svi_quartile` | `str` |
| `rucc_code` | `int64` |
| `rucc_description` | `str` |
| `rucc_population_2020` | `int64` |
| `rucc_collapsed` | `str` |
| `metro_nonmetro` | `str` |
| `rucc_nonmetro_binary` | `int64` |
| `acs_total_population` | `int64` |
| `acs_pct_male` | `float64` |
| `acs_pct_age_65_plus` | `float64` |
| `acs_pct_non_hispanic_black` | `float64` |
| `acs_pct_hispanic` | `float64` |
| `acs_pct_poverty` | `float64` |
| `acs_pct_uninsured` | `float64` |
| `acs_pct_high_school_grad_or_higher` | `float64` |
| `acs_pct_bachelors_or_higher` | `float64` |
| `acs_median_household_income` | `float64` |

## `tables/table1_county_characteristics.csv`

| Column | Inferred type |
| --- | --- |
| `death_status` | `str` |
| `counties` | `int64` |
| `person_years` | `float64` |
| `exact_deaths` | `float64` |
| `lower` | `float64` |
| `upper` | `float64` |
| `pct_nonmetro` | `float64` |
| `mean_svi` | `float64` |
| `mean_poverty` | `float64` |
| `mean_uninsured` | `float64` |
| `mean_age65` | `float64` |

## `tables/table2_mortality_by_rurality_svi.csv`

| Column | Inferred type |
| --- | --- |
| `primary_rurality` | `str` |
| `svi_quartile` | `str` |
| `counties` | `int64` |
| `person_years` | `float64` |
| `lower` | `float64` |
| `midpoint` | `float64` |
| `upper` | `float64` |
| `exact_deaths` | `float64` |
| `suppressed` | `int64` |
| `zero` | `int64` |
| `rate_lower_per_100k` | `float64` |
| `rate_midpoint_per_100k` | `float64` |
| `rate_upper_per_100k` | `float64` |

## `tables/table3_suppression_aware_models.csv`

| Column | Inferred type |
| --- | --- |
| `scenario` | `str` |
| `model_family` | `str` |
| `model_type` | `str` |
| `term` | `str` |
| `coef` | `float64` |
| `se` | `float64` |
| `irr` | `float64` |
| `ci_low` | `float64` |
| `ci_high` | `float64` |
| `p_value` | `float64` |
| `n_rows` | `int64` |
| `events` | `float64` |

## `tables/table4_temporal_context.csv`

| Column | Inferred type |
| --- | --- |
| `source` | `str` |
| `year` | `int64` |
| `deaths` | `float64` |
| `population` | `float64` |
| `rate_per_100k` | `float64` |
| `urbanization` | `str` |
| `death_status` | `str` |
| `rows` | `float64` |
| `lower` | `float64` |
| `upper` | `float64` |

## `tables/table5_ucd_sensitivity.csv`

| Column | Inferred type |
| --- | --- |
| `death_count_status` | `str` |
| `rows` | `float64` |
| `section` | `str` |
| `urbanization` | `str` |
| `year` | `float64` |
| `mcod_lower` | `float64` |
| `mcod_upper` | `float64` |
| `ucd_lower` | `float64` |
| `ucd_upper` | `float64` |
