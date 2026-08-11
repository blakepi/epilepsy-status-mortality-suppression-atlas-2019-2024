from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.constraints import assert_constraints  # noqa: E402
from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402


PRIMARY_PARAMETERS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
]
ANALYSIS_START_DRAW = 300


def quantile_summary(values: np.ndarray) -> tuple[float, float, float]:
    lower, median, upper = np.quantile(np.asarray(values, dtype=float), [0.025, 0.5, 0.975])
    return float(median), float(lower), float(upper)


def proposal_multiplier_recommendations(
    acceptance: pd.DataFrame,
    current: dict[str, float],
) -> dict[str, float]:
    median = acceptance[acceptance["type"].eq("parameter")].groupby("block")["acceptance_rate"].median()
    recommended: dict[str, float] = {}
    for block, multiplier in current.items():
        rate = float(median.get(block, np.nan))
        factor = 1.0
        if np.isfinite(rate):
            if rate < 0.10:
                factor = 0.50
            elif rate < 0.18:
                factor = 0.75
            elif rate > 0.80:
                factor = 2.00
            elif rate > 0.60:
                factor = 1.50
            elif rate > 0.50:
                factor = 1.25
        recommended[block] = float(multiplier * factor)
    return recommended


def main() -> None:
    output_root = ROOT / "outputs" / "scientific_reports_v2" / "extended_joint_pilot"
    chain_dirs = sorted((output_root / "chains").glob("chain_*"))
    if len(chain_dirs) != 4:
        raise SystemExit(f"Expected four extended joint-pilot chains; found {len(chain_dirs)}.")

    frame = load_model_frame()
    free_mask = frame["q002_upper"].to_numpy(dtype=int) > frame["q002_lower"].to_numpy(dtype=int)
    parameter_frames: list[pd.DataFrame] = []
    acceptance_frames: list[pd.DataFrame] = []
    latent_arrays: dict[int, np.ndarray] = {}
    status_rows: list[dict[str, object]] = []
    validation_failures = 0

    for chain_dir in chain_dirs:
        chain = int(chain_dir.name.split("_")[-1])
        status = json.loads((chain_dir / "chain_status.json").read_text(encoding="utf-8"))
        status_rows.append({"chain": chain, **status})
        params = pd.read_parquet(chain_dir / "draws_params.parquet")
        params = params[pd.to_numeric(params["draw"], errors="coerce") > ANALYSIS_START_DRAW].copy()
        parameter_frames.append(params)
        acceptance_frames.append(pd.read_csv(chain_dir / "acceptance_rates.csv"))
        latent_full = np.load(chain_dir / "draws_latent.npz", allow_pickle=True)["y"].astype(int)
        if latent_full.shape[0] <= ANALYSIS_START_DRAW:
            raise SystemExit(
                f"Chain {chain} has {latent_full.shape[0]} latent draws; "
                f"cannot discard the first {ANALYSIS_START_DRAW}."
            )
        latent = latent_full[ANALYSIS_START_DRAW:]
        latent_arrays[chain] = latent
        validation = pd.read_csv(chain_dir / "latent_validation.csv")
        validation_failures += int((~validation["passed"].astype(bool)).sum())
        for draw_index in range(latent.shape[0]):
            assert_constraints(
                latent[draw_index],
                frame,
                label=f"extended_joint_chain{chain}_tail_draw{draw_index + 1}",
            )

    status_df = pd.DataFrame(status_rows).sort_values("chain")
    parameter_draws = pd.concat(parameter_frames, ignore_index=True)
    acceptance = pd.concat(acceptance_frames, ignore_index=True)
    parameter_diagnostics = diagnostics_table(parameter_draws, output_dir=None)
    parameter_diagnostics.to_csv(output_root / "extended_joint_parameter_diagnostics.csv", index=False)
    acceptance.to_csv(output_root / "extended_joint_acceptance.csv", index=False)
    status_df.to_csv(output_root / "extended_joint_chain_status.csv", index=False)

    archived = pd.read_csv(
        ROOT / "outputs" / "bayes_constrained" / "production_8chain" / "posterior_parameter_summary.csv"
    ).set_index("parameter")
    diag_index = parameter_diagnostics.set_index("parameter")
    primary_rows: list[dict[str, object]] = []
    for parameter in PRIMARY_PARAMETERS:
        values = np.exp(
            parameter_draws.loc[parameter_draws["parameter"].eq(parameter), "value"].to_numpy(dtype=float)
        )
        median, lower, upper = quantile_summary(values)
        archived_median = float(archived.loc[parameter, "posterior_median"])
        diag = diag_index.loc[parameter]
        primary_rows.append(
            {
                "parameter": parameter,
                "pilot_median_irr": median,
                "pilot_lower_95": lower,
                "pilot_upper_95": upper,
                "archived_v111_median_irr": archived_median,
                "pilot_minus_v111": median - archived_median,
                "pilot_relative_shift_percent": (median / archived_median - 1.0) * 100.0,
                "r_hat": float(diag["r_hat"]),
                "ess_bulk": float(diag["ess_bulk"]),
                "ess_tail": float(diag["ess_tail"]),
            }
        )
    primary = pd.DataFrame(primary_rows)
    primary.to_csv(output_root / "extended_joint_primary_estimates.csv", index=False)

    category_masks: dict[str, np.ndarray] = {}
    for column, prefix in [("primary_rurality", "rurality"), ("svi_quartile", "svi")]:
        for category in sorted(frame[column].astype(str).unique()):
            category_masks[f"latent_{prefix}_total[{category}]"] = (
                frame[column].astype(str).eq(category).to_numpy()
            )

    latent_summary_rows: list[dict[str, object]] = []
    movement_rows: list[dict[str, object]] = []
    initial_paths = sorted(
        (ROOT / "data" / "processed" / "bayes_constrained").glob("initial_allocation_chain*.parquet")
    )
    for chain, latent in latent_arrays.items():
        initial = pd.read_parquet(initial_paths[(chain - 1) % len(initial_paths)])["latent_count"].to_numpy(dtype=int)
        for draw_index, state in enumerate(latent, start=1):
            difference = state - initial
            movement_rows.append(
                {
                    "chain": chain,
                    "draw": draw_index,
                    "l1_distance_free_cells": int(np.abs(difference[free_mask]).sum()),
                    "changed_free_cells": int((difference[free_mask] != 0).sum()),
                    "fraction_free_cells_changed": float((difference[free_mask] != 0).mean()),
                }
            )
            for parameter, mask in category_masks.items():
                latent_summary_rows.append(
                    {
                        "chain": chain,
                        "draw": draw_index,
                        "parameter": parameter,
                        "value": float(state[mask].sum()),
                    }
                )
    movement = pd.DataFrame(movement_rows)
    movement.to_csv(output_root / "extended_joint_latent_movement.csv", index=False)
    latent_summary_draws = pd.DataFrame(latent_summary_rows)
    latent_diagnostics = diagnostics_table(latent_summary_draws, output_dir=None)
    latent_diagnostics.to_csv(output_root / "extended_joint_latent_summary_diagnostics.csv", index=False)

    resolved_config = yaml.safe_load(
        (output_root / "extended_joint_pilot_chain_01_config.yaml").read_text(encoding="utf-8")
    )
    current_multipliers = {
        key: float(value)
        for key, value in resolved_config["run"]["proposal_scale_multipliers"].items()
    }
    recommended_multipliers = proposal_multiplier_recommendations(acceptance, current_multipliers)
    acceptance_summary = (
        acceptance.groupby(["type", "block"])["acceptance_rate"]
        .agg(["min", "median", "max"])
        .reset_index()
    )
    acceptance_summary.to_csv(output_root / "extended_joint_acceptance_summary.csv", index=False)

    primary_diag = parameter_diagnostics[
        parameter_diagnostics["parameter"].isin(PRIMARY_PARAMETERS)
    ].copy()
    finite_primary = np.isfinite(
        primary_diag[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(dtype=float)
    ).all()
    final_movement = movement.sort_values("draw").groupby("chain", as_index=False).tail(1)
    total_retained = min(int(row["saved_draws"]) for row in status_rows)
    summary = {
        "chains_completed": int(status_df["status"].eq("completed").sum()),
        "total_retained_draws_per_chain": int(total_retained),
        "diagnostic_tail_draws_per_chain": int(min(array.shape[0] for array in latent_arrays.values())),
        "discarded_combined_draws_per_chain": ANALYSIS_START_DRAW,
        "validation_failures": int(validation_failures),
        "maximum_primary_rhat": float(primary_diag["r_hat"].max()),
        "minimum_primary_bulk_ess": float(primary_diag["ess_bulk"].min()),
        "minimum_primary_tail_ess": float(primary_diag["ess_tail"].min()),
        "maximum_all_parameter_rhat": float(parameter_diagnostics["r_hat"].max()),
        "maximum_latent_summary_rhat": float(latent_diagnostics["r_hat"].max()),
        "minimum_latent_summary_bulk_ess": float(latent_diagnostics["ess_bulk"].min()),
        "median_final_fraction_free_cells_changed": float(
            final_movement["fraction_free_cells_changed"].median()
        ),
        "recommended_proposal_scale_multipliers": recommended_multipliers,
        "pilot_pass": bool(
            status_df["status"].eq("completed").all()
            and validation_failures == 0
            and finite_primary
            and float(primary_diag["r_hat"].max()) < 1.10
            and float(primary_diag["ess_bulk"].min()) >= 50.0
            and float(latent_diagnostics["r_hat"].max()) < 1.15
            and float(latent_diagnostics["ess_bulk"].min()) >= 30.0
        ),
        "interpretation_boundary": (
            "Extended tuning pilot only; no corrected epidemiologic estimate is authorized."
        ),
    }
    (output_root / "extended_joint_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "recommended_production_tuning.yaml").write_text(
        yaml.safe_dump(
            {
                "proposal_scale_multipliers": recommended_multipliers,
                "move_weights": resolved_config["run"]["move_weights"],
                "max_cycle_half_length": resolved_config["run"]["max_cycle_half_length"],
                "source": "Scientific Reports v2 four-chain extended joint tuning pilot",
                "not_for_inference": True,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Scientific Reports v2 extended corrected joint pilot",
        "",
        (
            "Four corrected chains were resumed from the short joint pilot and extended to "
            "10,000 total iterations. Diagnostics use only the final 650 retained draws per chain, "
            "after discarding the original 100 draws and the first 200 extension draws."
        ),
        "",
        "## Gate summary",
        "",
        f"- Chains completed: {summary['chains_completed']}/4",
        f"- Total retained draws per chain: {summary['total_retained_draws_per_chain']}",
        f"- Diagnostic tail draws per chain: {summary['diagnostic_tail_draws_per_chain']}",
        f"- Constraint-validation failures: {summary['validation_failures']}",
        f"- Maximum primary-parameter R-hat: {summary['maximum_primary_rhat']:.4f}",
        f"- Minimum primary bulk ESS: {summary['minimum_primary_bulk_ess']:.1f}",
        f"- Maximum latent-summary R-hat: {summary['maximum_latent_summary_rhat']:.4f}",
        f"- Minimum latent-summary bulk ESS: {summary['minimum_latent_summary_bulk_ess']:.1f}",
        (
            "- Median final fraction of free cells changed from the original dispersed starts: "
            f"{summary['median_final_fraction_free_cells_changed']:.4f}"
        ),
        f"- Extended pilot status: {'PASS' if summary['pilot_pass'] else 'HOLD'}",
        "",
        "## Primary contrasts, explicitly nonfinal",
        "",
        "| Parameter | Pilot median | Pilot 95% interval | v1.1.1 median | Relative shift | R-hat | Bulk ESS |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in primary.iterrows():
        lines.append(
            f"| {row['parameter']} | {row['pilot_median_irr']:.4f} | "
            f"{row['pilot_lower_95']:.4f}–{row['pilot_upper_95']:.4f} | "
            f"{row['archived_v111_median_irr']:.4f} | "
            f"{row['pilot_relative_shift_percent']:.2f}% | "
            f"{row['r_hat']:.4f} | {row['ess_bulk']:.1f} |"
        )
    lines.extend(
        [
            "",
            (
                "These values remain tuning evidence and must not be copied into the manuscript. "
                "A corrected eight-chain production run requires prespecified final convergence "
                "thresholds and complete parameter and latent-summary validation."
            ),
        ]
    )
    (output_root / "extended_joint_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not summary["pilot_pass"]:
        raise SystemExit("Extended corrected joint pilot is on HOLD; evidence has been written.")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
