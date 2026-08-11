# Scientific Reports v2 prior-sensitivity infrastructure

Status: **PASS**

| Check | Passed | Detail |
| --- | --- | --- |
| python_ast:model | True | AST parse passed |
| python_ast:prepare | True | AST parse passed |
| python_ast:runner | True | AST parse passed |
| python_ast:summarize | True | AST parse passed |
| primary_default_unchanged | True | default profile matches corrected primary target |
| context_restores_profile | True | profile override is scoped and exception-safe |
| prepare_requires_passed_production | True | sensitivity blocked before corrected production pass |
| both_profiles_prespecified | True | broader and regularizing profiles |
| fresh_chain_and_initialization_seeds | True | profile-specific nonproduction seeds |
| runner_activates_recorded_profile | True | single validated sampler reused under explicit profile context |
| runner_uses_fresh_feasible_starts | True | sensitivity chains do not inherit a primary posterior state |
| summary_rechecks_primary_production_gate | True | comparison requires passed primary analysis |
| summary_reports_all_parameter_convergence | True | all-parameter convergence is retained |
| summary_reports_material_primary_shifts | True | effect-size change and interval overlap reported |
| registry_contains_profiles | True | profiles frozen before corrected results |

No sensitivity or empirical production chain was launched by this audit.
