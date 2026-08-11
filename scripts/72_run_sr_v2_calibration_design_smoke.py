from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.calibration import (  # noqa: E402
    make_calibration_truth,
    public_frame_from_complete_counts,
    save_calibration_case,
    simulate_complete_counts,
    suppression_summary,
)
from bayes_constrained.calibration_design import select_state_clustered_panel  # noqa: E402
from bayes_constrained.constraints import solve_feasible_allocation, validate_constraints  # noqa: E402
from bayes_constrained.data import load_model_frame  # noqa: E402


def main() -> None:
    output = ROOT / "outputs" / "scientific_reports_v2" / "calibration_design_smoke"
    output.mkdir(parents=True, exist_ok=True)

    full = load_model_frame()
    panel = select_state_clustered_panel(full, max_states=6, counties_per_state=12)
    theta, truth = make_calibration_truth(panel, seed=20260811)
    counts = simulate_complete_counts(panel, theta, seed=20260812)
    public = public_frame_from_complete_counts(panel, counts)
    save_calibration_case(
        output,
        complete_frame=panel,
        public_frame=public,
        complete_counts=counts,
        truth=truth,
    )

    allocation_rows: list[dict[str, object]] = []
    allocations: list[np.ndarray] = []
    for index, seed in enumerate([31001, 31002, 31003, 31004], start=1):
        allocation = solve_feasible_allocation(
            public,
            seed=seed,
            objective="random",
            time_limit_seconds=60,
        )
        result = validate_constraints(allocation, public)
        if not result.passed:
            raise AssertionError(f"Calibration initialization {index} is infeasible.")
        allocations.append(allocation)
        pd.DataFrame(
            {
                "county_fips": public["county_fips"].astype(str),
                "year": public["year"].astype(str),
                "latent_count": allocation,
            }
        ).to_parquet(output / f"feasible_initialization_{index}.parquet", index=False)
        allocation_rows.append(
            {
                "initialization": index,
                "seed": seed,
                "grand_total": int(allocation.sum()),
                "l1_distance_from_truth": int(np.abs(allocation - counts).sum()),
                "changed_cells_from_truth": int((allocation != counts).sum()),
                "validation_passed": bool(result.passed),
            }
        )

    pairwise_rows: list[dict[str, object]] = []
    for (left_index, left), (right_index, right) in combinations(enumerate(allocations, start=1), 2):
        pairwise_rows.append(
            {
                "left_initialization": left_index,
                "right_initialization": right_index,
                "l1_distance": int(np.abs(left - right).sum()),
                "different_cells": int((left != right).sum()),
            }
        )
    allocation_table = pd.DataFrame(allocation_rows)
    pairwise_table = pd.DataFrame(pairwise_rows)
    allocation_table.to_csv(output / "feasible_initializations.csv", index=False)
    pairwise_table.to_csv(output / "initialization_pairwise_distances.csv", index=False)

    visibility = suppression_summary(public)
    overall = visibility[visibility["group"].eq("overall")].set_index("status")
    cell_counts = {
        status: int(overall.loc[status, "cells"]) if status in overall.index else 0
        for status in ["exact", "suppressed_1_9", "zero"]
    }
    period = public.drop_duplicates("county_fips")["q001_period_status"].value_counts()
    summary = {
        "states": int(panel["state_fips"].nunique()),
        "counties": int(panel["county_fips"].nunique()),
        "county_year_rows": int(len(panel)),
        "grand_total": int(counts.sum()),
        "exact_county_year_cells": cell_counts["exact"],
        "suppressed_county_year_cells": cell_counts["suppressed_1_9"],
        "zero_county_year_cells": cell_counts["zero"],
        "suppressed_fraction": float(cell_counts["suppressed_1_9"] / len(panel)),
        "county_period_exact": int(period.get("exact", 0)),
        "county_period_suppressed": int(period.get("suppressed_1_9", 0)),
        "county_period_zero": int(period.get("zero", 0)),
        "minimum_pairwise_initialization_l1": int(pairwise_table["l1_distance"].min()),
        "median_pairwise_initialization_l1": float(pairwise_table["l1_distance"].median()),
        "all_initializations_valid": bool(allocation_table["validation_passed"].all()),
        "design_pass": bool(
            cell_counts["exact"] > 0
            and cell_counts["suppressed_1_9"] > 0
            and cell_counts["zero"] > 0
            and allocation_table["validation_passed"].all()
            and int(pairwise_table["l1_distance"].min()) > 0
        ),
        "interpretation_boundary": (
            "Synthetic design and initialization smoke test only; no method-performance claim."
        ),
    }
    (output / "calibration_design_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 calibration-design smoke test",
        "",
        "A deterministic six-state, 72-county, six-year panel was selected from the real model frame. Complete NB2 counts were generated under known rurality, SVI, age, sex, year, and state effects, then subjected to the same 1–9 cell suppression rule and compatible county-period/state-year/national constraints.",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
        f"| states | {summary['states']} |",
        f"| counties | {summary['counties']} |",
        f"| county-year rows | {summary['county_year_rows']} |",
        f"| exact cells | {summary['exact_county_year_cells']} |",
        f"| suppressed cells | {summary['suppressed_county_year_cells']} |",
        f"| zero cells | {summary['zero_county_year_cells']} |",
        f"| suppressed fraction | {summary['suppressed_fraction']:.4f} |",
        f"| minimum pairwise initialization L1 distance | {summary['minimum_pairwise_initialization_l1']} |",
        f"| design gate | {'PASS' if summary['design_pass'] else 'HOLD'} |",
        "",
        "This validates the truth-known data generator, disclosure transformation, aggregate construction, feasibility solver, and dispersed-start construction. It does not yet evaluate estimator bias or interval coverage.",
    ]
    (output / "calibration_design_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not summary["design_pass"]:
        raise SystemExit("Calibration-design smoke test is on HOLD; evidence was written.")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
