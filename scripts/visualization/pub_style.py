from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
from PIL import Image


FONT_FAMILY = ["Aptos", "Segoe UI", "Arial", "DejaVu Sans", "sans-serif"]
MONO_FONT_FAMILY = ["Consolas", "DejaVu Sans Mono", "monospace"]

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

NEUTRALS = {
    "open": "#FFFFFF",
    "xlight": "#F4F5F7",
    "light": "#E2E5EA",
    "base": "#C5CAD3",
    "mid": "#7A828F",
    "dark": "#464C55",
}

PALETTES = {
    "blue": {"xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}

SUPPRESSION_STATUS_PALETTE = {
    "exact": PALETTES["blue"]["mid"],
    "suppressed_1_9": PALETTES["gold"]["mid"],
    "zero": NEUTRALS["base"],
    "missing_unmatched": NEUTRALS["xlight"],
}

RATE_BIN_PALETTE = {
    "<2": "#EEF5F2",
    "2-3": "#CDE3DB",
    "3-4": "#93C7B6",
    "4-5": "#4F9E91",
    ">=5": "#1F6F78",
}

SCENARIO_TIER_PALETTE = {
    "visible-only": PALETTES["blue"]["mid"],
    "total-preserving residual allocation": PALETTES["olive"]["mid"],
    "fixed-value stress test": PALETTES["orange"]["mid"],
    "interval model": PALETTES["pink"]["mid"],
}


def apply_pub_style() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "savefig.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "axes.linewidth": 0.7,
            "font.family": "sans-serif",
            "font.sans-serif": FONT_FAMILY,
            "font.monospace": MONO_FONT_FAMILY,
            "font.size": 8,
            "legend.fontsize": 7,
            "legend.title_fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.55,
            "grid.linestyle": "-",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_figure_bundle(
    fig: plt.Figure,
    stem: str,
    outdir: Path,
    width_in: float,
    height_in: float,
    png_dpi: int = 600,
    *,
    figure_number: str,
    source_script: str,
    input_data_files: Iterable[str | Path],
    tiff_dpi: int = 1000,
    include_eps: bool = True,
) -> list[dict]:
    outdir.mkdir(parents=True, exist_ok=True)
    fig.set_size_inches(width_in, height_in, forward=True)
    records: list[dict] = []
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    export_specs = [
        ("png", png_dpi),
        ("svg", None),
        ("pdf", None),
        ("eps", None),
        ("tiff", tiff_dpi),
    ]
    if not include_eps:
        export_specs = [spec for spec in export_specs if spec[0] != "eps"]
    for suffix, raster_dpi in export_specs:
        path = outdir / f"{stem}.{suffix}"
        save_kwargs = {"bbox_inches": "tight", "facecolor": TOKENS["surface"]}
        if raster_dpi:
            save_kwargs["dpi"] = raster_dpi
        fig.savefig(path, **save_kwargs)
        records.append(
            {
                "figure_number": figure_number,
                "output_filename": path.name,
                "relative_path": path.as_posix(),
                "format": suffix,
                "width_in": width_in,
                "height_in": height_in,
                "dpi": raster_dpi or "",
                "source_script": source_script,
                "input_data_files": ";".join(str(Path(p)) for p in input_data_files),
                "sha256": sha256_file(path),
                "generated_at_utc": generated_at,
                "bytes": path.stat().st_size,
            }
        )
    return records


def write_figure_manifest(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "figure_number",
        "output_filename",
        "relative_path",
        "format",
        "width_in",
        "height_in",
        "dpi",
        "source_script",
        "input_data_files",
        "sha256",
        "generated_at_utc",
        "bytes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def validate_figure_outputs(
    manifest_records: list[dict],
    *,
    expected_figures: Iterable[str] = ("1", "2", "3", "4"),
    min_png_dpi: int = 600,
    min_tiff_dpi: int = 500,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    by_fig: dict[str, set[str]] = {}
    for record in manifest_records:
        by_fig.setdefault(str(record["figure_number"]), set()).add(str(record["format"]).lower())
        path = Path(record["relative_path"])
        if not path.exists():
            errors.append(f"Missing output: {path}")
            continue
        if path.stat().st_size <= 0:
            errors.append(f"Empty output: {path}")
        if path.name.endswith("_tight.png") or path.name in {"suppression_bounds_forest_plot.png", "map3_suppression_aware_predicted_rates.png"}:
            errors.append(f"Old or intermediate filename in manifest: {path.name}")
        if record["format"] == "png":
            with Image.open(path) as image:
                dpi = image.info.get("dpi", (0, 0))[0] or int(record.get("dpi") or 0)
                if dpi < min_png_dpi - 2:
                    errors.append(f"Low-resolution PNG metadata for {path.name}: {dpi}")
                if image.width < 1600 or image.height < 1000:
                    errors.append(f"PNG pixel dimensions are too small for {path.name}: {image.width}x{image.height}")
        if record["format"] == "tiff":
            with Image.open(path) as image:
                dpi = image.info.get("dpi", (0, 0))[0] or int(record.get("dpi") or 0)
                if dpi < min_tiff_dpi - 2:
                    errors.append(f"Low-resolution TIFF metadata for {path.name}: {dpi}")
                if image.width < 2000 or image.height < 1500:
                    errors.append(f"TIFF pixel dimensions are too small for {path.name}: {image.width}x{image.height}")
    for figure_number in expected_figures:
        formats = by_fig.get(str(figure_number), set())
        missing = {"png", "svg", "pdf", "tiff"} - formats
        if missing:
            errors.append(f"Figure {figure_number} missing formats: {sorted(missing)}")
    return not errors, errors
