# Scientific Reports v2 calibration-design smoke test

A deterministic six-state, 72-county, six-year panel was selected from the real model frame. Complete NB2 counts were generated under known rurality, SVI, age, sex, year, and state effects, then subjected to the same 1–9 cell suppression rule and compatible county-period/state-year/national constraints.

| Quantity | Value |
| --- | ---: |
| states | 6 |
| counties | 72 |
| county-year rows | 432 |
| exact cells | 41 |
| suppressed cells | 227 |
| zero cells | 164 |
| suppressed fraction | 0.5255 |
| minimum pairwise initialization L1 distance | 296 |
| design gate | PASS |

This validates the truth-known data generator, disclosure transformation, aggregate construction, feasibility solver, and dispersed-start construction. It does not yet evaluate estimator bias or interval coverage.
