from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from utils import (
    PLOT_DIR,
    PROCESSED_DIR,
    REPORT_DIR,
    TABLE_DIR,
    constrained_allocation,
    md_table,
    numeric,
    rel,
    safe_rate,
    write_text,
)


RURAL_ORDER = ["metro_large", "metro_other", "nonmetro_adjacent", "nonmetro_nonadjacent"]
SVI_ORDER = ["Q1_lowest", "Q2", "Q3", "Q4_highest"]


def design_matrix(df: pd.DataFrame, include_svi: bool = True, include_components: bool = False) -> tuple[pd.DataFrame, list[str]]:
    x = pd.DataFrame(index=df.index)
    x["Intercept"] = 1.0
    cats = pd.Categorical(df["primary_rurality"], categories=RURAL_ORDER)
    dummies = pd.get_dummies(cats, prefix="primary_rurality", dtype=float)
    for col in dummies.columns:
        if col != "primary_rurality_metro_large":
            x[col] = dummies[col]
    if include_svi and "svi_quartile" in df.columns:
        cats_svi = pd.Categorical(df["svi_quartile"], categories=SVI_ORDER)
        svi_d = pd.get_dummies(cats_svi, prefix="svi_quartile", dtype=float)
        for col in svi_d.columns:
            if col != "svi_quartile_Q1_lowest":
                x[col] = svi_d[col]
    numeric_cols = ["acs_pct_age_65_plus", "acs_pct_male"]
    if include_components:
        numeric_cols = [
            "acs_pct_poverty",
            "acs_median_household_income",
            "acs_pct_high_school_grad_or_higher",
            "acs_pct_uninsured",
            "acs_pct_non_hispanic_black",
            "acs_pct_hispanic",
            "acs_pct_age_65_plus",
        ]
    for col in numeric_cols:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            sd = vals.std(skipna=True)
            if sd and not np.isnan(sd):
                x[col + "_z"] = (vals - vals.mean(skipna=True)) / sd
    x = x.replace([np.inf, -np.inf], np.nan).fillna(0)
    return x, list(x.columns)


def fit_model(df: pd.DataFrame, scenario: str, family_name: str, include_svi: bool = True, include_components: bool = False) -> tuple[pd.DataFrame, dict]:
    work = df.copy()
    work = work[pd.to_numeric(work["model_exposure_person_years"], errors="coerce") > 0]
    work = work[pd.to_numeric(work["modeled_deaths"], errors="coerce").notna()]
    work = work[work["primary_rurality"].notna()]
    if include_svi:
        work = work[work["svi_quartile"].notna()]
    if len(work) < 50:
        raise ValueError(f"Too few rows for {scenario}/{family_name}: {len(work)}")
    y = pd.to_numeric(work["modeled_deaths"], errors="coerce").astype(float)
    offset = np.log(pd.to_numeric(work["model_exposure_person_years"], errors="coerce").astype(float))
    x, columns = design_matrix(work, include_svi=include_svi, include_components=include_components)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = sm.GLM(y, x, family=sm.families.NegativeBinomial(alpha=1.0), offset=offset)
            res = model.fit(cov_type="HC0", maxiter=200)
            model_type = "GLM_negative_binomial_alpha1_robust"
        except Exception:
            model = sm.GLM(y, x, family=sm.families.Poisson(), offset=offset)
            res = model.fit(cov_type="HC0", maxiter=200)
            model_type = "GLM_poisson_robust_fallback"

    rows = []
    for term, coef, se, pval in zip(columns, res.params, res.bse, res.pvalues):
        if term == "Intercept":
            continue
        rows.append(
            {
                "scenario": scenario,
                "model_family": family_name,
                "model_type": model_type,
                "term": term,
                "coef": coef,
                "se": se,
                "irr": float(np.exp(coef)),
                "ci_low": float(np.exp(coef - 1.96 * se)),
                "ci_high": float(np.exp(coef + 1.96 * se)),
                "p_value": pval,
                "n_rows": int(len(work)),
                "events": float(y.sum()),
            }
        )
    fit = {
        "scenario": scenario,
        "model_family": family_name,
        "model_type": model_type,
        "n_rows": int(len(work)),
        "events": float(y.sum()),
        "pearson_chi2": float(getattr(res, "pearson_chi2", np.nan)),
        "df_resid": float(getattr(res, "df_resid", np.nan)),
        "overdispersion_ratio": float(getattr(res, "pearson_chi2", np.nan) / max(getattr(res, "df_resid", np.nan), 1)),
        "aic": float(getattr(res, "aic", np.nan)),
    }
    return pd.DataFrame(rows), fit


