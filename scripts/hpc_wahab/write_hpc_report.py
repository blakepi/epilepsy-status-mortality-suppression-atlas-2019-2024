from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from common import HPC_OUT, PROJECT_ROOT, load_json, rel


def simple_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    show = frame.head(20).copy()
    cols = list(show.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in show.iterrows():
        values = [str(row[col]).replace("|", "\\|") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", choices=["final", "nonfinal", "auto"], default="auto")
    args = parser.parse_args()
    gate_path = HPC_OUT / "convergence_gate.json"
    gate = load_json(gate_path) if gate_path.exists() else {"passed": False, "action": "missing_gate", "failures": ["missing convergence gate"]}
    status = args.status
    if status == "auto":
        status = "final" if gate.get("action") == "finalize" and gate.get("passed") else "nonfinal"
    diag_path = HPC_OUT / "hpc_mcmc_diagnostics.csv"
    diag_table = simple_markdown_table(pd.read_csv(diag_path)) if diag_path.exists() else "Diagnostics file missing."
    lines = [
        "# Wahab HPC Final Report" if status == "final" else "# Wahab HPC Non-Final Diagnostic Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Gate action: `{gate.get('action')}`",
        f"Gate passed: `{gate.get('passed')}`",
        "",
        "## Gate Failures",
        "",
    ]
    failures = gate.get("failures") or []
    lines.extend([f"- {failure}" for failure in failures] or ["- None"])
    lines.extend(["", "## Diagnostics Preview", "", diag_table, ""])
    if status == "nonfinal":
        lines.append("No final inferential manuscript should be generated from this run.")
    out = HPC_OUT / ("Wahab_HPC_Final_Report.md" if status == "final" else "Wahab_HPC_Nonfinal_Diagnostic_Report.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"hpc_report={rel(out)}")


if __name__ == "__main__":
    main()
