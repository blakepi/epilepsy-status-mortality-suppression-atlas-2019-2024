from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .model import PRIMARY_TERMS, term_to_label
from .paths import FIGURE_SUPP_DIR, OUTPUT_DIR


def split_rhat(values_by_chain: dict[int, np.ndarray]) -> float:
    chains = [np.asarray(v, dtype=float) for v in values_by_chain.values() if len(v) >= 4]
    if len(chains) < 2:
        return np.nan
    split = []
    for chain in chains:
        half = len(chain) // 2
        if half >= 2:
            split.append(chain[:half])
            split.append(chain[-half:])
    if len(split) < 2:
        return np.nan
    n = min(len(x) for x in split)
    arr = np.vstack([x[:n] for x in split])
    chain_means = arr.mean(axis=1)
    chain_vars = arr.var(axis=1, ddof=1)
    b = n * chain_means.var(ddof=1)
    w = chain_vars.mean()
    if w <= 0:
        return np.nan
    var_hat = ((n - 1) / n) * w + b / n
    return float(np.sqrt(var_hat / w))


def ess_bulk(values_by_chain: dict[int, np.ndarray]) -> float:
    chains = [np.asarray(v, dtype=float) for v in values_by_chain.values() if len(v) >= 4]
    if not chains:
        return np.nan
    arr = np.concatenate(chains)
    n = len(arr)
    if n < 4 or np.var(arr) <= 0:
        return np.nan
    max_lag = min(100, n // 2)
    acf_sum = 0.0
    centered = arr - arr.mean()
    denom = float(np.dot(centered, centered))
    for lag in range(1, max_lag + 1):
        rho = float(np.dot(centered[:-lag], centered[lag:]) / denom)
        if rho < 0:
            break
        acf_sum += rho
    return float(n / (1 + 2 * acf_sum))


def _parameter_array(parameter_draws: pd.DataFrame, parameter: str) -> np.ndarray:
    work = parameter_draws.loc[
        parameter_draws["parameter"].eq(parameter), ["chain", "draw", "value"]
    ].copy()
    if work.empty:
        raise ValueError(f"No draws found for parameter {parameter!r}.")
    if work.duplicated(["chain", "draw"]).any():
        raise ValueError(f"Duplicate chain/draw rows found for parameter {parameter!r}.")
    wide = work.pivot(index="chain", columns="draw", values="value").sort_index().sort_index(axis=1)
    if wide.isna().any().any():
        raise ValueError(f"Chains have unequal or missing draws for parameter {parameter!r}.")
    values = wide.to_numpy(dtype=float)
    if values.shape[0] < 2 or values.shape[1] < 4:
        raise ValueError(f"Parameter {parameter!r} requires at least two chains and four draws per chain.")
    if not np.isfinite(values).all():
        raise ValueError(f"Parameter {parameter!r} contains non-finite draws.")
    return values


def diagnostics_table(
    parameter_draws: pd.DataFrame,
    output_dir: Path | None = OUTPUT_DIR,
) -> pd.DataFrame:
    """Compute modern convergence diagnostics for every retained parameter.

    R-hat is the rank-normalized, folded split diagnostic. Bulk and tail ESS
    use ArviZ's multi-chain Geyer estimators. The legacy ``ess`` column is
    retained as an alias for ``ess_bulk`` so downstream readers fail safely
    while they migrate to the explicit columns.
    """

    import arviz as az

    required = {"chain", "draw", "parameter", "value"}
    missing = required - set(parameter_draws.columns)
    if missing:
        raise ValueError(f"Parameter draws are missing required columns: {sorted(missing)}")

    rows = []
    for parameter in sorted(parameter_draws["parameter"].dropna().astype(str).unique()):
        values = _parameter_array(parameter_draws, parameter)
        r_hat = float(az.rhat(values, method="rank"))
        ess_bulk_value = float(az.ess(values, method="bulk"))
        ess_tail_value = float(az.ess(values, method="tail", prob=[0.05, 0.95]))
        rows.append(
            {
                "parameter": parameter,
                "label": term_to_label(parameter),
                "r_hat": r_hat,
                "ess_bulk": ess_bulk_value,
                "ess_tail": ess_tail_value,
                "mcse_mean": float(az.mcse(values, method="mean")),
                "mcse_sd": float(az.mcse(values, method="sd")),
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=1)),
                "chains": int(values.shape[0]),
                "draws_per_chain": int(values.shape[1]),
                "draws": int(values.size),
                "ess": ess_bulk_value,
            }
        )
    diag = pd.DataFrame(rows)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        diag.to_csv(output_dir / "mcmc_diagnostics.csv", index=False)
        lines = [
            "# MCMC Diagnostics",
            "",
            "All retained parameters are reported. R-hat is rank-normalized and folded; ESS values are multi-chain bulk and tail estimates.",
            "",
            "| Parameter | R-hat | Bulk ESS | Tail ESS | MCSE mean | Draws |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for _, row in diag.iterrows():
            lines.append(
                f"| {row['label']} | {row['r_hat']:.6f} | {row['ess_bulk']:.1f} | "
                f"{row['ess_tail']:.1f} | {row['mcse_mean']:.6g} | {int(row['draws'])} |"
            )
        (output_dir / "mcmc_diagnostics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return diag


def make_diagnostic_figures(parameter_draws: pd.DataFrame, diagnostics: pd.DataFrame) -> None:
    FIGURE_SUPP_DIR.mkdir(parents=True, exist_ok=True)
    focus = [
        "primary_rurality_metro_other",
        "primary_rurality_nonmetro_adjacent",
        "primary_rurality_nonmetro_nonadjacent",
        "svi_quartile_Q4_highest",
    ]
    trace = parameter_draws[parameter_draws["parameter"].isin(focus)].copy()
    if not trace.empty:
        trace["irr"] = np.exp(trace["value"])
        fig, axes = plt.subplots(len(focus), 1, figsize=(7.2, 7.0), sharex=True)
        for ax, term in zip(np.atleast_1d(axes), focus):
            work = trace[trace["parameter"].eq(term)]
            for chain, group in work.groupby("chain"):
                ax.plot(group["draw"], group["irr"], linewidth=0.8, alpha=0.75, label=f"chain {chain}")
            ax.axhline(1.0, color="#555555", linestyle="--", linewidth=0.8)
            ax.set_ylabel(term_to_label(term), fontsize=7)
        axes[0].legend(ncol=4, fontsize=6, loc="upper right")
        axes[-1].set_xlabel("Saved draw")
        fig.suptitle("Bayesian constrained MCMC traces for primary IRRs", fontsize=10)
        fig.tight_layout()
        fig.savefig(FIGURE_SUPP_DIR / "bayes_trace_nonmetro_nonadjacent.png", dpi=300)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for term in focus:
            vals = trace.loc[trace["parameter"].eq(term), "irr"].to_numpy()
            if len(vals):
                ax.hist(vals, bins=30, density=True, histtype="step", linewidth=1.5, label=term_to_label(term))
        ax.axvline(1.0, color="#555555", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Posterior IRR")
        ax.set_ylabel("Density")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGURE_SUPP_DIR / "bayes_density_primary_irrs.png", dpi=300)
        plt.close(fig)

    hyper = parameter_draws[parameter_draws["parameter"].isin(["kappa", "sigma_state", "sigma_year"])].copy()
    if not hyper.empty:
        fig, axes = plt.subplots(1, 3, figsize=(9, 3))
        for ax, term in zip(axes, ["kappa", "sigma_state", "sigma_year"]):
            vals = hyper.loc[hyper["parameter"].eq(term), "value"].to_numpy(dtype=float)
            ax.hist(vals, bins=30, color="#5477C4", alpha=0.75)
            ax.set_title(term)
        fig.tight_layout()
        fig.savefig(FIGURE_SUPP_DIR / "bayes_kappa_sigma_diagnostics.png", dpi=300)
        plt.close(fig)

    if not diagnostics.empty:
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        plot = diagnostics.copy()
        ess_column = "ess_bulk" if "ess_bulk" in plot.columns else "ess"
        ax.scatter(plot["r_hat"], plot[ess_column], color="#2E4780")
        for _, row in plot.iterrows():
            ax.text(row["r_hat"], row[ess_column], row["label"], fontsize=6)
        ax.axvline(1.01, color="#B8A037", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Rank-normalized split R-hat")
        ax.set_ylabel("Bulk ESS")
        fig.tight_layout()
        fig.savefig(FIGURE_SUPP_DIR / "bayes_constraint_validation.png", dpi=300)
        plt.close(fig)
