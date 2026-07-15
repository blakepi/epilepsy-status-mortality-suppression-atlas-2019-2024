from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HPC_OUT = PROJECT_ROOT / "outputs" / "bayes_constrained" / "hpc"
SUBMITTED_JOBS = HPC_OUT / "submitted_jobs.tsv"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def ensure_hpc_out() -> Path:
    HPC_OUT.mkdir(parents=True, exist_ok=True)
    return HPC_OUT


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_submitted_job(stage: str, job_id: str, dependency: str = "", script: str = "") -> None:
    ensure_hpc_out()
    exists = SUBMITTED_JOBS.exists()
    with SUBMITTED_JOBS.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["submitted_at", "stage", "job_id", "dependency", "script"], delimiter="\t")
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
                "stage": stage,
                "job_id": job_id,
                "dependency": dependency,
                "script": script,
            }
        )


def read_submitted_jobs(path: Path = SUBMITTED_JOBS) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nonempty(path: Path) -> bool:
    return path.exists() and (path.is_dir() or path.stat().st_size > 0)


def expected_success_outputs() -> list[Path]:
    return [
        HPC_OUT / "environment_wahab_report.txt",
        HPC_OUT / "submitted_jobs.tsv",
        HPC_OUT / "chain_status_summary.csv",
        HPC_OUT / "convergence_gate.json",
        HPC_OUT / "convergence_gate.md",
        HPC_OUT / "hpc_runtime_summary.csv",
        HPC_OUT / "hpc_constraint_validation_summary.csv",
        HPC_OUT / "hpc_mcmc_diagnostics.csv",
        HPC_OUT / "Wahab_HPC_Run_Plan.md",
        PROJECT_ROOT / "tables" / "bayes_constrained_primary_irrs.csv",
        PROJECT_ROOT / "tables" / "bayes_constrained_primary_irrs.xlsx",
        PROJECT_ROOT / "manuscript" / "manuscript_main_bayes_constrained.md",
        PROJECT_ROOT / "RUN_BAYES_CONSTRAINED_REPORT.md",
    ]


def chain_status_paths(hpc_out: Path = HPC_OUT) -> Iterable[Path]:
    return sorted((hpc_out / "chains").glob("chain_*/chain_status.json"))


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)
