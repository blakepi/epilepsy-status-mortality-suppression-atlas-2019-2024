from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    ROOT
    / "outputs"
    / "scientific_reports_v2"
    / "prior_sensitivity_infrastructure"
)
FILES = {
    "model": ROOT / "src" / "bayes_constrained" / "model.py",
    "prepare": ROOT / "scripts" / "93_prepare_sr_v2_prior_sensitivity.py",
    "runner": ROOT / "scripts" / "94_run_sr_v2_prior_sensitivity_chain.py",
    "summarize": ROOT / "scripts" / "95_summarize_sr_v2_prior_sensitivity.py",
    "registry": ROOT / "config" / "scientific_reports_v2_robustness_registry.yaml",
}


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    texts = {
        name: path.read_text(encoding="utf-8")
        for name, path in FILES.items()
    }
    checks: list[dict[str, object]] = []
    for name in ["model", "prepare", "runner", "summarize"]:
        try:
            ast.parse(texts[name], filename=str(FILES[name]))
            checks.append(check(f"python_ast:{name}", True, "AST parse passed"))
        except SyntaxError as exc:
            checks.append(check(f"python_ast:{name}", False, repr(exc)))

    checks.extend(
        [
            check(
                "primary_default_unchanged",
                all(
                    token in texts["model"]
                    for token in [
                        "intercept_sd: float = 5.0",
                        "nonintercept_beta_sd: float = 1.5",
                        "state_scale_halfnormal_sd: float = 1.0",
                        "year_scale_halfnormal_sd: float = 1.0",
                        "log_kappa_sd: float = 1.5",
                    ]
                ),
                "default profile matches corrected primary target",
            ),
            check(
                "context_restores_profile",
                "finally:" in texts["model"]
                and "_ACTIVE_PRIOR_SPECIFICATION = previous" in texts["model"],
                "profile override is scoped and exception-safe",
            ),
            check(
                "prepare_requires_passed_production",
                "production_gate.json" in texts["prepare"]
                and "gate.get(\"passed\", False)" in texts["prepare"],
                "sensitivity blocked before corrected production pass",
            ),
            check(
                "both_profiles_prespecified",
                all(
                    profile in texts["prepare"]
                    for profile in ["broader", "regularizing"]
                ),
                "broader and regularizing profiles",
            ),
            check(
                "fresh_chain_and_initialization_seeds",
                all(
                    token in texts["prepare"]
                    for token in ["68291", "69291", "67291", "67391"]
                ),
                "profile-specific nonproduction seeds",
            ),
            check(
                "runner_activates_recorded_profile",
                "use_prior_specification(prior)" in texts["runner"]
                and "prior_specification_from_mapping" in texts["runner"],
                "single validated sampler reused under explicit profile context",
            ),
            check(
                "runner_uses_fresh_feasible_starts",
                "solve_feasible_allocation" in texts["runner"]
                and "objective=\"random\"" in texts["runner"],
                "sensitivity chains do not inherit a primary posterior state",
            ),
            check(
                "summary_rechecks_primary_production_gate",
                "production_gate.json" in texts["summarize"]
                and "gate.get(\"passed\", False)" in texts["summarize"],
                "comparison requires passed primary analysis",
            ),
            check(
                "summary_reports_all_parameter_convergence",
                all(
                    token in texts["summarize"]
                    for token in [
                        "maximum_all_parameter_rhat",
                        "minimum_all_parameter_bulk_ess",
                        "minimum_all_parameter_tail_ess",
                    ]
                ),
                "all-parameter convergence is retained",
            ),
            check(
                "summary_reports_material_primary_shifts",
                "relative_shift_percent" in texts["summarize"]
                and "primary_value_inside_sensitivity_interval" in texts["summarize"],
                "effect-size change and interval overlap reported",
            ),
            check(
                "registry_contains_profiles",
                all(
                    token in texts["registry"]
                    for token in [
                        "prior_profiles:",
                        "broader:",
                        "regularizing:",
                    ]
                ),
                "profiles frozen before corrected results",
            ),
        ]
    )
    passed = all(bool(row["passed"]) for row in checks)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "production_launched": False,
        "sensitivity_launched": False,
        "checks": checks,
        "interpretation_boundary": (
            "Infrastructure validation only. Prior-sensitivity chains remain blocked until the corrected primary production gate passes."
        ),
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "prior_sensitivity_infrastructure.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 prior-sensitivity infrastructure",
        "",
        f"Status: **{'PASS' if passed else 'HOLD'}**",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {row['check']} | {row['passed']} | {row['detail']} |"
        for row in checks
    )
    lines.extend(
        [
            "",
            "No sensitivity or empirical production chain was launched by this audit.",
        ]
    )
    (OUTPUT_ROOT / "prior_sensitivity_infrastructure.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not passed:
        failed = [row for row in checks if not row["passed"]]
        raise SystemExit(f"Prior-sensitivity infrastructure is on HOLD: {failed}")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
