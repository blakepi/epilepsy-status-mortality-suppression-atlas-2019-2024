# Scientific Reports v2 final production infrastructure audit

Final status: **PASS**

| Check | Passed | Detail |
| --- | --- | --- |
| python_ast:82_prepare_sr_v2_production_final.py | True | AST parse passed |
| v2_namespace:82_prepare_sr_v2_production_final.py | True | isolated corrected production namespace |
| python_ast:76_run_sr_v2_production_chain.py | True | AST parse passed |
| v2_namespace:76_run_sr_v2_production_chain.py | True | isolated corrected production namespace |
| python_ast:77_merge_sr_v2_production.py | True | AST parse passed |
| v2_namespace:77_merge_sr_v2_production.py | True | isolated corrected production namespace |
| python_ast:83_gate_sr_v2_production_final.py | True | AST parse passed |
| v2_namespace:83_gate_sr_v2_production_final.py | True | isolated corrected production namespace |
| frozen_v111_guard | True | immutable v1.1.1 tag and commit required |
| scientific_reports_branch_guard | True | final preparation restricted to v2 branch |
| exact_kernel_gates_required | True | deterministic and randomized exact-kernel evidence required |
| constraint_geometry_required | True | audited latent-variable rank and nullity required |
| extended_real_pilot_required | True | extended real-data tuning gate required |
| tuned_calibration_required | True | tuned truth-known calibration gate required |
| prespecified_chain_seed_range | True | chain seeds 58291–58298 |
| prespecified_initialization_seed_range | True | dispersed initialization seeds 57291–57298 |
| eight_chain_array | True | eight independent production jobs |
| cpu_only_array | True | CPU-only main-partition production |
| final_submit_uses_final_prepare | True | final gate-aware preparation |
| final_submit_uses_final_stage | True | tuned validation evidence staged |
| final_submit_fail_closed_dependency | True | finalization runs only after successful array |
| final_submit_uses_final_gate_job | True | final calibrated gate job selected |
| final_stage_includes_tuned_calibration | True | tuned calibration evidence copied to scratch |
| finalize_merges_then_gates | True | merge precedes fail-closed gate |
| all_parameter_gate | True | all-parameter and primary ESS thresholds enforced |
| latent_summary_gate | True | representative latent summaries gated |
| constraint_validation_gate | True | all retained latent states must satisfy constraints |
| final_gate_requires_tuned_calibration | True | final production gate rechecks tuned calibration |
| shell_shebang:stage_sr_v2_to_scratch_final.sh | True | login-shell shebang |
| shell_strict_mode:stage_sr_v2_to_scratch_final.sh | True | fail-closed shell mode |
| shell_portable_paths:stage_sr_v2_to_scratch_final.sh | True | no drive-qualified Windows path |
| shell_shebang:sync_sr_v2_results_home.sh | True | login-shell shebang |
| shell_strict_mode:sync_sr_v2_results_home.sh | True | fail-closed shell mode |
| shell_portable_paths:sync_sr_v2_results_home.sh | True | no drive-qualified Windows path |
| shell_shebang:submit_sr_v2_production_final.sh | True | login-shell shebang |
| shell_strict_mode:submit_sr_v2_production_final.sh | True | fail-closed shell mode |
| shell_portable_paths:submit_sr_v2_production_final.sh | True | no drive-qualified Windows path |
| shell_shebang:60_sr_v2_production_chain_array.sbatch | True | login-shell shebang |
| shell_strict_mode:60_sr_v2_production_chain_array.sbatch | True | fail-closed shell mode |
| shell_portable_paths:60_sr_v2_production_chain_array.sbatch | True | no drive-qualified Windows path |
| shell_shebang:62_sr_v2_finalize_production_final.sbatch | True | login-shell shebang |
| shell_strict_mode:62_sr_v2_finalize_production_final.sbatch | True | fail-closed shell mode |
| shell_portable_paths:62_sr_v2_finalize_production_final.sbatch | True | no drive-qualified Windows path |

Authoritative launch helper: `hpc/wahab/submit_sr_v2_production_final.sh`.

No production chain was launched by this audit.
