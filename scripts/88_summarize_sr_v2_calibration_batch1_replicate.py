from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.calibration_methods import comparator_scenarios  # noqa: E402
from bayes_constrained.calibration_study import (  # noqa: E402
    scenario_for_replicate,
    valid_replicates_for_batch,
)
from bayes_constrained.constraints import assert_constraints  # noqa: E402
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402


BATCH_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_study_batch1"
PRIMARY_PARAMETERS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
]


def quantiles(values: np.ndarray) -> tuple[float, float, float]:
    lower, median, upper = np.quantile(
        np.asarray(values, dtype=float),
        [0.025, 0.5, 0.975],
    )
    return float(median), float(lower), float(upper)


def replicate_root(replicate_id: int) -> Path:
    return BATCH_ROOT / f"replicate_{replicate_id:02d}"


def main() -> None:
    global BATCH_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", type=int, default=1, choices=(1, 2))
    parser.add_argument("--replicate-id", type=int, required=True)
    args = parser.parse_args()
    valid_replicates = valid_replicates_for_batch(args.batch_id)
    if args.replicate_id not in valid_replicates:
        parser.error(
            f"batch {args.batch_id} replicate must be one of {valid_replicates}"
        )
    BATCH_ROOT = (
        ROOT
        / "outputs"
        / "scientific_reports_v2"
        / f"calibration_study_batch{args.batch_id}"
    )

    scenario = scenario_for_replicate(
        args.replicate_id,
        batch_id=args.batch_id,
    )
    root = replicate_root(args.replicate_id)
    design_root = root / "design"
    summary_root = root / "summary"
    summary_root.mkdir(parents=True, exist_ok=True)
    chain_dirs = sorted((root / "chains").glob("chain_*"))
    if len(chain_dirs) != 4:
        raise SystemExit(
            f"Expected four chains for calibration replicate {args.replicate_id}; "
            f"found {len(chain_dirs)}."
        )

    public = pd.read_parquet(design_root / "public_suppressed_frame.parquet")
    design_summary = json.loads(
        (design_root / "design_summary.json").read_text(encoding="utf-8")
    )
    public.attrs["grand_total"] = int(design_summary["grand_total"])
    truth = json.loads((design_root / "truth.json").read_text(encoding="utf-8"))
    complete = pd.read_csv(
        design_root / "complete_truth_and_public_bounds.csv",
        dtype={"county_fips": str, "year": str},
    )
    complete_counts = complete["complete_count"].to_numpy(dtype=int)

    parameter_frames: list[pd.DataFrame] = []
    acceptance_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, object]] = []
    latent_by_chain: dict[int, np.ndarray] = {}
    validation_failures = 0
    for chain_dir in chain_dirs:
        chain = int(chain_dir.name.split("_")[-1])
        status = json.loads((chain_dir / "chain_status.json").read_text(encoding="utf-8"))
        status_rows.append({"chain": chain, **status})
        parameter_frames.append(pd.read_parquet(chain_dir / "draws_params.parquet"))
        acceptance_frames.append(pd.read_csv(chain_dir / "acceptance_rates.csv"))
        latent = np.load(chain_dir / "draws_latent.npz", allow_pickle=True)["y"].astype(int)
        latent_by_chain[chain] = latent
        validation = pd.read_csv(chain_dir / "latent_validation.csv")
        validation_failures += int((~validation["passed"].astype(bool)).sum())
        for draw_index, state in enumerate(latent, start=1):
            assert_constraints(
                state,
                public,
                label=(
                    f"calibration_batch{args.batch_id}_rep{args.replicate_id}_"
                    f"chain{chain}_draw{draw_index}"
                ),
            )

    status = pd.DataFrame(status_rows).sort_values("chain")
    parameter_draws = pd.concat(parameter_frames, ignore_index=True)
    acceptance = pd.concat(acceptance_frames, ignore_index=True)
    parameter_diagnostics = diagnostics_table(parameter_draws, output_dir=None)
    parameter_diagnostics.to_csv(
        summary_root / "parameter_diagnostics.csv",
        index=False,
    )
    acceptance.to_csv(summary_root / "acceptance.csv", index=False)
    (
        acceptance.groupby(["type", "block"])["acceptance_rate"]
        .agg(["min", "median", "max"])
        .reset_index()
        .to_csv(summary_root / "acceptance_summary.csv", index=False)
    )
    status.to_csv(summary_root / "chain_status.csv", index=False)

    diagnostic_index = parameter_diagnostics.set_index("parameter")
    primary_rows: list[dict[str, object]] = []
    for parameter in PRIMARY_PARAMETERS:
        coefficient_draws = parameter_draws.loc[
            parameter_draws["parameter"].eq(parameter),
            "value",
        ].to_numpy(dtype=float)
        irr_draws = np.exp(coefficient_draws)
        median, lower, upper = quantiles(irr_draws)
        truth_irr = float(np.exp(float(truth["beta_by_term"][parameter])))
        diagnostic = diagnostic_index.loc[parameter]
        primary_rows.append(
            {
                "replicate": args.replicate_id,
                "scenario": scenario.scenario_id,
                "parameter": parameter,
                "truth_irr": truth_irr,
                "posterior_median_irr": median,
                "posterior_lower_95": lower,
                "posterior_upper_95": upper,
                "bias_irr": median - truth_irr,
                "relative_bias_percent": (median / truth_irr - 1.0) * 100.0,
                "squared_error_irr": (median - truth_irr) ** 2,
                "interval_width": upper - lower,
                "truth_covered_by_95_interval": bool(lower <= truth_irr <= upper),
                "r_hat": float(diagnostic["r_hat"]),
                "ess_bulk": float(diagnostic["ess_bulk"]),
                "ess_tail": float(diagnostic["ess_tail"]),
            }
        )
    primary = pd.DataFrame(primary_rows)
    primary.to_csv(summary_root / "primary_recovery.csv", index=False)

    category_masks: dict[str, np.ndarray] = {}
    for column, prefix in [
        ("primary_rurality", "rurality"),
        ("svi_quartile", "svi"),
    ]:
        for category in sorted(public[column].astype(str).unique()):
            category_masks[f"latent_{prefix}_total[{category}]"] = (
                public[column].astype(str).eq(category).to_numpy()
            )
    latent_summary_rows: list[dict[str, object]] = []
    for chain, latent in sorted(latent_by_chain.items()):
        for parameter, mask in category_masks.items():
            values = latent[:, mask].sum(axis=1)
            latent_summary_rows.extend(
                {
                    "chain": chain,
                    "draw": draw,
                    "parameter": parameter,
                    "value": float(value),
                }
                for draw, value in enumerate(values, start=1)
            )
    latent_summary_draws = pd.DataFrame(latent_summary_rows)
    latent_summary_draws.to_parquet(
        summary_root / "latent_summary_draws.parquet",
        index=False,
    )
    latent_diagnostics = diagnostics_table(latent_summary_draws, output_dir=None)
    latent_diagnostics.to_csv(
        summary_root / "latent_summary_diagnostics.csv",
        index=False,
    )
    unique_latent_values = latent_summary_draws.groupby("parameter")["value"].nunique()
    stochastic_latent_parameters = unique_latent_values[unique_latent_values > 1].index
    stochastic_latent_diagnostics = latent_diagnostics[
        latent_diagnostics["parameter"].isin(stochastic_latent_parameters)
    ].copy()

    latent_draws = np.concatenate(
        [latent_by_chain[key] for key in sorted(latent_by_chain)],
        axis=0,
    )
    latent_mean = latent_draws.mean(axis=0)
    latent_lower = np.quantile(latent_draws, 0.025, axis=0)
    latent_upper = np.quantile(latent_draws, 0.975, axis=0)
    cell = complete.copy()
    cell["posterior_mean"] = latent_mean
    cell["posterior_lower_95"] = latent_lower
    cell["posterior_upper_95"] = latent_upper
    cell["absolute_error"] = np.abs(latent_mean - complete_counts)
    cell["squared_error"] = np.square(latent_mean - complete_counts)
    cell["covered_95"] = (
        (complete_counts >= latent_lower) & (complete_counts <= latent_upper)
    )
    cell.to_csv(summary_root / "cell_recovery.csv", index=False)

    recovery_rows: list[dict[str, object]] = []
    for label, mask in [
        ("all_cells", np.ones(len(cell), dtype=bool)),
        ("suppressed_cells", cell["public_status"].eq("suppressed_1_9").to_numpy()),
        ("exact_cells", cell["public_status"].eq("exact").to_numpy()),
        ("zero_cells", cell["public_status"].eq("zero").to_numpy()),
    ]:
        work = cell.loc[mask]
        recovery_rows.append(
            {
                "replicate": args.replicate_id,
                "scenario": scenario.scenario_id,
                "cell_group": label,
                "cells": int(len(work)),
                "mean_absolute_error": float(work["absolute_error"].mean()),
                "root_mean_squared_error": float(
                    np.sqrt(work["squared_error"].mean())
                ),
                "coverage_95": float(work["covered_95"].mean()),
                "mean_interval_width": float(
                    (work["posterior_upper_95"] - work["posterior_lower_95"]).mean()
                ),
            }
        )
    recovery = pd.DataFrame(recovery_rows)
    recovery.to_csv(summary_root / "latent_recovery_summary.csv", index=False)

    comparators = comparator_scenarios(
        public,
        complete_counts,
        kappa=float(truth["kappa"]),
        allocation_seed=55000 + args.replicate_id,
    )
    truth_irrs = {
        parameter: float(np.exp(float(truth["beta_by_term"][parameter])))
        for parameter in PRIMARY_PARAMETERS
    }
    comparators.insert(0, "replicate", args.replicate_id)
    comparators.insert(1, "truth_scenario", scenario.scenario_id)
    comparators["truth_irr"] = comparators["term"].map(truth_irrs)
    comparators["bias_irr"] = comparators["irr"] - comparators["truth_irr"]
    comparators["squared_error_irr"] = np.square(comparators["bias_irr"])
    comparators["truth_covered_by_95_interval"] = (
        (comparators["truth_irr"] >= comparators["ci_low"])
        & (comparators["truth_irr"] <= comparators["ci_high"])
    )
    comparators.to_csv(summary_root / "comparator_results.csv", index=False)

    primary_diag = parameter_diagnostics[
        parameter_diagnostics["parameter"].isin(PRIMARY_PARAMETERS)
    ].copy()
    suppressed = recovery[recovery["cell_group"].eq("suppressed_cells")].iloc[0]
    latent_finite = bool(
        not stochastic_latent_diagnostics.empty
        and np.isfinite(
            stochastic_latent_diagnostics[
                ["r_hat", "ess_bulk", "ess_tail"]
            ].to_numpy(dtype=float)
        ).all()
    )
    computational_pass = bool(
        status["status"].eq("completed").all()
        and validation_failures == 0
        and np.isfinite(
            primary_diag[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(dtype=float)
        ).all()
        and float(primary_diag["r_hat"].max()) < 1.05
        and float(primary_diag["ess_bulk"].min()) >= 100.0
        and float(primary_diag["ess_tail"].min()) >= 100.0
        and latent_finite
        and float(stochastic_latent_diagnostics["r_hat"].max()) < 1.10
        and float(stochastic_latent_diagnostics["ess_bulk"].min()) >= 50.0
    )
    summary = {
        **scenario.to_dict(),
        "design_summary": design_summary,
        "chains_completed": int(status["status"].eq("completed").sum()),
        "draws_per_chain": int(status["saved_draws"].min()),
        "validation_failures": int(validation_failures),
        "maximum_primary_rhat": float(primary_diag["r_hat"].max()),
        "minimum_primary_bulk_ess": float(primary_diag["ess_bulk"].min()),
        "minimum_primary_tail_ess": float(primary_diag["ess_tail"].min()),
        "maximum_all_parameter_rhat": float(parameter_diagnostics["r_hat"].max()),
        "maximum_stochastic_latent_summary_rhat": float(
            stochastic_latent_diagnostics["r_hat"].max()
        ),
        "minimum_stochastic_latent_summary_bulk_ess": float(
            stochastic_latent_diagnostics["ess_bulk"].min()
        ),
        "primary_truth_coverage_fraction": float(
            primary["truth_covered_by_95_interval"].mean()
        ),
        "primary_median_absolute_relative_bias_percent": float(
            primary["relative_bias_percent"].abs().median()
        ),
        "suppressed_cell_coverage_95": float(suppressed["coverage_95"]),
        "suppressed_cell_rmse": float(suppressed["root_mean_squared_error"]),
        "computational_gate_pass": computational_pass,
        "interpretation_boundary": (
            "One prespecified synthetic replicate. Batch-level coverage and bias remain exploratory until all replicates are aggregated; no empirical epidemiologic estimate is involved."
        ),
    }
    (summary_root / "replicate_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Calibration study batch {args.batch_id}, replicate {args.replicate_id}",
        "",
        f"Scenario: `{scenario.scenario_id}`",
        "",
        "## Computational gate",
        "",
        f"- Chains completed: {summary['chains_completed']}/4",
        f"- Draws per chain: {summary['draws_per_chain']}",
        f"- Constraint-validation failures: {summary['validation_failures']}",
        f"- Maximum primary R-hat: {summary['maximum_primary_rhat']:.4f}",
        f"- Minimum primary bulk ESS: {summary['minimum_primary_bulk_ess']:.1f}",
        f"- Maximum stochastic latent-summary R-hat: {summary['maximum_stochastic_latent_summary_rhat']:.4f}",
        f"- Computational status: {'PASS' if computational_pass else 'HOLD'}",
        "",
        "## Primary coefficient recovery",
        "",
        "| Parameter | Truth IRR | Posterior median | 95% interval | Relative bias | Covered | R-hat | Bulk ESS |",
        "| --- | ---: | ---: | --- | ---: | --- | ---: | ---: |",
    ]
    for _, row in primary.iterrows():
        lines.append(
            f"| {row['parameter']} | {row['truth_irr']:.3f} | "
            f"{row['posterior_median_irr']:.3f} | "
            f"{row['posterior_lower_95']:.3f}–{row['posterior_upper_95']:.3f} | "
            f"{row['relative_bias_percent']:.2f}% | "
            f"{row['truth_covered_by_95_interval']} | "
            f"{row['r_hat']:.4f} | {row['ess_bulk']:.1f} |"
        )
    lines.extend(
        [
            "",
            f"Suppressed-cell 95% interval coverage: {summary['suppressed_cell_coverage_95']:.3f}.",
            f"Suppressed-cell posterior-mean RMSE: {summary['suppressed_cell_rmse']:.3f} deaths.",
            "",
            "This replicate is part of a prespecified multi-replicate batch. It must not be presented as a standalone calibration claim.",
        ]
    )
    (summary_root / "replicate_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not computational_pass:
        raise SystemExit(
            f"Calibration batch {args.batch_id} replicate {args.replicate_id} is on HOLD; evidence was written."
        )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
