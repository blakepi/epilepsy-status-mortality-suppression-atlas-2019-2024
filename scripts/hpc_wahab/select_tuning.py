from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from common import HPC_OUT, PROJECT_ROOT, rel


def score_acceptance(path: Path) -> float:
    if not path.exists():
        return -1.0
    rates = pd.read_csv(path)
    if rates.empty:
        return -1.0
    parameter = rates[rates["type"].eq("parameter")]["acceptance_rate"].dropna()
    count = rates[rates["type"].eq("count_move")]["acceptance_rate"].dropna()
    score = 0.0
    if not parameter.empty:
        score -= float((parameter.sub(0.30).abs()).mean())
    if not count.empty:
        score += float(count.clip(0, 1).mean()) * 0.25
    return score


def main() -> None:
    rows = []
    for chain_dir in sorted((HPC_OUT / "chains").glob("chain_*")):
        status_path = chain_dir / "chain_status.json"
        if not status_path.exists():
            continue
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("mode") != "tune":
            continue
        config_path = chain_dir / "chain_config_resolved.yaml"
        resolved = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        settings = resolved.get("resolved_settings", {})
        rows.append(
            {
                "chain_dir": chain_dir.name,
                "status": status.get("status"),
                "score": score_acceptance(chain_dir / "acceptance_rates.csv"),
                "settings": settings,
            }
        )
    if not rows:
        raise SystemExit("No tuning chain outputs found.")
    candidates = pd.DataFrame([{k: v for k, v in row.items() if k != "settings"} for row in rows])
    out_csv = HPC_OUT / "tuning_selection_summary.csv"
    candidates.sort_values("score", ascending=False).to_csv(out_csv, index=False)
    best = sorted(rows, key=lambda row: row["score"], reverse=True)[0]
    selected = {
        key: best["settings"][key]
        for key in [
            "count_move_sweeps_per_iter",
            "max_count_proposals_per_iter",
            "blocked_refresh_frequency",
            "blocked_refresh_attempts",
            "block_size",
            "move_weights",
            "proposal_scale_multipliers",
        ]
        if key in best["settings"]
    }
    selected["selected_from"] = best["chain_dir"]
    selected["selection_score"] = float(best["score"])
    out_yaml = HPC_OUT / "selected_tuning.yaml"
    out_yaml.write_text(yaml.safe_dump(selected, sort_keys=False), encoding="utf-8")
    print(f"selected_tuning={rel(out_yaml)}")
    print(f"tuning_summary={rel(out_csv)}")


if __name__ == "__main__":
    main()
