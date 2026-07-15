from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from submission_viz.io import load_config  # noqa: E402
from submission_viz.qc import run_qc  # noqa: E402


def main() -> None:
    config = load_config()
    report = run_qc(config, exit_nonzero=True)
    print(f"passed={report['passed']}")
    print("outputs/submission/qc/SUBMISSION_QC_REPORT_FINAL.md")


if __name__ == "__main__":
    main()
