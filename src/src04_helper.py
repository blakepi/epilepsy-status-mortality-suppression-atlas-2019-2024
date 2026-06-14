from __future__ import annotations

import pandas as pd


RURAL_ORDER = ["metro_large", "metro_other", "nonmetro_adjacent", "nonmetro_nonadjacent"]
SVI_ORDER = ["Q1_lowest", "Q2", "Q3", "Q4_highest"]


def design_matrix_for_interval(df: pd.DataFrame, include_svi: bool = True) -> tuple[pd.DataFrame, list[str]]:
    x = pd.DataFrame(index=df.index)
    x["Intercept"] = 1.0
    rural = pd.Categorical(df["primary_rurality"], categories=RURAL_ORDER)
    rural_d = pd.get_dummies(rural, prefix="primary_rurality", dtype=float)
    for col in rural_d.columns:
        if col != "primary_rurality_metro_large":
            x[col] = rural_d[col]
    if include_svi:
        svi = pd.Categorical(df["svi_quartile"], categories=SVI_ORDER)
        svi_d = pd.get_dummies(svi, prefix="svi_quartile", dtype=float)
        for col in svi_d.columns:
            if col != "svi_quartile_Q1_lowest":
                x[col] = svi_d[col]
    return x.fillna(0), list(x.columns)
