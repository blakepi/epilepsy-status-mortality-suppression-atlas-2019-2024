from __future__ import annotations

import importlib
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import HPC_OUT, PROJECT_ROOT, rel


REQUIRED_IMPORTS = ["pandas", "numpy", "scipy", "pyarrow", "statsmodels", "matplotlib", "yaml", "docx"]


def check_imports() -> list[dict]:
    rows = []
    for name in REQUIRED_IMPORTS:
        try:
            module = importlib.import_module(name)
            rows.append({"name": name, "available": True, "version": getattr(module, "__version__", "available")})
        except Exception as exc:
            rows.append({"name": name, "available": False, "version": repr(exc)})
    return rows


def command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"not_available: {exc}"


def main() -> None:
    HPC_OUT.mkdir(parents=True, exist_ok=True)
    rows = check_imports()
    missing = [row for row in rows if not row["available"]]
    report = [
        "# Wahab Environment Report",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Project root: `{PROJECT_ROOT}`",
        f"Hostname: `{platform.node()}`",
        f"Python executable: `{sys.executable}`",
        f"Python version: `{sys.version.split()[0]}`",
        f"Platform: `{platform.platform()}`",
        f"PROJECT_HOME: `{os.environ.get('PROJECT_HOME', '')}`",
        f"PROJECT_SCRATCH: `{os.environ.get('PROJECT_SCRATCH', '')}`",
        f"Git commit: `{command_output(['git', 'rev-parse', 'HEAD'])}`",
        f"Loaded modules: `{command_output(['bash', '-lc', 'module list 2>&1'])}`",
        "",
        "## Imports",
        "",
        "| Package | Available | Version or Error |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        report.append(f"| {row['name']} | {row['available']} | {row['version']} |")
    report.extend(
        [
            "",
            "## Lightweight File Checks",
            "",
            f"- requirements-bayes.txt: `{rel(PROJECT_ROOT / 'requirements-bayes.txt')}` exists={Path(PROJECT_ROOT / 'requirements-bayes.txt').exists()}",
            f"- production config: `{rel(PROJECT_ROOT / 'hpc/wahab/configs/bayes_constrained_hpc_production.yaml')}` exists={(PROJECT_ROOT / 'hpc/wahab/configs/bayes_constrained_hpc_production.yaml').exists()}",
            f"- model frame: `{rel(PROJECT_ROOT / 'data/processed/bayes_constrained/model_frame.parquet')}` exists={(PROJECT_ROOT / 'data/processed/bayes_constrained/model_frame.parquet').exists()}",
            "",
            "## Status",
            "",
            "FAILED" if missing else "PASSED",
        ]
    )
    out = HPC_OUT / "environment_wahab_report.txt"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"environment_report={rel(out)}")
    if missing:
        raise SystemExit(f"Missing required imports: {[row['name'] for row in missing]}")


if __name__ == "__main__":
    main()
