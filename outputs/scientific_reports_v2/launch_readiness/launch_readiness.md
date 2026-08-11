# Scientific Reports v2 production launch readiness

Status: **PASS**

| Check | Passed | Detail |
| --- | --- | --- |
| v111_frozen | True | v1.1.1 remains the immutable baseline tag |
| exact_kernel_pass | True | True |
| randomized_exact_kernel_pass | True | True |
| constraint_geometry_matches | True | latent=9695 rank=1256 nullity=8439 |
| extended_real_pilot_pass | True | max_primary_rhat=1.0631317259532127 min_bulk_ess=73.16747911375178 |
| calibration_design_pass | True | True |
| tuned_calibration_extension_pass | True | max_primary_rhat=1.021967606648702 min_bulk_ess=152.5878092124334 primary_coverage=1.0 |
| final_infrastructure_pass | True | True |
| ready_helper_strict_shell | True | login shell and fail-closed mode |
| ready_helper_order | True | audit → prepare → stage → production array → dependent final gate |
| ready_helper_fail_closed_dependency | True | final gate launches only after the entire array succeeds |
| ready_helper_records_jobs | True | job IDs and dependencies persisted |

Authoritative Wahab command:

```bash
bash hpc/wahab/submit_sr_v2_production_ready.sh
```

This gate does not launch production and does not authorize a corrected manuscript estimate.
