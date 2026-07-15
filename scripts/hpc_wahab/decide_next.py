from __future__ import annotations

import subprocess
from pathlib import Path

from common import HPC_OUT, PROJECT_ROOT, append_submitted_job, load_json, rel


SLURM_DIR = PROJECT_ROOT / "hpc" / "wahab" / "slurm"


def sbatch(stage: str, script: Path, dependency: str = "", extra_export: str = "") -> str:
    command = ["sbatch", "--parsable"]
    if dependency:
        command.append(f"--dependency={dependency}")
    if extra_export:
        command.append(f"--export=ALL,{extra_export}")
    command.append(str(script))
    job_id = subprocess.check_output(command, cwd=PROJECT_ROOT, text=True).strip().split(";")[0]
    append_submitted_job(stage, job_id, dependency, rel(script))
    return job_id


def main() -> None:
    gate_path = HPC_OUT / "convergence_gate.json"
    if not gate_path.exists():
        raise SystemExit(f"Missing convergence gate: {gate_path}")
    gate = load_json(gate_path)
    action = gate.get("action")
    if action == "extend":
        round_path = HPC_OUT / "extension_round.txt"
        current_round = int(round_path.read_text(encoding="utf-8").strip()) if round_path.exists() and round_path.read_text(encoding="utf-8").strip() else 0
        next_round = current_round + 1
        round_path.write_text(f"{next_round}\n", encoding="utf-8")
        extend = sbatch("extend_chain_array", SLURM_DIR / "35_extend_chain_array.sbatch", extra_export=f"HPC_EXTENSION_ROUND={next_round}")
        summarize = sbatch("summarize_gate_after_extend", SLURM_DIR / "40_summarize_gate.sbatch", dependency=f"afterok:{extend}")
        decide = sbatch("decide_next_after_extend", SLURM_DIR / "45_decide_next.sbatch", dependency=f"afterok:{summarize}")
        sbatch("failure_report_after_extend", SLURM_DIR / "99_failure_report.sbatch", dependency=f"afternotok:{extend}:{summarize}:{decide}")
        print(f"extension_round={next_round}")
        print(f"extend_job={extend}")
    elif action == "finalize":
        finalize = sbatch("finalize_manuscript", SLURM_DIR / "50_finalize_manuscript.sbatch")
        print(f"finalize_job={finalize}")
    elif action == "stop_nonfinal":
        failure = sbatch("nonfinal_failure_report", SLURM_DIR / "99_failure_report.sbatch")
        print(f"failure_report_job={failure}")
    else:
        raise SystemExit(f"Unknown convergence gate action: {action}")


if __name__ == "__main__":
    main()
