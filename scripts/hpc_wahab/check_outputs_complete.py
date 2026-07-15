from __future__ import annotations

import argparse

import pandas as pd

from common import HPC_OUT, expected_success_outputs, nonempty, rel


def check_required_outputs() -> pd.DataFrame:
    rows = []
    for path in expected_success_outputs():
        rows.append({"path": rel(path), "exists": path.exists(), "nonempty": nonempty(path)})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    HPC_OUT.mkdir(parents=True, exist_ok=True)
    result = check_required_outputs()
    out_csv = HPC_OUT / "output_completion_check.csv"
    result.to_csv(out_csv, index=False)
    if args.write_report:
        missing = result[~(result["exists"] & result["nonempty"])]
        lines = ["# Wahab Output Completion Check", "", "| Path | Exists | Nonempty |", "| --- | --- | --- |"]
        for _, row in result.iterrows():
            lines.append(f"| `{row['path']}` | {row['exists']} | {row['nonempty']} |")
        (HPC_OUT / "output_completion_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if not missing.empty:
            print(missing.to_string(index=False))
            raise SystemExit(1)
    print(f"output_completion_check={rel(out_csv)}")


if __name__ == "__main__":
    main()
