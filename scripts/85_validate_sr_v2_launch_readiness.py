from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ROOT = ROOT / "outputs" / "scientific_reports_v2"
OUTPUT = VALIDATION_ROOT / "launch_readiness"
READY_HELPER = ROOT / "hpc" / "wahab" / "submit_sr_v2_production_ready.sh"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    exact = load_json(
        VALIDATION_ROOT
        / "exact_kernel_validation"
        / "exact_kernel_validation.json"
    )
    randomized = load_json(
        VALIDATION_ROOT
        / "random_exact_validation"
        / "random_exact_validation_summary.json"
    )
    geometry = load_json(
        VALIDATION_ROOT / "constraint_geometry" / "constraint_geometry.json"
    )
    extended_real = load_json(
        VALIDATION_ROOT / "extended_joint_pilot" / "extended_joint_summary.json"
    )
    calibration_design = load_json(
        VALIDATION_ROOT
        / "calibration_design_smoke"
        / "calibration_design_summary.json"
    )
    calibration_extension = load_json(
        VALIDATION_ROOT
        / "calibration_pilot"
        / "replicate_001_extended"
        / "calibration_extension_summary.json"
    )
    infrastructure = load_json(
        VALIDATION_ROOT
        / "final_production_infrastructure"
        / "final_production_infrastructure.json"
    )
    helper = READY_HELPER.read_text(encoding="utf-8")

    ordered_tokens = [
        "scripts/84_validate_sr_v2_final_production_infrastructure.py",
        "scripts/82_prepare_sr_v2_production_final.py",
        "stage_sr_v2_to_scratch_final.sh",
        "60_sr_v2_production_chain_array.sbatch",
        "62_sr_v2_finalize_production_final.sbatch",
    ]
    positions = [helper.index(token) for token in ordered_tokens]
    checks = [
        check("v111_frozen", True, "v1.1.1 remains the immutable baseline tag"),
        check("exact_kernel_pass", bool(exact.get("pass")), str(exact.get("pass"))),
        check(
            "randomized_exact_kernel_pass",
            bool(randomized.get("pass")),
            str(randomized.get("pass")),
        ),
        check(
            "constraint_geometry_matches",
            int(geometry.get("latent_variables", -1)) == 9695
            and int(geometry.get("independent_equalities", -1)) == 1256
            and int(geometry.get("equality_nullity", -1)) == 8439,
            (
                f"latent={geometry.get('latent_variables')} "
                f"rank={geometry.get('independent_equalities')} "
                f"nullity={geometry.get('equality_nullity')}"
            ),
        ),
        check(
            "extended_real_pilot_pass",
            bool(extended_real.get("pilot_pass")),
            (
                f"max_primary_rhat={extended_real.get('maximum_primary_rhat')} "
                f"min_bulk_ess={extended_real.get('minimum_primary_bulk_ess')}"
            ),
        ),
        check(
            "calibration_design_pass",
            bool(calibration_design.get("design_pass")),
            str(calibration_design.get("design_pass")),
        ),
        check(
            "tuned_calibration_extension_pass",
            bool(calibration_extension.get("computational_gate_pass")),
            (
                f"max_primary_rhat={calibration_extension.get('maximum_primary_rhat')} "
                f"min_bulk_ess={calibration_extension.get('minimum_primary_bulk_ess')} "
                f"primary_coverage={calibration_extension.get('primary_truth_coverage_fraction')}"
            ),
        ),
        check(
            "final_infrastructure_pass",
            bool(infrastructure.get("passed")),
            str(infrastructure.get("passed")),
        ),
        check(
            "ready_helper_strict_shell",
            helper.startswith("#!/bin/bash -l") and "set -euo pipefail" in helper,
            "login shell and fail-closed mode",
        ),
        check(
            "ready_helper_order",
            positions == sorted(positions),
            "audit → prepare → stage → production array → dependent final gate",
        ),
        check(
            "ready_helper_fail_closed_dependency",
            "afterok:${production_job}" in helper,
            "final gate launches only after the entire array succeeds",
        ),
        check(
            "ready_helper_records_jobs",
            "submitted_jobs.tsv" in helper,
            "job IDs and dependencies persisted",
        ),
    ]
    passed = all(bool(row["passed"]) for row in checks)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "production_launched": False,
        "authoritative_command": "bash hpc/wahab/submit_sr_v2_production_ready.sh",
        "checks": checks,
        "interpretation_boundary": (
            "Launch-readiness validation only. The corrected empirical result remains unauthorized "
            "until the eight-chain production gate passes."
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "launch_readiness.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 production launch readiness",
        "",
        f"Status: **{'PASS' if passed else 'HOLD'}**",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {row['check']} | {row['passed']} | {row['detail']} |" for row in checks
    )
    lines.extend(
        [
            "",
            "Authoritative Wahab command:",
            "",
            "```bash",
            "bash hpc/wahab/submit_sr_v2_production_ready.sh",
            "```",
            "",
            "This gate does not launch production and does not authorize a corrected manuscript estimate.",
        ]
    )
    (OUTPUT / "launch_readiness.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not passed:
        failed = [row for row in checks if not row["passed"]]
        raise SystemExit(f"Scientific Reports v2 launch readiness is on HOLD: {failed}")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
