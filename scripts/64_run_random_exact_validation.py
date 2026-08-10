from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.random_exact_validation import validate_random_cases  # noqa: E402


def main() -> None:
    results, failures = validate_random_cases(cases=30, seed=20260810)
    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "random_exact_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_dir / "random_exact_validation_cases.csv", index=False)
    summary = {
        "cases": int(len(results)),
        "passed": int(results["passed"].sum()),
        "failed": int((~results["passed"]).sum()),
        "cases_where_legacy_kernel_was_disconnected": int((results["legacy_components"] > 1).sum()),
        "maximum_repaired_row_sum_error": float(results["row_sum_error"].max()),
        "maximum_repaired_stationarity_error": float(results["stationarity_error"].max()),
        "maximum_repaired_detailed_balance_error": float(results["detailed_balance_error"].max()),
        "minimum_feasible_states": int(results["feasible_states"].min()),
        "maximum_feasible_states": int(results["feasible_states"].max()),
        "pass": not failures,
    }
    (output_dir / "random_exact_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        (output_dir / "random_exact_validation_failures.json").write_text(
            json.dumps(failures, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    lines = [
        "# Randomized exact latent-kernel validation",
        "",
        "Thirty reproducible one-state, three-county, three-year bounded fibers were generated with mixtures of exact and interval county-period margins. Every feasible state was enumerated and the exact repaired transition matrix was tested against the exact conditional posterior.",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines.extend(
        [
            "",
            "These randomized finite systems supplement, but do not replace, full-data dispersed-start and latent-movement diagnostics.",
        ]
    )
    (output_dir / "random_exact_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(f"{len(failures)} randomized exact validation case(s) failed.")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
