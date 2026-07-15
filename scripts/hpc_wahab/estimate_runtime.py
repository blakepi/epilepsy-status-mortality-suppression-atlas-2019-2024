from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from common import HPC_OUT, chain_status_paths, rel


def main() -> None:
    rows = []
    for status_path in chain_status_paths():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        runtime_path = status_path.parent / "runtime_log.csv"
        runtime_rows = pd.read_csv(runtime_path).to_dict("records") if runtime_path.exists() else []
        rows.append(
            {
                "chain": status_path.parent.name,
                "status": status.get("status"),
                "mode": status.get("mode"),
                "iteration": status.get("iteration"),
                "target_iteration": status.get("target_iteration"),
                "saved_draws": status.get("saved_draws"),
                "runtime_events": len(runtime_rows),
            }
        )
    out = HPC_OUT / "hpc_runtime_summary.csv"
    HPC_OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"runtime_summary={rel(out)}")


if __name__ == "__main__":
    main()
