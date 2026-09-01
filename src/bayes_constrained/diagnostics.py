from __future__ import annotations

from typing import Sequence

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


def spatial_diagnostics_table(
    scalar_draws: pd.DataFrame,
    spatial_draws: dict[str, np.ndarray],
    graph,
    *,
    parameter_schema: Sequence[str],
    count_constraint_failures: int = 0,
    spatial_constraint_failures: int = 0,
) -> pd.DataFrame:
    """Compute the frozen six-column spatial diagnostic universe."""

    import arviz as az
    from .spatial_bym2 import validate_structured_effect

    if az.__version__ != "1.2.0":
        raise ValueError("Spatial diagnostics require pinned ArviZ 1.2.0.")
    if (
        not isinstance(parameter_schema, (list, tuple))
        or not parameter_schema
        or any(
            not isinstance(value, str)
            or not value
            or value.strip() != value
            for value in parameter_schema
        )
        or len(set(parameter_schema)) != len(parameter_schema)
    ):
        raise ValueError(
            "Spatial diagnostics require an exact ordered parameter schema."
        )
    expected_parameters = list(parameter_schema)
    for value, label in (
        (count_constraint_failures, "count_constraint_failures"),
        (spatial_constraint_failures, "spatial_constraint_failures"),
    ):
        if isinstance(value, (bool, np.bool_)) or not isinstance(
            value, (int, np.integer)
        ):
            raise ValueError(f"{label} must be an exact integer.")
        if int(value) != 0:
            raise ValueError("Spatial diagnostics require zero constraint failures.")

    def exact_integer_array(values, *, label: str) -> np.ndarray:
        array = np.asarray(values)
        if (
            array.ndim != 1
            or np.issubdtype(array.dtype, np.bool_)
            or not np.issubdtype(array.dtype, np.integer)
        ):
            raise ValueError(f"{label} must contain exact integers.")
        return array.astype(np.int64)

    def expected_epoch(draw_id: int) -> int:
        for epoch, (start, end) in {
            0: (1, 4_500),
            1: (4_501, 7_500),
            2: (7_501, 10_500),
            3: (10_501, 13_500),
        }.items():
            if start <= draw_id <= end:
                return epoch
        raise ValueError("Spatial diagnostic draw id is outside the frozen schedule.")

    scalar_columns = {
        "chain_id",
        "draw_id",
        "extension_epoch",
        "parameter",
        "value",
    }
    if set(scalar_draws.columns) != scalar_columns:
        raise ValueError("Spatial scalar diagnostics schema mismatch.")
    required = {
        "chain_id",
        "draw_id",
        "extension_epoch",
        "structured",
        "unstructured",
    }
    if set(spatial_draws) != required:
        raise ValueError("Spatial diagnostic array schema mismatch.")
    chain = exact_integer_array(spatial_draws["chain_id"], label="chain_id")
    draw = exact_integer_array(spatial_draws["draw_id"], label="draw_id")
    epoch = exact_integer_array(
        spatial_draws["extension_epoch"], label="extension_epoch"
    )
    structured = np.asarray(spatial_draws["structured"])
    unstructured = np.asarray(spatial_draws["unstructured"])
    if (
        chain.ndim != 1
        or draw.shape != chain.shape
        or epoch.shape != chain.shape
        or structured.shape != unstructured.shape
        or structured.ndim != 2
        or structured.shape[0] != len(chain)
        or structured.shape[1] != len(graph.counties)
        or structured.dtype != np.float64
        or unstructured.dtype != np.float64
        or not np.isfinite(structured).all()
        or not np.isfinite(unstructured).all()
    ):
        raise ValueError("Spatial diagnostic arrays are malformed or nonfinite.")
    if not np.array_equal(
        epoch,
        np.asarray([expected_epoch(int(value)) for value in draw], dtype=np.int64),
    ):
        raise ValueError("Spatial diagnostic extension epochs disagree with draw ids.")
    for row in structured:
        validate_structured_effect(row, graph)
    order = np.lexsort((draw, chain))
    chain = chain[order]
    draw = draw[order]
    epoch = epoch[order]
    structured = structured[order]
    unstructured = unstructured[order]
    chains = sorted(np.unique(chain).tolist())
    if chains != [1, 2, 3, 4]:
        raise ValueError("Spatial diagnostics require exactly chains 1..4.")
    draw_ids = sorted(np.unique(draw).tolist())
    if draw_ids != list(range(1, len(draw_ids) + 1)):
        raise ValueError(
            "Spatial diagnostic draw grid must be the exact prefix 1..N."
        )
    expected = [(chain_id, draw_id) for chain_id in chains for draw_id in draw_ids]
    if list(zip(chain.tolist(), draw.tolist(), strict=True)) != expected:
        raise ValueError("Spatial diagnostics require an exact equal-length chain/draw grid.")
    chain_count = len(chains)
    draw_count = len(draw_ids)
    structured_3d = structured.reshape(chain_count, draw_count, -1)
    unstructured_3d = unstructured.reshape(chain_count, draw_count, -1)

    scalar = scalar_draws.copy()
    scalar_chain = exact_integer_array(scalar["chain_id"], label="scalar chain_id")
    scalar_draw = exact_integer_array(scalar["draw_id"], label="scalar draw_id")
    scalar_epoch = exact_integer_array(
        scalar["extension_epoch"], label="scalar extension_epoch"
    )
    if not scalar["parameter"].map(lambda value: isinstance(value, str)).all():
        raise ValueError("Spatial scalar parameter names must be strings.")
    if scalar["value"].dtype != np.float64:
        raise ValueError("Spatial scalar diagnostic values must be float64.")
    scalar_value = scalar["value"].to_numpy(dtype=np.float64)
    if not np.isfinite(scalar_value).all():
        raise ValueError("Spatial scalar diagnostics contain nonfinite values.")
    scalar = pd.DataFrame(
        {
            "chain_id": scalar_chain,
            "draw_id": scalar_draw,
            "extension_epoch": scalar_epoch,
            "parameter": scalar["parameter"].to_numpy(dtype=str),
            "value": scalar_value,
        }
    )
    if scalar.duplicated(["chain_id", "draw_id", "parameter"]).any():
        raise ValueError("Spatial scalar diagnostics contain duplicate cells.")
    if not np.array_equal(
        scalar_epoch,
        np.asarray([expected_epoch(int(value)) for value in scalar_draw], dtype=np.int64),
    ):
        raise ValueError("Spatial scalar extension epochs disagree with draw ids.")
    expected_grid = {(chain_id, draw_id) for chain_id in chains for draw_id in draw_ids}
    observed_parameters = set(scalar["parameter"].unique().tolist())
    if observed_parameters != set(expected_parameters):
        raise ValueError("Spatial scalar parameter schema mismatch.")
    for parameter in expected_parameters:
        cells = scalar.loc[
            scalar["parameter"].eq(parameter), ["chain_id", "draw_id"]
        ]
        if set(map(tuple, cells.to_numpy().tolist())) != expected_grid:
            raise ValueError(f"Spatial scalar grid is incomplete for {parameter}.")

    def scalar_matrix(parameter: str) -> np.ndarray:
        work = scalar.loc[
            scalar["parameter"].eq(parameter),
            ["chain_id", "draw_id", "value"],
        ].copy()
        wide = (
            work.pivot(index="chain_id", columns="draw_id", values="value")
            .reindex(index=chains, columns=draw_ids)
        )
        if wide.isna().any().any():
            raise ValueError(f"Spatial scalar grid is incomplete for {parameter}.")
        return wide.to_numpy(dtype=np.float64)

    sigma = scalar_matrix("sigma_county")
    phi = scalar_matrix("phi_structured")
    if (
        not np.isfinite(sigma).all()
        or np.any(sigma <= 0)
        or not np.isfinite(phi).all()
        or np.any((phi <= 0) | (phi >= 1))
    ):
        raise ValueError("Spatial hyperparameter draws are outside their support.")
    combined = sigma[:, :, None] * (
        np.sqrt(phi)[:, :, None] * structured_3d
        + np.sqrt(1.0 - phi)[:, :, None] * unstructured_3d
    )

    def diagnostic_row(parameter: str, values: np.ndarray) -> dict[str, object]:
        row = {
            "parameter": parameter,
            "r_hat": float(az.rhat(values, method="rank")),
            "ess_bulk": float(az.ess(values, method="bulk")),
            "ess_tail": float(az.ess(values, method="tail", prob=[0.05, 0.95])),
            "arviz_version": az.__version__,
            "constraint_failures": 0,
        }
        if not np.isfinite(
            [row["r_hat"], row["ess_bulk"], row["ess_tail"]]
        ).all():
            raise ValueError(f"Spatial diagnostics are nonfinite for {parameter}.")
        return row

    rows: list[dict[str, object]] = [
        diagnostic_row(parameter, scalar_matrix(parameter))
        for parameter in expected_parameters
    ]
    for county_index, county in enumerate(graph.counties):
        if not bool(graph.singleton_mask[county_index]):
            rows.append(
                diagnostic_row(
                    f"spatial_structured[{county}]",
                    structured_3d[:, :, county_index],
                )
            )
        rows.append(
            diagnostic_row(
                f"spatial_unstructured[{county}]",
                unstructured_3d[:, :, county_index],
            )
        )
        rows.append(
            diagnostic_row(
                f"county_combined[{county}]",
                combined[:, :, county_index],
            )
        )
    result = pd.DataFrame(rows)
    columns = [
        "parameter",
        "r_hat",
        "ess_bulk",
        "ess_tail",
        "arviz_version",
        "constraint_failures",
    ]
    result = result.loc[:, columns]
    if len(graph.counties) == 3_142:
        expected_rows = 71 + 3_128 + 3_142 + 3_142
        if len(expected_parameters) != 71 or len(result) != expected_rows:
            raise ValueError("Production spatial diagnostic universe must have 9,483 rows.")
        if draw_count not in {4_500, 7_500, 10_500, 13_500}:
            raise ValueError("Production spatial diagnostics have an invalid draw count.")
    return result


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
