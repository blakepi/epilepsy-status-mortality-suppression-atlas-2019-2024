from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.latent_pilot import run_fixed_theta_latent_pilot, theta_from_parameter_summary  # noqa: E402


PROFILES = {
    "balanced_circuit_heatbath": {
        "state_year_transfer": 0.05,
        "county_period_exploration": 0.30,
        "interval_path_transfer": 0.25,
        "swap_2x2": 0.30,
        "cycle_swap": 0.10,
    },
    "interval_path_heavy": {
        "state_year_transfer": 0.05,
        "county_period_exploration": 0.25,
        "interval_path_transfer": 0.40,
        "swap_2x2": 0.25,
        "cycle_swap": 0.05,
    },
    "direct_interval_heavy": {
        "state_year_transfer": 0.05,
        "county_period_exploration": 0.45,
        "interval_path_transfer": 0.20,
        "swap_2x2": 0.25,
        "cycle_swap": 0.05,
    },
    "exact_margin_heavy": {
        "state_year_transfer": 0.05,
        "county_period_exploration": 0.20,
        "interval_path_transfer": 0.20,
        "swap_2x2": 0.50,
        "cycle_swap": 0.05,
    },
}


def pairwise_group_ratio(trajectories: pd.DataFrame) -> float:
    group_columns = [
        column
        for column in trajectories.columns
        if column.startswith("rurality_total__") or column.startswith("svi_total__")
    ]
    start = trajectories.sort_values("proposal").groupby("chain", as_index=False).head(1).set_index("chain")
    final = trajectories.sort_values("proposal").groupby("chain", as_index=False).tail(1).set_index("chain")
    ratios: list[float] = []
    chains = sorted(start.index)
    for left_index, left in enumerate(chains):
        for right in chains[left_index + 1 :]:
            starting = float(np.abs(start.loc[left, group_columns] - start.loc[right, group_columns]).sum())
            ending = float(np.abs(final.loc[left, group_columns] - final.loc[right, group_columns]).sum())
            if starting > 0:
                ratios.append(ending / starting)
    return float(np.median(ratios)) if ratios else np.nan


def main() -> None:
    frame = load_model_frame()
    initial_paths = sorted((ROOT / "data" / "processed" / "bayes_constrained").glob("initial_allocation_chain*.parquet"))
    if len(initial_paths) < 4:
        raise SystemExit(f"Expected four initial allocations; found {len(initial_paths)}.")
    initial_states = [pd.read_parquet(path)["latent_count"].to_numpy(dtype=int) for path in initial_paths[:4]]
    theta = theta_from_parameter_summary(
        frame,
        ROOT / "outputs" / "bayes_constrained" / "production_8chain" / "posterior_parameter_summary.csv",
    )

    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "latent_tuning"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, object]] = []

    for profile_index, (profile_name, weights) in enumerate(PROFILES.items(), start=1):
        started = time.perf_counter()
        outputs = run_fixed_theta_latent_pilot(
            frame,
            initial_states,
            theta,
            proposals_per_chain=20_000,
            record_every=500,
            seed=20260810 + 1000 * profile_index,
            move_weights=weights,
            max_cycle_half_length=6,
        )
        elapsed = time.perf_counter() - started
        profile_dir = output_dir / profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        outputs.trajectories.to_csv(profile_dir / "trajectories.csv", index=False)
        outputs.acceptance.to_csv(profile_dir / "acceptance.csv", index=False)
        outputs.pairwise.to_csv(profile_dir / "pairwise.csv", index=False)

        final = outputs.trajectories.sort_values("proposal").groupby("chain", as_index=False).tail(1)
        pairwise_ratio = np.where(
            outputs.pairwise["starting_l1_distance_free"].to_numpy(dtype=float) > 0,
            outputs.pairwise["final_l1_distance_free"].to_numpy(dtype=float)
            / outputs.pairwise["starting_l1_distance_free"].to_numpy(dtype=float),
            np.nan,
        )
        accepted_total = int(outputs.acceptance["accepted"].sum())
        proposed_total = int(outputs.acceptance["proposed"].sum())
        changed_fraction = float(final["fraction_free_cells_changed"].median())
        cell_distance_ratio = float(np.nanmedian(pairwise_ratio))
        group_distance_ratio = pairwise_group_ratio(outputs.trajectories)
        # Higher is better. Cell exploration matters, but convergence of
        # rurality/SVI latent totals receives the greatest weight because it is
        # closest to the manuscript estimands.
        score = (
            0.35 * changed_fraction
            + 0.25 * (1.0 - cell_distance_ratio)
            + 0.40 * (1.0 - group_distance_ratio)
        )
        row: dict[str, object] = {
            "profile": profile_name,
            "proposals_per_chain": 20_000,
            "elapsed_seconds": elapsed,
            "overall_changed_proposal_fraction": accepted_total / proposed_total,
            "median_final_fraction_free_cells_changed": changed_fraction,
            "median_pairwise_final_to_start_cell_l1_ratio": cell_distance_ratio,
            "median_pairwise_final_to_start_rurality_svi_ratio": group_distance_ratio,
            "selection_score": score,
        }
        row.update({f"weight_{key}": value for key, value in weights.items()})
        for move, group in outputs.acceptance.groupby("move"):
            row[f"median_change_fraction_{move}"] = float(group["acceptance_rate"].median())
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows).sort_values("selection_score", ascending=False).reset_index(drop=True)
    summary.to_csv(output_dir / "latent_tuning_profiles.csv", index=False)
    selected_name = str(summary.iloc[0]["profile"])
    selected_weights = PROFILES[selected_name]
    selected = {
        "selected_profile": selected_name,
        "selection_rule": "0.35*cell exploration + 0.25*cell-distance reduction + 0.40*rurality/SVI-distance reduction",
        "pilot_proposals_per_chain": 20_000,
        "move_weights": selected_weights,
        "max_cycle_half_length": 6,
        "profile_metrics": summary.iloc[0].to_dict(),
        "interpretation_boundary": "Fixed-theta tuning only; does not estimate the corrected epidemiologic posterior.",
    }
    (output_dir / "selected_latent_tuning.json").write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "selected_latent_tuning.yaml").write_text(
        yaml.safe_dump(selected, sort_keys=False), encoding="utf-8"
    )

    lines = [
        "# Scientific Reports v2 latent-move profile comparison",
        "",
        "Four circuit-aware proposal mixtures were compared from the same four dispersed feasible allocations with model parameters held fixed. Selection prioritizes convergence of rurality/SVI latent totals, then cell-space distance reduction and breadth of cell exploration.",
        "",
        "| Profile | Changed proposals | Free cells changed | Cell-distance ratio | Rurality/SVI-distance ratio | Score | Runtime (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['profile']} | {row['overall_changed_proposal_fraction']:.4f} | "
            f"{row['median_final_fraction_free_cells_changed']:.4f} | "
            f"{row['median_pairwise_final_to_start_cell_l1_ratio']:.4f} | "
            f"{row['median_pairwise_final_to_start_rurality_svi_ratio']:.4f} | "
            f"{row['selection_score']:.4f} | {row['elapsed_seconds']:.1f} |"
        )
    lines.extend(
        [
            "",
            f"Selected profile: **{selected_name}**.",
            "",
            "This profile is eligible for a short joint parameter/latent pilot. It is not yet a production setting and may be revised if joint-chain diagnostics expose a different bottleneck.",
        ]
    )
    (output_dir / "latent_tuning_profiles.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(selected, sort_keys=True))


if __name__ == "__main__":
    main()
