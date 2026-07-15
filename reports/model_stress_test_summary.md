# Model Stress Test Summary

Generated: 2026-06-13

## Rurality Signal Category

`SUPPRESSION_SENSITIVE_SIGNAL`

## Nonmetro Nonadjacent Stress Test

| scenario | irr | ci_low | ci_high | p_value |
| --- | --- | --- | --- | --- |
| observed_exact_positive_only | 0.9743 | 0.7986 | 1.189 | 0.7977 |
| observed_exact_plus_zero | 0.9081 | 0.7766 | 1.062 | 0.2272 |
| suppressed_equals_1 | 0.9845 | 0.8844 | 1.096 | 0.7759 |
| suppressed_equals_5 | 1.291 | 1.178 | 1.415 | 4.784e-08 |
| suppressed_equals_9 | 1.423 | 1.266 | 1.598 | 3.135e-09 |
| population_scaled_residual_allocation | 1.037 | 0.9807 | 1.096 | 0.2033 |
| conservative_anti_rural_allocation | 0.9659 | 0.8988 | 1.038 | 0.3459 |
| pro_rural_allocation | 1.125 | 1.054 | 1.201 | 0.0003932 |

## SVI Q4 vs Q1 Stress Test

| scenario | irr | ci_low | ci_high | p_value |
| --- | --- | --- | --- | --- |
| observed_exact_positive_only | 0.862 | 0.7504 | 0.9901 | 0.03565 |
| observed_exact_plus_zero | 1.024 | 0.885 | 1.184 | 0.7532 |
| suppressed_equals_1 | 1.114 | 1.014 | 1.225 | 0.02521 |
| suppressed_equals_5 | 0.9954 | 0.9124 | 1.086 | 0.9165 |
| suppressed_equals_9 | 0.9555 | 0.8558 | 1.067 | 0.4177 |
| population_scaled_residual_allocation | 1.062 | 1.011 | 1.116 | 0.01629 |
| conservative_anti_rural_allocation | 1.088 | 1.019 | 1.162 | 0.0115 |
| pro_rural_allocation | 1.049 | 0.9924 | 1.109 | 0.09082 |

## Interpretation

The rurality conclusion should be framed according to `SUPPRESSION_SENSITIVE_SIGNAL`. If
the most conservative allocation attenuates precision, manuscript language
should emphasize suppression-aware uncertainty rather than deterministic
fully observed county-level claims.
