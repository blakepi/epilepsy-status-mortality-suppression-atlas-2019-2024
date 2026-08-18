# Scientific Reports v2 corrected production gate

Final status: **PASS**
Action: `freeze_corrected_results`

| Check | Passed | Detail |
| --- | --- | --- |
| eight_completed_chains | True | chains=8 statuses=['completed'] |
| expected_iterations | True | iterations=[300000] |
| expected_draws_per_chain | True | draws=[4500] |
| unique_prespecified_seeds | True | seeds=[58291, 58292, 58293, 58294, 58295, 58296, 58297, 58298] |
| grand_total_preserved | True | totals=[58380] |
| zero_constraint_failures | True | failures=0 records=489696 |
| complete_parameter_set | True | parameters=69 expected=69 |
| parameter_diagnostics_finite | True | finite=True |
| all_parameter_rhat | True | maximum=1.005976 threshold=1.01 |
| all_parameter_bulk_ess | True | minimum=1577.7 threshold=400 |
| all_parameter_tail_ess | True | minimum=2738.2 threshold=400 |
| primary_bulk_ess | True | minimum=4070.6 threshold=1000 |
| primary_tail_ess | True | minimum=9330.5 threshold=1000 |
| latent_summary_diagnostics_finite | True | stochastic=32 deterministic=0 finite=True |
| latent_summary_rhat | True | maximum=1.001524 threshold=1.01 |
| latent_summary_bulk_ess | True | minimum=4467.1 threshold=400 |
| latent_summary_tail_ess | True | minimum=5805.8 threshold=400 |
| exact_kernel_gate | True | True |
| randomized_exact_kernel_gate | True | True |
| constraint_geometry_recorded | True | latent_variables=9695 rank=1256 nullity=8439 |
| extended_real_pilot_gate | True | True |
| calibration_design_gate | True | True |
| tuned_calibration_extension_gate | True | True |

Passing this gate authorizes freezing corrected computational results only; it does not by itself authorize journal submission.
