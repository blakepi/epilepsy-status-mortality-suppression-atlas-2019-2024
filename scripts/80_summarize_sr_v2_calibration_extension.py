from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.constraints import assert_constraints  # noqa: E402
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402


DESIGN_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_design_smoke"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_pilot" / "replicate_001_extended"
PRIMARY_PARAMETERS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
]
ANALYSIS_START_DRAW = 800


def quantiles(values: np.ndarray) -> tuple[float, float, float]:
    lower, median, upper = np.quantile(np.asarray(values, dtype=float), [0.025, 0.5, 0.975])
    return float(median), float(lower), float(upper)


def extension_acceptance(chain_dir: Path, chain: int) -> pd.DataFrame:
    cumulative = pd.read_csv(chain_dir / "acceptance_rates.csv")
    source = pd.read_csv(chain_dir / "source_acceptance_rates.csv")
    keys = ["type", "block"]
    merged = cumulative.merge(
        source[keys + ["accepted", "proposed"]],
        on=keys,
        how="left",
        suffixes=("_cumulative", "_source"),
        validate="one_to_one",
    )
    merged[["accepted_source", "proposed_source"]] = merged[
        ["accepted_source", "proposed_source"]
    ].fillna(0)
    accepted = merged["accepted_cumulative"] - merged["accepted_source"]
    proposed = merged["proposed_cumulative"] - merged["proposed_source"]
    out = merged[keys].copy()
    out["chain"] = chain
    out["accepted"] = accepted.astype(int)
    out["proposed"] = proposed.astype(int)
    out["acceptance_rate"] = np.where(proposed > 0, accepted / proposed, np.nan)
    return out


