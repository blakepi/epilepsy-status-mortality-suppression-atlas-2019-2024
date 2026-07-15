from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib as mpl
import matplotlib.pyplot as plt


def configure_matplotlib(config: dict | None = None) -> None:
    style = (config or {}).get("style", {})
    font = style.get("font_family", "Arial")
    size = style.get("base_font_size", 10)
    mpl.rcParams.update(
        {
            "font.family": font,
            "font.size": size,
            "axes.titlesize": size + 2,
            "axes.labelsize": size,
            "xtick.labelsize": size - 1,
            "ytick.labelsize": size - 1,
            "legend.fontsize": size - 1,
            "figure.titlesize": size + 3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#E5E7E9",
            "grid.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.bbox": "tight",
        }
    )


def wrap_label(text: str, width: int = 32) -> str:
    return fill(str(text), width=width)


def fmt_num(value, digits: int = 2) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # NaN
            return ""
    except Exception:
        pass
    return f"{float(value):.{digits}f}"


def fmt_ci(low, high, digits: int = 2) -> str:
    return f"{fmt_num(low, digits)}-{fmt_num(high, digits)}"


def save_figure_all(fig: plt.Figure, stem: str, out_dir: Path, config: dict) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dpi = int(config.get("style", {}).get("figure_dpi", 600))
    formats = config.get("style", {}).get("export_formats", ["svg", "pdf", "tiff", "png"])
    written: list[Path] = []
    for ext in formats:
        path = out_dir / f"{stem}.{ext}"
        kwargs = {"dpi": dpi}
        if ext.lower() in {"tif", "tiff"}:
            kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
        fig.savefig(path, **kwargs)
        written.append(path)
    plt.close(fig)
    return written
