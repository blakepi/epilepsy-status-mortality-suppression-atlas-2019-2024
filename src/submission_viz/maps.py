from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from .io import load_county_summary, rel_path


def load_map_frame(config: dict) -> gpd.GeoDataFrame:
    geo = gpd.read_file(rel_path(config, "county_geojson"))
    geo["county_fips"] = geo["id"].astype(str).str.zfill(5)
    summary = load_county_summary(config).copy()
    summary["county_fips"] = summary["county_fips"].astype(str).str.zfill(5)
    merged = geo.merge(summary, on="county_fips", how="left")
    return merged.to_crs(5070)


def _bins(series: pd.Series, n: int = 5) -> np.ndarray:
    values = series.dropna().astype(float)
    if values.empty:
        return np.array([0, 1])
    qs = np.unique(np.quantile(values, np.linspace(0, 1, n + 1)))
    if len(qs) < 3:
        qs = np.linspace(values.min(), values.max() + 1e-9, n + 1)
    qs[0] = min(qs[0], values.min())
    qs[-1] = max(qs[-1], values.max())
    return qs


def _plot_subset(ax, gdf: gpd.GeoDataFrame, column: str, cmap, norm, title: str | None = None) -> None:
    gdf.plot(
        ax=ax,
        column=column,
        cmap=cmap,
        norm=norm,
        linewidth=0.04,
        edgecolor="#F8F9F9",
        missing_kwds={"color": "#ECEFF1", "edgecolor": "#F8F9F9", "linewidth": 0.03},
    )
    ax.set_axis_off()
    if title:
        ax.set_title(title, loc="left", fontweight="bold", pad=2)


def plot_us_with_insets(
    ax,
    gdf: gpd.GeoDataFrame,
    column: str,
    title: str,
    cmap_name: str = "Blues",
    bins: np.ndarray | None = None,
):
    if bins is None:
        bins = _bins(gdf[column], n=5)
    cmap = plt.get_cmap(cmap_name, len(bins) - 1)
    norm = colors.BoundaryNorm(bins, cmap.N)
    state = gdf["STATE"].astype(str).str.zfill(2)
    main = gdf[~state.isin(["02", "15", "72"])].copy()
    _plot_subset(ax, main, column, cmap, norm, title=title)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    alaska = gdf[state.eq("02") & gdf[column].notna()].copy()
    hawaii = gdf[state.eq("15") & gdf[column].notna()].copy()
    if not alaska.empty:
        ax_ak = inset_axes(ax, width="22%", height="22%", loc="lower left", borderpad=0.7)
        _plot_subset(ax_ak, alaska, column, cmap, norm)
        ax_ak.set_title("AK", fontsize=7, pad=1)
    if not hawaii.empty:
        ax_hi = inset_axes(ax, width="16%", height="16%", loc="lower right", borderpad=0.8)
        _plot_subset(ax_hi, hawaii, column, cmap, norm)
        ax_hi.set_title("HI", fontsize=7, pad=1)
    return sm, bins


def write_map_data(config: dict, out_path: Path) -> Path:
    gdf = load_map_frame(config)
    cols = [
        "county_fips",
        "NAME",
        "STATE",
        "posterior_mean_rate_per_100k",
        "rate_credible_interval_lower_95",
        "rate_credible_interval_upper_95",
        "posterior_probability_rate_exceeds_national_rate",
        "rurality",
        "svi_quartile",
    ]
    available = [c for c in cols if c in gdf.columns]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(gdf[available].drop(columns="geometry", errors="ignore")).to_csv(out_path, index=False)
    return out_path
