from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.summaries import summarize_all  # noqa: E402


def main() -> None:
    outputs = summarize_all()
    for key, value in outputs.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
