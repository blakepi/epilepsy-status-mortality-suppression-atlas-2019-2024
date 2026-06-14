from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom

from utils import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, md_table, rel, write_text
from src04_helper import RURAL_ORDER, SVI_ORDER, design_matrix_for_interval


def negloglik(params: np.ndarray, x: np.ndarray, offset: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    beta = params[:-1]
    alpha = np.exp(params[-1])
    mu = np.exp(offset + x @ beta)
    r = 1.0 / alpha
    p = r / (r + mu)
    prob = np.where(
        lower == upper,
        nbinom.pmf(lower, r, p),
        nbinom.cdf(upper, r, p) - nbinom.cdf(lower - 1, r, p),
    )
    prob = np.clip(prob, 1e-12, 1.0)
    return float(-np.log(prob).sum())


def fit_interval(df: pd.DataFrame, model_family: str, include_svi: bool) -> tuple[pd.DataFrame, dict]:
    work = df[~df["aggregate_total_indicator"]].copy()
    work = work[pd.to_numeric(work["model_exposure_person_years"], errors="coerce") > 0]
    work = work[work["primary_rurality"].notna()]
    if include_svi:
        work = work[work["svi_quartile"].notna()]
    xdf, cols = design_matrix_for_interval(work, include_svi)
    x = xdf.values.astype(float)
    offset = np.log(pd.to_numeric(work["model_exposure_person_years"], errors="coerce").values.astype(float))
    lower = pd.to_numeric(work["death_lower"], errors="coerce").values.astype(float)
    upper = pd.to_numeric(work["death_upper"], errors="coerce").values.astype(float)
    start = np.zeros(x.shape[1] + 1)
    start[-1] = np.log(0.5)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = minimize(negloglik, start, args=(x, offset, lower, upper), method="L-BFGS-B", options={"maxiter": 500})
    rows = []
    se = np.full(len(cols) + 1, np.nan)
    try:
        inv_hess = res.hess_inv.todense()
        se = np.sqrt(np.diag(inv_hess))
    except Exception:
        pass
    for i, term in enumerate(cols):
        if term == "Intercept":
            continue
        coef = res.x[i]
        rows.append(
            {
                "model_family": model_family,
                "term": term,
                "coef": coef,
                "se_approx": se[i],
                "irr": float(np.exp(coef)),
                "ci_low_approx": float(np.exp(coef - 1.96 * se[i])) if np.isfinite(se[i]) else np.nan,
                "ci_high_approx": float(np.exp(coef + 1.96 * se[i])) if np.isfinite(se[i]) else np.nan,
                "n_rows": int(len(work)),
                "interval_log_likelihood": float(-res.fun),
                "converged": bool(res.success),
            }
        )
    fit = {
        "model_family": model_family,
        "n_rows": int(len(work)),
        "converged": bool(res.success),
        "message": str(res.message),
        "interval_log_likelihood": float(-res.fun),
        "alpha": float(np.exp(res.x[-1])),
    }
    return pd.DataFrame(rows), fit


def main() -> None:
    df = pd.read_csv(PROCESSED_DIR / "county_period_analysis.csv", dtype={"county_fips": str})
    rows = []
    fits = []
    errors = []
    for family, include_svi in [("interval_nb_rurality_only", False), ("interval_nb_rurality_svi", True)]:
        try:
            res, fit = fit_interval(df, family, include_svi)
            rows.append(res)
            fits.append(fit)
        except Exception as exc:
            errors.append({"model_family": family, "error": str(exc)})
    results = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    results.to_csv(TABLE_DIR / "interval_model_results.csv", index=False)
    pd.DataFrame(fits).to_csv(TABLE_DIR / "interval_model_fit_summary.csv", index=False)
    if errors:
        pd.DataFrame(errors).to_csv(TABLE_DIR / "interval_model_errors.csv", index=False)

    focus = results[results["term"].eq("primary_rurality_nonmetro_nonadjacent")]
    report = f"""# Interval-Likelihood Model Addendum

Generated: 2026-06-13

## Feasibility

The script attempted a custom maximum-likelihood negative-binomial interval
model:

- exact rows: P(Y = y)
- zero rows: P(Y = 0)
- suppressed rows: P(1 <= Y <= 9)

## Outputs

- Results: `{rel(TABLE_DIR / "interval_model_results.csv")}`
- Fit summary: `{rel(TABLE_DIR / "interval_model_fit_summary.csv")}`

## Main Interval Estimates

{md_table(focus) if not focus.empty else "No interval estimates were produced."}

## Caveat

Approximate standard errors use the optimizer inverse-Hessian approximation.
Bias-bounding models remain the primary suppression-aware evidence if interval
standard errors are unstable.
"""
    write_text(REPORT_DIR / "interval_model_report.md", report)
    # Append compact note to model report without overwriting prior content.
    with (REPORT_DIR / "model_results_report.md").open("a", encoding="utf-8") as f:
        f.write("\n## Interval-Likelihood Addendum\n\n")
        f.write(md_table(focus) if not focus.empty else "No interval estimates were produced.")
        f.write("\n")
    print("Completed interval-likelihood models.")


if __name__ == "__main__":
    main()
