from __future__ import annotations

import importlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = PROJECT_ROOT / "data" / "raw" / "geography" / "plotly_geojson_counties_fips.json"
REPORT_DIR = PROJECT_ROOT / "reports" / "viz_environment_check"
PUBLICATION_FIGURE_DIR = PROJECT_ROOT / "manuscript" / "publication_figures"
FINAL_FIGURE_DIR = PROJECT_ROOT / "manuscript" / "final_submission_ready" / "figures"

REQUIRED_IMPORTS = {
    "matplotlib": "matplotlib",
    "pandas": "pandas",
    "numpy": "numpy",
    "scipy": "scipy",
    "statsmodels": "statsmodels",
    "geopandas": "geopandas",
    "shapely": "shapely",
    "pyproj": "pyproj",
    "pyogrio": "pyogrio",
    "mapclassify": "mapclassify",
    "colorspacious": "colorspacious",
    "pillow": "PIL",
    "lxml": "lxml",
    "python-docx": "docx",
    "openpyxl": "openpyxl",
    "pytest": "pytest",
}

OPTIONAL_IMPORTS = {
    "cairosvg": "cairosvg",
    "svgutils": "svgutils",
    "great-tables": "great_tables",
    "kaleido": "kaleido",
    "imageio": "imageio",
}


def package_version(dist_name: str, module) -> str:
    version = getattr(module, "__version__", None)
    if version:
        return str(version)
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def import_packages() -> tuple[list[dict], list[dict]]:
    required_rows: list[dict] = []
    optional_rows: list[dict] = []
    errors: list[str] = []
    for dist_name, import_name in REQUIRED_IMPORTS.items():
        try:
            module = importlib.import_module(import_name)
            required_rows.append(
                {
                    "package": dist_name,
                    "import": import_name,
                    "version": package_version(dist_name, module),
                    "status": "ok",
                }
            )
        except Exception as exc:
            required_rows.append({"package": dist_name, "import": import_name, "version": "", "status": f"missing: {exc}"})
            errors.append(f"{dist_name}: {exc}")
    for dist_name, import_name in OPTIONAL_IMPORTS.items():
        try:
            module = importlib.import_module(import_name)
            optional_rows.append(
                {
                    "package": dist_name,
                    "import": import_name,
                    "version": package_version(dist_name, module),
                    "status": "ok",
                }
            )
        except Exception as exc:
            optional_rows.append({"package": dist_name, "import": import_name, "version": "", "status": f"optional_missing: {exc}"})
    return required_rows, optional_rows


def check_ruff() -> dict:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        return {
            "package": "ruff",
            "import": "python -m ruff",
            "version": completed.stdout.strip() or completed.stderr.strip(),
            "status": "ok" if completed.returncode == 0 else f"missing: {completed.stderr.strip()}",
        }
    except Exception as exc:
        return {"package": "ruff", "import": "python -m ruff", "version": "", "status": f"missing: {exc}"}


def check_matplotlib_formats() -> list[dict]:
    import matplotlib.pyplot as plt

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(2.5, 1.5))
    ax.plot([0, 1, 2], [0, 1, 0], color="#5477C4", linewidth=1.2)
    ax.set_title("Format smoke test")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    rows = []
    for suffix in ["png", "svg", "pdf"]:
        path = REPORT_DIR / f"matplotlib_smoke_test.{suffix}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        rows.append({"format": suffix, "path": str(path), "bytes": path.stat().st_size, "status": "ok" if path.stat().st_size > 0 else "empty"})
    plt.close(fig)
    return rows


def check_geopandas() -> dict:
    import geopandas as gpd

    if not GEOMETRY_PATH.exists():
        raise FileNotFoundError(GEOMETRY_PATH)
    gdf = gpd.read_file(GEOMETRY_PATH, engine="pyogrio")
    if gdf.empty:
        raise ValueError("GeoPandas read returned zero county features.")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    projected = gdf.to_crs("EPSG:5070")
    return {
        "path": str(GEOMETRY_PATH),
        "feature_count": int(len(gdf)),
        "source_crs": str(gdf.crs),
        "projected_crs": str(projected.crs),
        "status": "ok",
    }


def ensure_output_dirs() -> list[dict]:
    rows = []
    for path in [REPORT_DIR, PUBLICATION_FIGURE_DIR, FINAL_FIGURE_DIR, PROJECT_ROOT / "manuscript" / "final_submission_ready" / "reports"]:
        path.mkdir(parents=True, exist_ok=True)
        rows.append({"path": str(path), "exists": path.exists()})
    return rows


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    required_rows, optional_rows = import_packages()
    required_rows.append(check_ruff())
    format_rows = check_matplotlib_formats()
    geo_row = check_geopandas()
    output_dirs = ensure_output_dirs()

    payload = {
        "python": sys.executable,
        "required_packages": required_rows,
        "optional_packages": optional_rows,
        "matplotlib_format_checks": format_rows,
        "geopandas_geometry_check": geo_row,
        "output_dirs": output_dirs,
    }
    (REPORT_DIR / "viz_environment_check.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))
    failed = [row for row in required_rows if row["status"] != "ok"]
    failed.extend(row for row in format_rows if row["status"] != "ok")
    if geo_row["status"] != "ok":
        failed.append(geo_row)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
