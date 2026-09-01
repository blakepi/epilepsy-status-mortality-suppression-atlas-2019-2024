from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.identifiability import analyze_constraint_geometry, geometry_markdown  # noqa: E402


def main() -> None:
    frame = load_model_frame()
    geometry = analyze_constraint_geometry(frame)
    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "constraint_geometry"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = geometry.to_dict()
    (output_dir / "constraint_geometry.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pd.DataFrame([payload]).to_csv(output_dir / "constraint_geometry.csv", index=False)
    (output_dir / "constraint_geometry.md").write_text(geometry_markdown(geometry), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
