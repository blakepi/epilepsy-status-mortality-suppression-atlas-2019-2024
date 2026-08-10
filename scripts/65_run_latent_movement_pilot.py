from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.latent_pilot import run_fixed_theta_latent_pilot, theta_from_parameter_summary  # noqa: E402


def main() -> None:
    frame = load_model_frame()
    initial_paths = sorted((ROOT / "data" / "processed" / "bayes_constrained").glob("initial_allocation_chain*.parquet"))
    if len(initial_paths) < 4:
        raise SystemExit(f"Expected at least four dispersed initial allocations; found {len(initial_paths)}.")
    initial_states = [pd.read_parquet(path)["latent_count"].to_numpy(dtype=int) for path in initial_paths[:4]]
    theta = theta_from_parameter_summary(
        frame,
        ROOT / "outputs" / "bayes_constrained" / "production_8chain" / "posterior_parameter_summary.csv",
    )
    outputs = run_fixed_theta_latent_pilot(
        frame,
        initial_states,
        theta,
        proposals_per_chain=25_000,
        record_every=500,
        seed=20260810,
        move_weights={
            "state_year_transfer": 0.45,
            "county_period_exploration": 0.20,
            "swap_2x2": 0.20,
            "cycle_swap": 0.15,
        },
        max_cycle_half_length=6,
    )

    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "latent_movement_pilot"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs.trajectories.to_csv(output_dir / "latent_pilot_trajectories.csv", index=False)
    outputs.acceptance.to_csv(output_dir / "latent_pilot_acceptance.csv", index=False)
    outputs.pairwise.to_csv(output_dir / "latent_pilot_pairwise.csv", index=False)

    final = outputs.trajectories.sort_values("proposal").groupby("chain", as_index=False).tail(1)
    acceptance_by_move = (
        outputs.acceptance.groupby("move")["acceptance_rate"]
        .agg(["min", "median", "max"])
        .reset_index()
    )
    pairwise_ratio = np.where(
        outputs.pairwise["starting_l1_distance_free"].to_numpy(dtype=float) > 0,
        outputs.pairwise["final_l1_distance_free"].to_numpy(dtype=float)
        / outputs.pairwise["starting_l1_distance_free"].to_numpy(dtype=float),
        np.nan,
    )
    summary = {
        "chains": int(final["chain"].nunique()),
        "proposals_per_chain": 25_000,
        "reference_theta": "v1.1.1 posterior medians used only for fixed-parameter movement diagnostics",
        "minimum_final_fraction_free_cells_changed": float(final["fraction_free_cells_changed"].min()),
        "median_final_fraction_free_cells_changed": float(final["fraction_free_cells_changed"].median()),
        "maximum_final_fraction_free_cells_changed": float(final["fraction_free_cells_changed"].max()),
        "minimum_final_l1_distance_free_cells": int(final["l1_distance_free_cells"].min()),
        "median_pairwise_final_to_start_l1_ratio": float(np.nanmedian(pairwise_ratio)),
        "unique_recorded_state_hashes": int(outputs.trajectories["state_hash"].nunique()),
        "all_recorded_states_constraint_valid": True,
        "acceptance_by_move": acceptance_by_move.to_dict("records"),
    }
    (output_dir / "latent_pilot_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Full-data fixed-theta latent movement pilot",
        "",
        "Four independently generated v1 initial allocations were evolved for 25,000 corrected latent-count proposals each while holding model parameters fixed at the archived v1.1.1 posterior medians. This is a movement and tuning diagnostic only; it is not a corrected posterior analysis and does not update the manuscript estimate.",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
        f"| Chains | {summary['chains']} |",
        f"| Proposals per chain | {summary['proposals_per_chain']:,} |",
        f"| Minimum final fraction of free cells changed | {summary['minimum_final_fraction_free_cells_changed']:.4f} |",
        f"| Median final fraction of free cells changed | {summary['median_final_fraction_free_cells_changed']:.4f} |",
        f"| Maximum final fraction of free cells changed | {summary['maximum_final_fraction_free_cells_changed']:.4f} |",
        f"| Minimum final L1 distance over free cells | {summary['minimum_final_l1_distance_free_cells']:,} |",
        f"| Median pairwise final/start L1 ratio | {summary['median_pairwise_final_to_start_l1_ratio']:.4f} |",
        f"| Unique recorded state hashes | {summary['unique_recorded_state_hashes']:,} |",
        "",
        "## Acceptance by move",
        "",
        "| Move | Minimum | Median | Maximum |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in summary["acceptance_by_move"]:
        lines.append(f"| {row['move']} | {row['min']:.4f} | {row['median']:.4f} | {row['max']:.4f} |")
    lines.extend(
        [
            "",
            "The next pilot must update parameters jointly, use eight independently dispersed starts, and compute latent-summary autocorrelation and between-chain convergence. No epidemiologic estimate is authorized from this fixed-theta diagnostic.",
        ]
    )
    (output_dir / "latent_pilot_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
