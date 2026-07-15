from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import build_model_frame  # noqa: E402
from bayes_constrained.constraints import solve_and_save_initial_allocations  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    frame = build_model_frame()
    seeds = None
    if args.config:
        import yaml

        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = ROOT / config_path
        with config_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
        seeds = config.get("run", {}).get("random_seeds")
    solve_and_save_initial_allocations(frame, seeds=seeds)
    print(f"bayes_model_frame_rows={len(frame)}")
    print("initial_allocations=validated")


if __name__ == "__main__":
    main()