def main() -> None:
    chain_dirs = sorted((OUTPUT_ROOT / "chains").glob("chain_*"))
    if len(chain_dirs) != 4:
        raise SystemExit(f"Expected four extended calibration chains; found {len(chain_dirs)}.")

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
        parameters = pd.read_parquet(chain_dir / "draws_params.parquet")
        parameters = parameters[pd.to_numeric(parameters["draw"], errors="coerce") > ANALYSIS_START_DRAW]
        parameter_frames.append(parameters)
        acceptance_frames.append(extension_acceptance(chain_dir, chain))
        latent_full = np.load(chain_dir / "draws_latent.npz", allow_pickle=True)["y"].astype(int)
        if latent_full.shape[0] <= ANALYSIS_START_DRAW:
            raise SystemExit(
                f"Chain {chain} retained {latent_full.shape[0]} draws; "
                f"cannot discard the first {ANALYSIS_START_DRAW}."
            )
        latent = latent_full[ANALYSIS_START_DRAW:]
        latent_frames.append(latent)
        validation = pd.read_csv(chain_dir / "latent_validation.csv")
        validation_failures += int((~validation["passed"].astype(bool)).sum())
        for draw_index, state in enumerate(latent, start=1):
            assert_constraints(state, public, label=f"calibration_extension_chain{chain}_draw{draw_index}")

    status = pd.DataFrame(status_rows).sort_values("chain")
    parameter_draws = pd.concat(parameter_frames, ignore_index=True)
    acceptance = pd.concat(acceptance_frames, ignore_index=True)
    latent_draws = np.concatenate(latent_frames, axis=0)
    diagnostics = diagnostics_table(parameter_draws, output_dir=None)
    diagnostics.to_csv(OUTPUT_ROOT / "calibration_extension_parameter_diagnostics.csv", index=False)
    acceptance.to_csv(OUTPUT_ROOT / "calibration_extension_acceptance.csv", index=False)
    status.to_csv(OUTPUT_ROOT / "calibration_extension_chain_status.csv", index=False)
    acceptance_summary = (
        acceptance.groupby(["type", "block"])["acceptance_rate"]
        .agg(["min", "median", "max"])
        .reset_index()
    )
    acceptance_summary.to_csv(OUTPUT_ROOT / "calibration_extension_acceptance_summary.csv", index=False)

    diagnostic_index = diagnostics.set_index("parameter")
    primary_rows: list[dict[str, object]] = []
    for parameter in PRIMARY_PARAMETERS:
        coefficient_draws = parameter_draws.loc[
            parameter_draws["parameter"].eq(parameter), "value"
        ].to_numpy(dtype=float)
        irr_draws = np.exp(coefficient_draws)
        median, lower, upper = quantiles(irr_draws)
        truth_coefficient = float(truth["beta_by_term"][parameter])
        truth_irr = float(np.exp(truth_coefficient))
        diagnostic = diagnostic_index.loc[parameter]
        primary_rows.append(
            {
                "parameter": parameter,
                "truth_irr": truth_irr,
                "posterior_median_irr": median,
                "posterior_lower_95": lower,
                "posterior_upper_95": upper,
                "relative_bias_percent": (median / truth_irr - 1.0) * 100.0,
                "truth_covered_by_95_interval": bool(lower <= truth_irr <= upper),
                "r_hat": float(diagnostic["r_hat"]),
                "ess_bulk": float(diagnostic["ess_bulk"]),
                "ess_tail": float(diagnostic["ess_tail"]),
            }
        )
    primary = pd.DataFrame(primary_rows)
    primary.to_csv(OUTPUT_ROOT / "calibration_extension_primary_recovery.csv", index=False)

    latent_mean = latent_draws.mean(axis=0)
    latent_lower = np.quantile(latent_draws, 0.025, axis=0)
    latent_upper = np.quantile(latent_draws, 0.975, axis=0)
    cell = complete_table.copy()
    cell["posterior_mean"] = latent_mean
    cell["posterior_lower_95"] = latent_lower
    cell["posterior_upper_95"] = latent_upper
    cell["absolute_error"] = np.abs(latent_mean - complete_counts)
    cell["squared_error"] = np.square(latent_mean - complete_counts)
    cell["covered_95"] = (complete_counts >= latent_lower) & (complete_counts <= latent_upper)
    cell.to_csv(OUTPUT_ROOT / "calibration_extension_cell_recovery.csv", index=False)

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
                "cell_group": label,
                "cells": int(len(work)),
                "mean_absolute_error": float(work["absolute_error"].mean()),
                "root_mean_squared_error": float(np.sqrt(work["squared_error"].mean())),
                "coverage_95": float(work["covered_95"].mean()),
                "mean_interval_width": float(
                    (work["posterior_upper_95"] - work["posterior_lower_95"]).mean()
                ),
            }
        )
    recovery = pd.DataFrame(recovery_rows)
    recovery.to_csv(OUTPUT_ROOT / "calibration_extension_latent_recovery_summary.csv", index=False)

    primary_diag = diagnostics[diagnostics["parameter"].isin(PRIMARY_PARAMETERS)]
    suppressed = recovery[recovery["cell_group"].eq("suppressed_cells")].iloc[0]
    summary = {
        "chains_completed": int(status["status"].eq("completed").sum()),
        "total_retained_draws_per_chain": int(status["saved_draws"].min()),
        "diagnostic_tail_draws_per_chain": int(
            min(array.shape[0] for array in latent_frames)
        ),
        "discarded_combined_draws_per_chain": ANALYSIS_START_DRAW,
        "validation_failures": int(validation_failures),
        "maximum_primary_rhat": float(primary_diag["r_hat"].max()),
        "minimum_primary_bulk_ess": float(primary_diag["ess_bulk"].min()),
        "minimum_primary_tail_ess": float(primary_diag["ess_tail"].min()),
        "maximum_all_parameter_rhat": float(diagnostics["r_hat"].max()),
        "primary_truth_coverage_fraction": float(primary["truth_covered_by_95_interval"].mean()),
        "suppressed_cell_coverage_95": float(suppressed["coverage_95"]),
        "suppressed_cell_rmse": float(suppressed["root_mean_squared_error"]),
        "computational_gate_pass": bool(
            status["status"].eq("completed").all()
            and validation_failures == 0
            and np.isfinite(primary_diag[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(dtype=float)).all()
            and float(primary_diag["r_hat"].max()) < 1.05
            and float(primary_diag["ess_bulk"].min()) >= 100.0
            and float(primary_diag["ess_tail"].min()) >= 100.0
        ),
        "interpretation_boundary": (
            "One synthetic replicate after tuned extension. Bias and coverage remain descriptive until a prespecified multi-replicate calibration study is completed."
        ),
    }
    (OUTPUT_ROOT / "calibration_extension_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 tuned truth-known calibration extension",
        "",
        "The original four synthetic calibration chains were resumed for 20,000 additional iterations using proposal scales selected from the initial acceptance profile. Diagnostics use only the final 1,800 retained draws per chain.",
        "",
        "## Computational gate",
        "",
        f"- Chains completed: {summary['chains_completed']}/4",
        f"- Total retained draws per chain: {summary['total_retained_draws_per_chain']}",
        f"- Diagnostic tail draws per chain: {summary['diagnostic_tail_draws_per_chain']}",
        f"- Constraint-validation failures: {summary['validation_failures']}",
        f"- Maximum primary R-hat: {summary['maximum_primary_rhat']:.4f}",
        f"- Minimum primary bulk ESS: {summary['minimum_primary_bulk_ess']:.1f}",
        f"- Minimum primary tail ESS: {summary['minimum_primary_tail_ess']:.1f}",
        f"- Status: {'PASS' if summary['computational_gate_pass'] else 'HOLD'}",
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
            f"{row['relative_bias_percent']:.2f}% | {row['truth_covered_by_95_interval']} | "
            f"{row['r_hat']:.4f} | {row['ess_bulk']:.1f} |"
        )
    lines.extend(
        [
            "",
            f"Suppressed-cell 95% interval coverage in this one replicate was {summary['suppressed_cell_coverage_95']:.3f}; posterior-mean RMSE was {summary['suppressed_cell_rmse']:.3f} deaths.",
            "",
            "These are one-replicate diagnostics and do not establish nominal frequentist coverage or comparative superiority.",
        ]
    )
    (OUTPUT_ROOT / "calibration_extension_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not summary["computational_gate_pass"]:
        raise SystemExit("Tuned truth-known calibration extension is on HOLD; evidence has been written.")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