def make_scenarios(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    base = df[~df["aggregate_total_indicator"]].copy()
    exact_sum = pd.to_numeric(base.loc[base["death_status"].eq("exact"), "deaths_exact"], errors="coerce").sum()
    total = 58380.0
    residual = total - exact_sum
    scenarios = {}

    s = base[base["death_status"].eq("exact") & (pd.to_numeric(base["deaths_exact"], errors="coerce") > 0)].copy()
    s["modeled_deaths"] = s["deaths_exact"]
    scenarios["observed_exact_positive_only"] = s

    s = base[base["death_status"].isin(["exact", "zero"])].copy()
    s["modeled_deaths"] = s["death_lower"]
    scenarios["observed_exact_plus_zero"] = s

    for value in [1, 5, 9]:
        s = base.copy()
        s["modeled_deaths"] = np.where(s["death_status"].eq("suppressed_1_9"), value, s["death_lower"])
        scenarios[f"suppressed_equals_{value}"] = s

    suppressed_mask = base["death_status"].eq("suppressed_1_9")
    weights = pd.to_numeric(base.loc[suppressed_mask, "model_exposure_person_years"], errors="coerce").fillna(1)
    alloc = constrained_allocation(weights, residual, 1, 9)
    s = base.copy()
    s["modeled_deaths"] = s["death_lower"]
    s.loc[suppressed_mask, "modeled_deaths"] = alloc
    scenarios["population_scaled_residual_allocation"] = s

    rural = base.loc[suppressed_mask, "primary_rurality"].fillna("")
    exposure = pd.to_numeric(base.loc[suppressed_mask, "model_exposure_person_years"], errors="coerce").fillna(1)
    conservative_weights = exposure * rural.map(
        {"metro_large": 2.0, "metro_other": 1.7, "nonmetro_adjacent": 0.35, "nonmetro_nonadjacent": 0.2}
    ).fillna(1.0)
    alloc = constrained_allocation(conservative_weights, residual, 1, 9)
    s = base.copy()
    s["modeled_deaths"] = s["death_lower"]
    s.loc[suppressed_mask, "modeled_deaths"] = alloc
    scenarios["conservative_anti_rural_allocation"] = s

    pro_weights = exposure * rural.map(
        {"metro_large": 0.2, "metro_other": 0.35, "nonmetro_adjacent": 1.7, "nonmetro_nonadjacent": 2.0}
    ).fillna(1.0)
    alloc = constrained_allocation(pro_weights, residual, 1, 9)
    s = base.copy()
    s["modeled_deaths"] = s["death_lower"]
    s.loc[suppressed_mask, "modeled_deaths"] = alloc
    scenarios["pro_rural_allocation"] = s

    summary_rows = []
    for name, sdf in scenarios.items():
        summary_rows.append(
            {
                "scenario": name,
                "rows": len(sdf),
                "modeled_deaths": float(pd.to_numeric(sdf["modeled_deaths"], errors="coerce").sum()),
                "suppressed_rows_included": int(sdf["death_status"].eq("suppressed_1_9").sum()),
            }
        )
    pd.DataFrame(summary_rows).to_csv(PROCESSED_DIR / "suppression_scenario_death_assignments.csv", index=False)
    return scenarios


def vif_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "acs_pct_poverty",
        "acs_median_household_income",
        "acs_pct_high_school_grad_or_higher",
        "acs_pct_uninsured",
        "acs_pct_non_hispanic_black",
        "acs_pct_hispanic",
        "acs_pct_age_65_plus",
    ]
    work = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    rows = []
    for col in cols:
        y = work[col].values.astype(float)
        others = [c for c in cols if c != col]
        x = work[others].values.astype(float)
        x = np.column_stack([np.ones(len(x)), x])
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        pred = x @ beta
        ss_res = ((y - pred) ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        vif = 1 / (1 - r2) if r2 < 1 else np.inf
        rows.append({"variable": col, "vif": vif, "r_squared": r2, "n": len(work)})
    return pd.DataFrame(rows)


def plot_forest(results: pd.DataFrame) -> None:
    focus_terms = [
        "primary_rurality_metro_other",
        "primary_rurality_nonmetro_adjacent",
        "primary_rurality_nonmetro_nonadjacent",
        "svi_quartile_Q4_highest",
    ]
    plot_df = results[(results["model_family"].eq("rurality_svi_composite")) & (results["term"].isin(focus_terms))].copy()
    if plot_df.empty:
        return
    plot_df["label"] = plot_df["scenario"] + " | " + plot_df["term"].str.replace("primary_rurality_", "").str.replace("svi_quartile_", "SVI ")
    plot_df = plot_df.sort_values(["term", "scenario"])
    fig, ax = plt.subplots(figsize=(9, max(5, len(plot_df) * 0.25)))
    y = np.arange(len(plot_df))
    ax.errorbar(
        plot_df["irr"],
        y,
        xerr=[plot_df["irr"] - plot_df["ci_low"], plot_df["ci_high"] - plot_df["irr"]],
        fmt="o",
        color="#1f4e79",
        ecolor="#7f8c8d",
        capsize=2,
    )
    ax.axvline(1.0, color="#333333", linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"], fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("Incidence rate ratio, log scale")
    ax.set_title("Suppression-bounds model estimates")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "suppression_bounds_forest_plot.png", dpi=200)
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(PROCESSED_DIR / "county_period_analysis.csv", dtype={"county_fips": str})
    scenarios = make_scenarios(df)
    result_frames = []
    fit_rows = []
    for scenario, sdf in scenarios.items():
        for family_name, include_svi, include_components in [
            ("rurality_only", False, False),
            ("rurality_svi_composite", True, False),
            ("acs_component_family", False, True),
        ]:
            try:
                res, fit = fit_model(sdf, scenario, family_name, include_svi=include_svi, include_components=include_components)
                result_frames.append(res)
                fit_rows.append(fit)
            except Exception as exc:
                fit_rows.append({"scenario": scenario, "model_family": family_name, "model_type": "failed", "error": str(exc)})

    results = pd.concat(result_frames, ignore_index=True) if result_frames else pd.DataFrame()
    fits = pd.DataFrame(fit_rows)
    results.to_csv(TABLE_DIR / "suppression_bounds_model_results.csv", index=False)
    fits.to_csv(TABLE_DIR / "model_fit_summary.csv", index=False)
    vif = vif_table(df)
    vif.to_csv(TABLE_DIR / "component_model_vif.csv", index=False)
    plot_forest(results)

    focus = results[
        results["term"].eq("primary_rurality_nonmetro_nonadjacent")
        & results["model_family"].eq("rurality_svi_composite")
    ][["scenario", "irr", "ci_low", "ci_high", "p_value"]]

    report = f"""# Model Results Report

Generated: 2026-06-13

## Bias-Bounding Models

County-period negative-binomial count models used log person-years as the
offset. When robust GLM negative-binomial fitting was not stable, the script
falls back to a robust Poisson model and records that model type in the fit
summary.

Primary output files:

- `{rel(TABLE_DIR / "suppression_bounds_model_results.csv")}`
- `{rel(TABLE_DIR / "model_fit_summary.csv")}`
- `{rel(TABLE_DIR / "component_model_vif.csv")}`
- `{rel(PLOT_DIR / "suppression_bounds_forest_plot.png")}`

## Main Nonmetro Nonadjacent Signal

{md_table(focus) if not focus.empty else "No nonmetro nonadjacent estimates were available."}

## Component Collinearity Diagnostics

{md_table(vif)}

## Interpretation Guardrail

These are ecological county-level count models. They do not estimate person-level
risk or cause-and-effect relationships. SVI composite and ACS component variables are modeled
in separate families to avoid including SVI with its own components in the same
primary model.
"""
    write_text(REPORT_DIR / "model_results_report.md", report)
    print("Completed suppression-bounds models.")


if __name__ == "__main__":
    main()
