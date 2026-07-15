from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.summaries import summarize_all  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", choices=["implementation_local", "hpc_nonfinal", "hpc_final"], default="implementation_local")
    parser.add_argument("--gate-json", default="outputs/bayes_constrained/hpc/convergence_gate.json")
    args = parser.parse_args()
    gate_path = ROOT / args.gate_json
    if args.status == "hpc_final":
        if not gate_path.exists():
            raise SystemExit(f"Refusing hpc_final manuscript generation; missing convergence gate: {gate_path}")
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("action") != "finalize" or not gate.get("passed"):
            raise SystemExit(f"Refusing hpc_final manuscript generation; convergence gate action is {gate.get('action')!r}.")
    if args.status == "hpc_nonfinal":
        note = ROOT / "outputs" / "bayes_constrained" / "hpc" / "hpc_nonfinal_manuscript_status.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(
            "# HPC Non-Final Manuscript Status\n\n"
            "The Wahab run did not pass the convergence gate. Final inferential manuscript files were not created.\n",
            encoding="utf-8",
        )
        print(f"nonfinal_status={note.relative_to(ROOT)}")
        return
    outputs = summarize_all()
    if args.status == "hpc_final":
        final_main = ROOT / "manuscript" / "manuscript_main_bayes_constrained_HPC_FINAL.docx"
        final_supp = ROOT / "supplement" / "supplement_bayes_constrained_HPC_FINAL.docx"
        shutil.copy2(ROOT / outputs["manuscript"], final_main)
        shutil.copy2(ROOT / outputs["supplement"], final_supp)
        print(f"hpc_final_manuscript={final_main.relative_to(ROOT)}")
        print(f"hpc_final_supplement={final_supp.relative_to(ROOT)}")
    print(f"manuscript={outputs['manuscript']}")
    print(f"supplement={outputs['supplement']}")
    print(f"run_report={outputs['run_report']}")


if __name__ == "__main__":
    main()
