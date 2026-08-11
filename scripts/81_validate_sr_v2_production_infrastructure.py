from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "scientific_reports_v2" / "production_infrastructure_smoke"
PYTHON_FILES = [
    ROOT / "scripts" / "75_prepare_sr_v2_production.py",
    ROOT / "scripts" / "76_run_sr_v2_production_chain.py",
    ROOT / "scripts" / "77_merge_sr_v2_production.py",
    ROOT / "scripts" / "78_gate_sr_v2_production.py",
]
SHELL_FILES = [
    ROOT / "hpc" / "wahab" / "stage_sr_v2_to_scratch.sh",
    ROOT / "hpc" / "wahab" / "sync_sr_v2_results_home.sh",
    ROOT / "hpc" / "wahab" / "submit_sr_v2_production.sh",
    ROOT / "hpc" / "wahab" / "slurm" / "60_sr_v2_production_chain_array.sbatch",
    ROOT / "hpc" / "wahab" / "slurm" / "61_sr_v2_finalize_production.sbatch",
]
WINDOWS_DRIVE_PATH = re.compile(r"(?im)(?:^|[\s\"'=(:])(?:[a-z]:[\\/])")


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def contains_windows_drive_path(text: str) -> bool:
    """Return True only for a drive-qualified path such as a Windows drive root."""

    return WINDOWS_DRIVE_PATH.search(text) is not None


