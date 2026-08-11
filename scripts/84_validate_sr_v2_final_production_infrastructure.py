from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "scientific_reports_v2" / "final_production_infrastructure"
PYTHON_FILES = [
    ROOT / "scripts" / "82_prepare_sr_v2_production_final.py",
    ROOT / "scripts" / "76_run_sr_v2_production_chain.py",
    ROOT / "scripts" / "77_merge_sr_v2_production.py",
    ROOT / "scripts" / "83_gate_sr_v2_production_final.py",
]
SHELL_FILES = [
    ROOT / "hpc" / "wahab" / "stage_sr_v2_to_scratch_final.sh",
    ROOT / "hpc" / "wahab" / "sync_sr_v2_results_home.sh",
    ROOT / "hpc" / "wahab" / "submit_sr_v2_production_final.sh",
    ROOT / "hpc" / "wahab" / "slurm" / "60_sr_v2_production_chain_array.sbatch",
    ROOT / "hpc" / "wahab" / "slurm" / "62_sr_v2_finalize_production_final.sbatch",
]
WINDOWS_DRIVE_PATH = re.compile(r"(?im)(?:^|[\s\"'=(:])(?:[a-z]:[\\/])")


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    checks: list[dict[str, object]] = []
    for path in PYTHON_FILES:
        text = path.read_text(encoding="utf-8")
        try:
            ast.parse(text, filename=str(path))
            parsed = True
            detail = "AST parse passed"
        except SyntaxError as exc:
            parsed = False
            detail = repr(exc)
        checks.append(check(f"python_ast:{path.name}", parsed, detail))
        checks.append(
            check(
                f"v2_namespace:{path.name}",
                "scientific_reports_v2" in text and "production_8chain" in text,
                "isolated corrected production namespace",
            )
        )

    prepare = PYTHON_FILES[0].read_text(encoding="utf-8")
    gate = PYTHON_FILES[3].read_text(encoding="utf-8")
    submit = (ROOT / "hpc" / "wahab" / "submit_sr_v2_production_final.sh").read_text(encoding="utf-8")
    stage = (ROOT / "hpc" / "wahab" / "stage_sr_v2_to_scratch_final.sh").read_text(encoding="utf-8")
    array = (ROOT / "hpc" / "wahab" / "slurm" / "60_sr_v2_production_chain_array.sbatch").read_text(encoding="utf-8")
    finalize = (ROOT / "hpc" / "wahab" / "slurm" / "62_sr_v2_finalize_production_final.sbatch").read_text(encoding="utf-8")

    checks.extend(
        [
            check(
                "frozen_v111_guard",
                "BASELINE_COMMIT" in prepare and "v1.1.1" in prepare,
                "immutable v1.1.1 tag and commit required",
            ),
            check(
                "scientific_reports_branch_guard",
                "EXPECTED_BRANCH" in prepare and "scientific-reports-v2" in prepare,
                "final preparation restricted to v2 branch",
            ),
            check(
                "exact_kernel_gates_required",
                "exact_kernel_validation" in prepare
                and "random_exact_validation" in prepare,
                "deterministic and randomized exact-kernel evidence required",
            ),
            check(
                "constraint_geometry_required",
                all(token in prepare for token in ["9695", "1256", "8439"]),
                "audited latent-variable rank and nullity required",
            ),
            check(
                "extended_real_pilot_required",
                "extended_joint_summary.json" in prepare and "pilot_pass" in prepare,
                "extended real-data tuning gate required",
            ),
            check(
                "tuned_calibration_required",
                "replicate_001_extended" in prepare
                and "calibration_extension_summary.json" in prepare
                and "computational_gate_pass" in prepare,
                "tuned truth-known calibration gate required",
            ),
            check(
                "prespecified_chain_seed_range",
                "list(range(58291, 58299))" in prepare,
                "chain seeds 58291–58298",
            ),
            check(
                "prespecified_initialization_seed_range",
                "list(range(57291, 57299))" in prepare,
                "dispersed initialization seeds 57291–57298",
            ),
            check(
                "eight_chain_array",
                "#SBATCH --array=1-8%8" in array,
                "eight independent production jobs",
            ),
            check(
                "cpu_only_array",
                "#SBATCH --partition=main" in array
                and "--gres" not in array.lower()
                and "gpu" not in array.lower(),
                "CPU-only main-partition production",
            ),
            check(
                "final_submit_uses_final_prepare",
                "scripts/82_prepare_sr_v2_production_final.py" in submit,
                "final gate-aware preparation",
            ),
            check(
                "final_submit_uses_final_stage",
                "stage_sr_v2_to_scratch_final.sh" in submit,
                "tuned validation evidence staged",
            ),
            check(
                "final_submit_fail_closed_dependency",
                "afterok:${production_job}" in submit,
                "finalization runs only after successful array",
            ),
            check(
                "final_submit_uses_final_gate_job",
                "62_sr_v2_finalize_production_final.sbatch" in submit,
                "final calibrated gate job selected",
            ),
            check(
                "final_stage_includes_tuned_calibration",
                "replicate_001_extended" in stage,
                "tuned calibration evidence copied to scratch",
            ),
            check(
                "finalize_merges_then_gates",
                finalize.index("scripts/77_merge_sr_v2_production.py")
                < finalize.index("scripts/83_gate_sr_v2_production_final.py"),
                "merge precedes fail-closed gate",
            ),
            check(
                "all_parameter_gate",
                all(
                    token in gate
                    for token in [
                        "all_parameter_rhat",
                        "all_parameter_bulk_ess",
                        "all_parameter_tail_ess",
                        "primary_bulk_ess",
                        "primary_tail_ess",
                    ]
                ),
                "all-parameter and primary ESS thresholds enforced",
            ),
            check(
                "latent_summary_gate",
                all(
                    token in gate
                    for token in [
                        "latent_summary_rhat",
                        "latent_summary_bulk_ess",
                        "latent_summary_tail_ess",
                    ]
                ),
                "representative latent summaries gated",
            ),
            check(
                "constraint_validation_gate",
                "zero_constraint_failures" in gate,
                "all retained latent states must satisfy constraints",
            ),
            check(
                "final_gate_requires_tuned_calibration",
                "tuned_calibration_extension_gate" in gate
                and "replicate_001_extended" in gate,
                "final production gate rechecks tuned calibration",
            ),
        ]
    )

    for path in SHELL_FILES:
        text = path.read_text(encoding="utf-8")
        checks.append(
            check(
                f"shell_shebang:{path.name}",
                text.startswith("#!/bin/bash -l"),
                "login-shell shebang",
            )
        )
        checks.append(
            check(
                f"shell_strict_mode:{path.name}",
                "set -euo pipefail" in text,
                "fail-closed shell mode",
            )
        )
        checks.append(
            check(
                f"shell_portable_paths:{path.name}",
                WINDOWS_DRIVE_PATH.search(text) is None,
                "no drive-qualified Windows path",
            )
        )

    passed = all(bool(row["passed"]) for row in checks)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "production_launched": False,
        "checks": checks,
        "authoritative_submission_helper": "hpc/wahab/submit_sr_v2_production_final.sh",
        "interpretation_boundary": (
            "Infrastructure validation only. No corrected empirical production chain was launched."
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "final_production_infrastructure.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 final production infrastructure audit",
        "",
        f"Final status: **{'PASS' if passed else 'HOLD'}**",
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
            "Authoritative launch helper: `hpc/wahab/submit_sr_v2_production_final.sh`.",
            "",
            "No production chain was launched by this audit.",
        ]
    )
    (OUTPUT / "final_production_infrastructure.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not passed:
        failed = [row for row in checks if not row["passed"]]
        raise SystemExit(f"Final v2 infrastructure is on HOLD: {failed}")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
