from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from submission_viz.io import load_config  # noqa: E402
from submission_viz.manuscript_text import build_main_manuscript  # noqa: E402


def main() -> None:
    config = load_config()
    outputs = build_main_manuscript(config)
    for path in outputs.values():
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
