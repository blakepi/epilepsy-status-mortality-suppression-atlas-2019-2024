from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.summaries import summarize_all  # noqa: E402


def main() -> None:
    outputs = summarize_all()
    print("figures_and_tables_refreshed=1")
    print(f"primary_irrs={outputs['primary_irrs']}")


if __name__ == "__main__":
    main()