def main() -> None:
    rows: list[dict[str, object]] = []
    for path in PYTHON_FILES:
        text = path.read_text(encoding="utf-8")
        try:
            ast.parse(text, filename=str(path))
            parsed = True
            detail = "AST parse passed"
        except SyntaxError as exc:
            parsed = False
            detail = repr(exc)
        rows.append(check(f"python_ast:{path.name}", parsed, detail))
        rows.append(
            check(
                f"isolated_output_namespace:{path.name}",
                "outputs/scientific_reports_v2/production_8chain" in text
                or "scientific_reports_v2\" / \"production_8chain" in text,
                "Scientific Reports v2 production namespace present",
            )
        )

    submit = (ROOT / "hpc" / "wahab" / "submit_sr_v2_production.sh").read_text(encoding="utf-8")
    stage = (ROOT / "hpc" / "wahab" / "stage_sr_v2_to_scratch.sh").read_text(encoding="utf-8")
    array = (ROOT / "hpc" / "wahab" / "slurm" / "60_sr_v2_production_chain_array.sbatch").read_text(encoding="utf-8")
    finalize = (ROOT / "hpc" / "wahab" / "slurm" / "61_sr_v2_finalize_production.sbatch").read_text(encoding="utf-8")
    sync = (ROOT / "hpc" / "wahab" / "sync_sr_v2_results_home.sh").read_text(encoding="utf-8")

    rows.extend(
        [
            check("array_has_eight_chains", "#SBATCH --array=1-8%8" in array, "expected 1-8%8"),
            check("array_uses_main_partition", "#SBATCH --partition=main" in array, "main partition"),
            check("array_has_no_gpu_request", "--gres" not in array.lower() and "gpu" not in array.lower(), "CPU-only"),
            check("array_uses_v2_runner", "scripts/76_run_sr_v2_production_chain.py" in array, "v2 chain runner"),
            check("array_uses_v2_sync", "sync_sr_v2_results_home.sh" in array, "isolated result sync"),
            check("finalize_uses_v2_merger", "scripts/77_merge_sr_v2_production.py" in finalize, "v2 merger"),
            check("finalize_uses_v2_gate", "scripts/78_gate_sr_v2_production.py" in finalize, "v2 gate"),
            check("submission_has_afterok_dependency", "afterok:${production_job}" in submit, "fail-closed dependency"),
            check(
                "submission_prepares_before_v2_staging",
                submit.index("scripts/75_prepare_sr_v2_production.py")
                < submit.index("stage_sr_v2_to_scratch.sh"),
                "prepare then stage frozen v2 evidence",
            ),
            check(
                "submission_uses_v2_staging",
                "stage_sr_v2_to_scratch.sh" in submit and "bash hpc/wahab/stage_to_scratch.sh" not in submit,
                "dedicated v2 staging path",
            ),
            check(
                "staging_calls_base_code_stage",
                "stage_to_scratch.sh" in stage,
                "base code/data stage retained",
            ),
            check(
                "staging_includes_validation_evidence",
                all(
                    token in stage
                    for token in [
                        "exact_kernel_validation",
                        "random_exact_validation",
                        "constraint_geometry",
                        "extended_joint_pilot",
                        "calibration_design_smoke",
                        "calibration_pilot/replicate_001",
                    ]
                ),
                "all preproduction validation evidence staged",
            ),
            check(
                "staging_includes_prepared_config",
                "production_8chain/config" in stage
                and "production_preparation_manifest.json" in stage,
                "frozen production config and manifest staged",
            ),
            check("sync_scope_is_v2_only", 'RELATIVE_ROOT="outputs/scientific_reports_v2/production_8chain"' in sync, "v2-only relative root"),
            check("legacy_sync_not_used", "sync_results_home.sh" not in array and "sync_results_home.sh" not in finalize, "legacy sync excluded"),
        ]
    )

    preparation = (ROOT / "scripts" / "75_prepare_sr_v2_production.py").read_text(encoding="utf-8")
    gate = (ROOT / "scripts" / "78_gate_sr_v2_production.py").read_text(encoding="utf-8")
    rows.extend(
        [
            check("baseline_commit_guard", "BASELINE_COMMIT" in preparation and "v1.1.1" in preparation, "tag and commit guard"),
            check("branch_guard", "EXPECTED_BRANCH" in preparation, "scientific-reports-v2 branch guard"),
            check("extended_pilot_guard", "extended_joint_pilot" in preparation and "pilot_pass" in preparation, "extended pilot required"),
            check("calibration_guard", "calibration_pilot_summary.json" in preparation and "computational_gate_pass" in preparation, "truth-known calibration required"),
            check("new_random_seeds", "58291" in preparation and "58298" in preparation, "new v2 chain seeds"),
            check("new_initialization_seeds", "57291" in preparation and "57298" in preparation, "new dispersed-start seeds"),
            check("all_parameter_gate", "rhat_max_all" in gate and "ess_bulk_min_all" in gate and "ess_tail_min_all" in gate, "all-parameter convergence gate"),
            check("latent_summary_gate", "latent_summary_rhat" in gate and "latent_summary_bulk_ess" in gate, "latent aggregate convergence gate"),
            check("validation_gate", "zero_constraint_failures" in gate, "zero-failure constraint gate"),
        ]
    )

    for path in SHELL_FILES:
        text = path.read_text(encoding="utf-8")
        rows.append(check(f"shell_has_shebang:{path.name}", text.startswith("#!/bin/bash -l"), "login-shell shebang"))
        rows.append(check(f"shell_fail_closed:{path.name}", "set -euo pipefail" in text, "strict shell mode"))
        has_windows_path = contains_windows_drive_path(text)
        rows.append(
            check(
                f"shell_no_windows_path:{path.name}",
                not has_windows_path,
                "portable paths" if not has_windows_path else "drive-qualified Windows path detected",
            )
        )

    # Parse any frozen configuration already present without requiring it to exist before the gates pass.
    config = ROOT / "hpc" / "wahab" / "configs" / "sr_v2_production.yaml"
    if config.exists():
        payload = yaml.safe_load(config.read_text(encoding="utf-8"))
        rows.append(check("frozen_config_eight_chains", int(payload["run"]["n_chains"]) == 8, str(payload["run"]["n_chains"])))
        rows.append(check("frozen_config_expected_draws", (int(payload["run"]["n_iter"]) - int(payload["run"]["burn_in"])) // int(payload["run"]["thin"]) == 4500, "4,500 draws per chain"))
    else:
        rows.append(check("frozen_config_deferred", True, "config correctly deferred until pilot gates pass"))

    passed = all(bool(row["passed"]) for row in rows)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "checks": rows,
        "production_launched": False,
        "interpretation_boundary": "Infrastructure audit only; no production chain was launched.",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "production_infrastructure_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 production infrastructure smoke audit",
        "",
        f"Final status: **{'PASS' if passed else 'HOLD'}**",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {row['check']} | {row['passed']} | {row['detail']} |" for row in rows)
    lines.extend(
        [
            "",
            "No production chain was launched. The audit checks namespace isolation, required-evidence staging, fail-closed gates, frozen-baseline guards, Slurm wiring, and syntax-level integrity.",
        ]
    )
    (OUTPUT / "production_infrastructure_smoke.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit("Scientific Reports v2 production infrastructure audit failed.")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
