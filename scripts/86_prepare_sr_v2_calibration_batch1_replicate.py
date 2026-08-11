from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.calibration import (  # noqa: E402
    public_frame_from_complete_counts,
    save_calibration_case,
    simulate_complete_counts,
    suppression_summary,
)
from bayes_constrained.calibration_design import select_state_clustered_panel  # noqa: E402
from bayes_constrained.calibration_study import (  # noqa: E402
    make_scenario_truth,
    scenario_for_replicate,
)
from bayes_constrained.constraints import solve_feasible_allocation, validate_constraints  # noqa: E402
from bayes_constrained.data import load_model_frame  # noqa: E402


BATCH_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_study_batch1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicate-id", type=int, required=True, choices=range(1, 5))
    args = parser.parse_args()

    scenario = scenario_for_replicate(args.replicate_id)
    replicate_root = BATCH_ROOT / f"replicate_{args.replicate_id:02d}"
    design_root = replicate_root / "design"
    design_root.mkdir(parents=True, exist_ok=True)

    full = load_model_frame()
    panel = select_state_clustered_panel(full, max_states=6, counties_per_state=12)
    theta, truth = make_scenario_truth(panel, scenario)
    complete_counts = simulate_complete_counts(
        panel,
        theta,
        seed=scenario.count_seed,
    )
    public = public_frame_from_complete_counts(panel, complete_counts)
    save_calibration_case(
        design_root,
        complete_frame=panel,
        public_frame=public,
        complete_counts=complete_counts,
        truth=truth,
    )
    (design_root / "scenario.json").write_text(
        json.dumps(scenario.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    initialization_rows: list[dict[str, object]] = []
    allocations: list[np.ndarray] = []
    for chain_id in range(1, 5):
        seed = scenario.initialization_seed_base + chain_id
        allocation = solve_feasible_allocation(
            public,
            seed=seed,
            objective="random",
            time_limit_seconds=90,
        )
        validation = validate_constraints(allocation, public)
        if not validation.passed:
            raise AssertionError(
                f"Replicate {args.replicate_id} chain {chain_id} start is infeasible."
            )
        allocations.append(allocation)
        pd.DataFrame(
            {
                "county_fips": public["county_fips"].astype(str),
                "year": public["year"].astype(str),
                "latent_count": allocation.astype(int),
            }
        ).to_parquet(
            design_root / f"initial_allocation_chain_{chain_id:02d}.parquet",
            index=False,
        )
        initialization_rows.append(
            {
                "chain": chain_id,
                "seed": seed,
                "grand_total": int(allocation.sum()),
                "l1_distance_from_truth": int(
                    np.abs(allocation - complete_counts).sum()
                ),
                "different_cells_from_truth": int(
                    (allocation != complete_counts).sum()
                ),
                "validation_passed": bool(validation.passed),
            }
        )

    pairwise_rows: list[dict[str, object]] = []
    for (left_id, left), (right_id, right) in combinations(
        enumerate(allocations, start=1),
        2,
    ):
        pairwise_rows.append(
            {
                "left_chain": left_id,
                "right_chain": right_id,
                "l1_distance": int(np.abs(left - right).sum()),
                "different_cells": int((left != right).sum()),
            }
        )
    initializations = pd.DataFrame(initialization_rows)
    pairwise = pd.DataFrame(pairwise_rows)
    initializations.to_csv(design_root / "initialization_summary.csv", index=False)
    pairwise.to_csv(design_root / "initialization_pairwise_distances.csv", index=False)

    visibility = suppression_summary(public)
    overall = visibility[visibility["group"].eq("overall")].set_index("status")
    cells = {
        status: int(overall.loc[status, "cells"]) if status in overall.index else 0
        for status in ["exact", "suppressed_1_9", "zero"]
    }
    summary = {
        **scenario.to_dict(),
        "states": int(panel["state_fips"].nunique()),
        "counties": int(panel["county_fips"].nunique()),
        "county_year_rows": int(len(panel)),
        "grand_total": int(complete_counts.sum()),
        "exact_cells": cells["exact"],
        "suppressed_cells": cells["suppressed_1_9"],
        "zero_cells": cells["zero"],
        "suppressed_fraction": float(cells["suppressed_1_9"] / len(panel)),
        "minimum_pairwise_initialization_l1": int(pairwise["l1_distance"].min()),
        "median_pairwise_initialization_l1": float(pairwise["l1_distance"].median()),
        "all_initializations_valid": bool(initializations["validation_passed"].all()),
        "design_pass": bool(
            cells["suppressed_1_9"] > 0
            and cells["exact"] + cells["zero"] > 0
            and initializations["validation_passed"].all()
            and int(pairwise["l1_distance"].min()) > 0
        ),
        "interpretation_boundary": (
            "Truth-known calibration replicate design only; no empirical epidemiologic inference."
        ),
    }
    (design_root / "design_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Calibration batch 1, replicate {args.replicate_id}",
        "",
        f"Scenario: `{scenario.scenario_id}`",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
        f"| Baseline rate per 100,000 | {scenario.baseline_rate_per_100k:.2f} |",
        f"| NB2 kappa | {scenario.kappa:.2f} |",
        f"| County-year rows | {len(panel)} |",
        f"| Exact cells | {cells['exact']} |",
        f"| Suppressed 1–9 cells | {cells['suppressed_1_9']} |",
        f"| Zero cells | {cells['zero']} |",
        f"| Suppressed fraction | {summary['suppressed_fraction']:.4f} |",
        f"| Minimum pairwise start L1 distance | {summary['minimum_pairwise_initialization_l1']} |",
        f"| Design status | {'PASS' if summary['design_pass'] else 'HOLD'} |",
        "",
        "The complete counts are retained only as simulation truth. The analysis input contains exact cells, explicit zeros, bounded 1–9 cells, and compatible public-style aggregate constraints.",
    ]
    (design_root / "design_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not summary["design_pass"]:
        raise SystemExit(
            f"Calibration replicate {args.replicate_id} design is on HOLD."
        )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
