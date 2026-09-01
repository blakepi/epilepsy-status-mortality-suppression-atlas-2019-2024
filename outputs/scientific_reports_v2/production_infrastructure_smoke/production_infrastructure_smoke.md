# Scientific Reports v2 production infrastructure smoke audit

Final status: **HOLD**

| Check | Passed | Detail |
| --- | --- | --- |
| python_ast:75_prepare_sr_v2_production.py | True | AST parse passed |
| isolated_output_namespace:75_prepare_sr_v2_production.py | True | Scientific Reports v2 production namespace present |
| python_ast:76_run_sr_v2_production_chain.py | True | AST parse passed |
| isolated_output_namespace:76_run_sr_v2_production_chain.py | True | Scientific Reports v2 production namespace present |
| python_ast:77_merge_sr_v2_production.py | True | AST parse passed |
| isolated_output_namespace:77_merge_sr_v2_production.py | True | Scientific Reports v2 production namespace present |
| python_ast:78_gate_sr_v2_production.py | True | AST parse passed |
| isolated_output_namespace:78_gate_sr_v2_production.py | True | Scientific Reports v2 production namespace present |
| array_has_eight_chains | True | expected 1-8%8 |
| array_uses_main_partition | True | main partition |
| array_has_no_gpu_request | True | CPU-only |
| array_uses_v2_runner | True | v2 chain runner |
| array_uses_v2_sync | True | isolated result sync |
| finalize_uses_v2_merger | True | v2 merger |
| finalize_uses_v2_gate | True | v2 gate |
| submission_has_afterok_dependency | True | fail-closed dependency |
| submission_prepares_before_staging | True | prepare then stage |
| sync_scope_is_v2_only | True | v2-only relative root |
| legacy_sync_not_used | True | legacy sync excluded |
| baseline_commit_guard | True | tag and commit guard |
| branch_guard | True | scientific-reports-v2 branch guard |
| extended_pilot_guard | True | extended pilot required |
| calibration_guard | True | truth-known calibration required |
| new_random_seeds | False | new v2 chain seeds |
| new_initialization_seeds | False | new dispersed-start seeds |
| all_parameter_gate | True | all-parameter convergence gate |
| latent_summary_gate | True | latent aggregate convergence gate |
| validation_gate | True | zero-failure constraint gate |
| shell_has_shebang:sync_sr_v2_results_home.sh | True | login-shell shebang |
| shell_fail_closed:sync_sr_v2_results_home.sh | True | strict shell mode |
| shell_no_windows_path:sync_sr_v2_results_home.sh | True | portable paths |
| shell_has_shebang:submit_sr_v2_production.sh | True | login-shell shebang |
| shell_fail_closed:submit_sr_v2_production.sh | True | strict shell mode |
| shell_no_windows_path:submit_sr_v2_production.sh | True | portable paths |
| shell_has_shebang:60_sr_v2_production_chain_array.sbatch | True | login-shell shebang |
| shell_fail_closed:60_sr_v2_production_chain_array.sbatch | True | strict shell mode |
| shell_no_windows_path:60_sr_v2_production_chain_array.sbatch | True | portable paths |
| shell_has_shebang:61_sr_v2_finalize_production.sbatch | True | login-shell shebang |
| shell_fail_closed:61_sr_v2_finalize_production.sbatch | True | strict shell mode |
| shell_no_windows_path:61_sr_v2_finalize_production.sbatch | True | portable paths |
| frozen_config_deferred | True | config correctly deferred until pilot gates pass |

No production chain was launched. The audit checks namespace isolation, fail-closed gates, frozen-baseline guards, Slurm wiring, and syntax-level integrity.
