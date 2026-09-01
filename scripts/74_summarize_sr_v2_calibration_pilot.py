from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.calibration_methods import comparator_scenarios  # noqa: E402
from bayes_constrained.constraints import assert_constraints  # noqa: E402
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402


DESIGN_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_design_smoke"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_pilot" / "replicate_001"
PRIMARY_PARAMETERS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
]


def _quantiles(values: np.ndarray) -> tuple[float, float, float]:
    lower, median, upper = np.quantile(np.asarray(values, dtype=float), [0.025, 0.5, 0.975])
    return float(median), float(lower), float(upper)


def main() -> None:
    chain_dirs = sorted((OUTPUT_ROOT / "chains").glob("chain_*"))
    if len(chain_dirs) != 4:
        raise SystemExit(f"Expected four calibration chains; found {len(chain_dirs)}.")

    public = pd.read_parquet(DESIGN_ROOT / "public_suppressed_frame.parquet")
    design_summary = json.loads(
        (DESIGN_ROOT / "calibration_design_summary.json").read_text(encoding="utf-8")
    )
    public.attrs["grand_total"] = int(design_summary["grand_total"])
    truth = json.loads((DESIGN_ROOT / "truth.json").read_text(encoding="utf-8"))
    complete_table = pd.read_csv(
        DESIGN_ROOT / "complete_truth_and_public_bounds.csv",
        dtype={"county_fips": str, "year": str},
    )
    complete_counts = complete_table["complete_count"].to_numpy(dtype=int)

    parameter_frames: list[pd.DataFrame] = []
    acceptance_frames: list[pd.DataFrame] = []
    latent_frames: list[np.ndarray] = []
    status_rows: list[dict[str, object]] = []
    validation_failures = 0
    for chain_dir in chain_dirs:
        chain = int(chain_dir.name.split("_")[-1])
        status = json.loads((chain_dir / "chain_status.json").read_text(encoding="utf-8"))
        status_rows.append({"chain": chain, **status})
        parameter_frames.append(pd.read_parquet(chain_dir / "draws_params.parquet"))
        acceptance_frames.append(pd.read_csv(chain_dir / "acceptance_rates.csv"))
        latent = np.load(chain_dir / "draws_latent.npz", allow_pickle=True)["y"].astype(int)
        latent_frames.append(latent)
        validation = pd.read_csv(chain_dir / "latent_validation.csv")
        validation_failures += int((~validation["passed"].astype(bool)).sum())
        for draw_index, state in enumerate(latent, start=1):
            assert_constraints(
                state,
                public,
                label=f"calibration_chain{chain}_draw{draw_index}",
            )

    status = pd.DataFrame(status_rows).sort_values("chain")
    parameter_draws = pd.concat(parameter_frames, ignore_index=True)
    acceptance = pd.concat(acceptance_frames, ignore_index=True)
    latent_draws = np.concatenate(latent_frames, axis=0)
    diagnostics = diagnostics_table(parameter_draws, output_dir=None)
    diagnostics.to_csv(OUTPUT_ROOT / "calibration_parameter_diagnostics.csv", index=False)
    acceptance.to_csv(OUTPUT_ROOT / "calibration_acceptance.csv", index=False)
    status.to_csv(OUTPUT_ROOT / "calibration_chain_status.csv", index=False)

    diagnostic_index = diagnostics.set_index("parameter")
    primary_rows: list[dict[str, object]] = []
    for parameter in PRIMARY_PARAMETERS:
        coefficient_draws = parameter_draws.loc[
            parameter_draws["parameter"].eq(parameter), "value"
        ].to_numpy(dtype=float)
        irr_draws = np.exp(coefficient_draws)
        median, lower, upper = _quantiles(irr_draws)
        truth_coefficient = float(truth["beta_by_term"][parameter])
        truth_irr = float(np.exp(truth_coefficient))
        diag = diagnostic_index.loc[parameter]
        primary_rows.append(
            {
                "parameter": parameter,
                "truth_coefficient": truth_coefficient,
                "truth_irr": truth_irr,
                "posterior_median_irr": median,
                "posterior_lower_95": lower,
                "posterior_upper_95": upper,
                "bias_irr": median - truth_irr,
                "relative_bias_percent": (median / truth_irr - 1.0) * 100.0,
                "truth_covered_by_95_interval": bool(lower <= truth_irr <= upper),
                "r_hat": float(diag["r_hat"]),
                "ess_bulk": float(diag["ess_bulk"]),
                "ess_tail": float(diag["ess_tail"]),
            }
        )
    primary = pd.DataFrame(primary_rows)
    primary.to_csv(OUTPUT_ROOT / "calibration_primary_recovery.csv", index=False)

    latent_mean = latent_draws.mean(axis=0)
    latent_median = np.quantile(latent_draws, 0.5, axis=0)
    latent_lower = np.quantile(latent_draws, 0.025, axis=0)
    latent_upper = np.quantile(latent_draws, 0.975, axis=0)
    cell_recovery = complete_table.copy()
    cell_recovery["posterior_mean"] = latent_mean
    cell_recovery["posterior_median"] = latent_median
    cell_recovery["posterior_lower_95"] = latent_lower
    cell_recovery["posterior_upper_95"] = latent_upper
    cell_recovery["absolute_error_posterior_mean"] = np.abs(latent_mean - complete_counts)
    cell_recovery["squared_error_posterior_mean"] = np.square(latent_mean - complete_counts)
    cell_recovery["truth_covered_by_95_interval"] = (
        (complete_counts >= latent_lower) & (complete_counts <= latent_upper)
    )
    cell_recovery.to_csv(OUTPUT_ROOT / "calibration_cell_recovery.csv", index=False)

    recovery_rows: list[dict[str, object]] = []
    for label, mask in [
        ("all_cells", np.ones(len(cell_recovery), dtype=bool)),
        ("suppressed_cells", cell_recovery["public_status"].eq("suppressed_1_9").to_numpy()),
        ("exact_cells", cell_recovery["public_status"].eq("exact").to_numpy()),
        ("zero_cells", cell_recovery["public_status"].eq("zero").to_numpy()),
    ]:
        work = cell_recovery.loc[mask]
        recovery_rows.append(
            {
                "cell_group": label,
                "cells": int(len(work)),
                "mean_absolute_error": float(work["absolute_error_posterior_mean"].mean()),
                "root_mean_squared_error": float(
                    np.sqrt(work["squared_error_posterior_mean"].mean())
                ),
                "coverage_95": float(work["truth_covered_by_95_interval"].mean()),
                "mean_interval_width": float(
                    (work["posterior_upper_95"] - work["posterior_lower_95"]).mean()
                ),
            }
        )
    recovery = pd.DataFrame(recovery_rows)
    recovery.to_csv(OUTPUT_ROOT / "calibration_latent_recovery_summary.csv", index=False)

    comparators = comparator_scenarios(
        public,
        complete_counts,
        kappa=float(truth["kappa"]),
    )
    comparator_truth = {
        parameter: float(np.exp(truth["beta_by_term"][parameter]))
        for parameter in PRIMARY_PARAMETERS
    }
    comparators["truth_irr"] = comparators["term"].map(comparator_truth)
    comparators["bias_irr"] = comparators["irr"] - comparators["truth_irr"]
    comparators["truth_covered_by_95_interval"] = (
        (comparators["truth_irr"] >= comparators["ci_low"])
        & (comparators["truth_irr"] <= comparators["ci_high"])
    )
    comparators.to_csv(OUTPUT_ROOT / "calibration_comparator_results.csv", index=False)

    acceptance_summary = (
        acceptance.groupby(["type", "block"])["acceptance_rate"]
        .agg(["min", "median", "max"])
        .reset_index()
    )
    acceptance_summary.to_csv(OUTPUT_ROOT / "calibration_acceptance_summary.csv", index=False)

    primary_diag = diagnostics[diagnostics["parameter"].isin(PRIMARY_PARAMETERS)]
    suppressed_recovery = recovery[recovery["cell_group"].eq("suppressed_cells")].iloc[0]
    summary = {
        "chains_completed": int(status["status"].eq("completed").sum()),
        "draws_per_chain": int(status["saved_draws"].min()),
        "validation_failures": int(validation_failures),
        "maximum_primary_rhat": float(primary_diag["r_hat"].max()),
        "minimum_primary_bulk_ess": float(primary_diag["ess_bulk"].min()),
        "primary_truth_coverage_fraction": float(primary["truth_covered_by_95_interval"].mean()),
        "suppressed_cell_coverage_95": float(suppressed_recovery["coverage_95"]),
        "suppressed_cell_rmse": float(suppressed_recovery["root_mean_squared_error"]),
        "suppressed_cell_mean_interval_width": float(suppressed_recovery["mean_interval_width"]),
        "computational_gate_pass": bool(
            status["status"].eq("completed").all()
            and validation_failures == 0
            and np.isfinite(primary_diag[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(dtype=float)).all()
            and float(primary_diag["r_hat"].max()) < 1.10
            and float(primary_diag["ess_bulk"].min()) >= 50.0
        ),
        "interpretation_boundary": (
            "Single synthetic replicate and computational smoke test only. Coverage and bias require a prespecified multi-replicate calibration study."
        ),
    }
    (OUTPUT_ROOT / "calibration_pilot_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Scientific Reports v2 truth-known calibration pilot",
        "",
        "One synthetic data set with known rurality, SVI, age, sex, state, year, and dispersion parameters was suppressed using the 1–9 rule and analyzed with the corrected constrained sampler. This is an end-to-end computational smoke test, not the final calibration study.",
        "",
        "## Computational gate",
        "",
        f"- Chains completed: {summary['chains_completed']}/4",
        f"- Draws per chain: {summary['draws_per_chain']}",
        f"- Constraint-validation failures: {summary['validation_failures']}",
        f"- Maximum primary R-hat: {summary['maximum_primary_rhat']:.4f}",
        f"- Minimum primary bulk ESS: {summary['minimum_primary_bulk_ess']:.1f}",
        f"- Computational status: {'PASS' if summary['computational_gate_pass'] else 'HOLD'}",
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
            f"{row['truth_covered_by_95_interval']} | {row['r_hat']:.4f} | "
            f"{row['ess_bulk']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Suppressed-cell recovery",
            "",
            f"- 95% interval coverage: {summary['suppressed_cell_coverage_95']:.3f}",
            f"- Posterior-mean RMSE: {summary['suppressed_cell_rmse']:.3f} deaths",
            f"- Mean 95% interval width: {summary['suppressed_cell_mean_interval_width']:.3f} deaths",
            "",
            "The values above are one-replicate diagnostics. They cannot establish nominal coverage or comparative superiority; those claims require the planned multi-replicate study.",
        ]
    )
    (OUTPUT_ROOT / "calibration_pilot_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not summary["computational_gate_pass"]:
        raise SystemExit("Truth-known calibration pilot is on HOLD; evidence has been written.")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
