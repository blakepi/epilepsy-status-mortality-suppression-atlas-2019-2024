from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
RAW_WONDER = PROJECT_ROOT / "data" / "raw" / "wonder" / "csv"
BAYES_DATA = DATA_PROCESSED / "bayes_constrained"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "bayes_constrained"
TABLE_DIR = PROJECT_ROOT / "tables"
FIGURE_MAIN_DIR = PROJECT_ROOT / "figures" / "main"
FIGURE_SUPP_DIR = PROJECT_ROOT / "figures" / "supplement"
MANUSCRIPT_DIR = PROJECT_ROOT / "manuscript"
SUPPLEMENT_DIR = PROJECT_ROOT / "supplement"
CONFIG_PATH = PROJECT_ROOT / "config" / "bayes_constrained.yaml"


def ensure_bayes_dirs() -> None:
    for path in [
        BAYES_DATA,
        OUTPUT_DIR,
        TABLE_DIR,
        FIGURE_MAIN_DIR,
        FIGURE_SUPP_DIR,
        MANUSCRIPT_DIR,
        SUPPLEMENT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
