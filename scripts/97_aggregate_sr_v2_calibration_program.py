from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2"
PROGRAM_ROOT = OUTPUT_ROOT / "calibration_program"
EXPECTED_REPLICATES = {1: 4, 2: 16}
EXPECTED_SCENARIO_REPLICATES = 5


def exact_binomial_interval(
    successes: int,
    trials: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    if trials <= 0:
        return float("nan"), float("nan")
    lower = (
        0.0
        if successes == 0
        else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    )
    upper = (
        1.0
        if successes == trials
        else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    )
    return lower, upper


def read_batch_table(batch_id: int, filename: str) -> pd.DataFrame:
    path = (
        OUTPUT_ROOT
        / f"calibration_study_batch{batch_id}"
        / filename
    )
    if not path.exists():
        raise FileNotFoundError(f"Missing calibration evidence: {path}")
    frame = pd.read_csv(path)
    frame.insert(0, "batch", batch_id)
    return frame


def main() -> None:
    PROGRAM_ROOT.mkdir(parents=True, exist_ok=True)
    statuses = pd.concat(
        [
            read_batch_table(batch_id, "replicate_status.csv")
            for batch_id in EXPECTED_REPLICATES
        ],
        ignore_index=True,
    )
    primary = pd.concat(
        [
            read_batch_table(batch_id, "primary_recovery_all_replicates.csv")
            for batch_id in EXPECTED_REPLICATES
        ],
        ignore_index=True,
    )
    latent = pd.concat(
        [
            read_batch_table(batch_id, "latent_recovery_all_replicates.csv")
            for batch_id in EXPECTED_REPLICATES
        ],
        ignore_index=True,
    )
    comparators = pd.concat(
        [
            read_batch_table(batch_id, "comparator_results_all_replicates.csv")
            for batch_id in EXPECTED_REPLICATES
        ],
        ignore_index=True,
    )

    statuses.to_csv(PROGRAM_ROOT / "replicate_status.csv", index=False)
    primary.to_csv(PROGRAM_ROOT / "primary_recovery.csv", index=False)
    latent.to_csv(PROGRAM_ROOT / "latent_recovery.csv", index=False)
    comparators.to_csv(PROGRAM_ROOT / "comparator_results.csv", index=False)

    observed_by_batch = {
        int(batch_id): int(len(group))
        for batch_id, group in statuses.groupby("batch")
    }
    scenario_counts = {
        str(scenario): int(len(group))
        for scenario, group in statuses.groupby("scenario_id")
    }
    design_complete = bool(
        observed_by_batch == EXPECTED_REPLICATES
        and len(scenario_counts) == 4
        and all(
            count == EXPECTED_SCENARIO_REPLICATES
            for count in scenario_counts.values()
        )
    )
    computational_pass = bool(
        design_complete
        and statuses["computational_gate_pass"].astype(bool).all()
    )

    coefficient_rows: list[dict[str, object]] = []
    for parameter, group in primary.groupby("parameter", sort=False):
        covered = group["truth_covered_by_95_interval"].astype(bool)
        successes = int(covered.sum())
        trials = int(len(group))
        lower, upper = exact_binomial_interval(successes, trials)
        coefficient_rows.append(
            {
                "parameter": parameter,
                "replicates": trials,
                "coverage_successes": successes,
                "coverage_fraction": successes / trials,
                "coverage_exact_95_lower": lower,
                "coverage_exact_95_upper": upper,
                "mean_bias_irr": float(group["bias_irr"].mean()),
                "median_bias_irr": float(group["bias_irr"].median()),
                "root_mean_squared_error_irr": float(
                    np.sqrt(group["squared_error_irr"].mean())
                ),
                "median_absolute_relative_bias_percent": float(
                    group["relative_bias_percent"].abs().median()
                ),
                "median_interval_width": float(group["interval_width"].median()),
                "maximum_rhat": float(group["r_hat"].max()),
                "minimum_bulk_ess": float(group["ess_bulk"].min()),
                "minimum_tail_ess": float(group["ess_tail"].min()),
            }
        )
    coefficient = pd.DataFrame(coefficient_rows)
    coefficient.to_csv(
        PROGRAM_ROOT / "coefficient_calibration_summary.csv",
        index=False,
    )

    scenario_rows: list[dict[str, object]] = []
    for (scenario, parameter), group in primary.groupby(
        ["scenario", "parameter"],
        sort=False,
    ):
        successes = int(group["truth_covered_by_95_interval"].astype(bool).sum())
        trials = int(len(group))
        lower, upper = exact_binomial_interval(successes, trials)
        scenario_rows.append(
            {
                "truth_scenario": scenario,
                "parameter": parameter,
                "replicates": trials,
                "coverage_successes": successes,
                "coverage_fraction": successes / trials,
                "coverage_exact_95_lower": lower,
                "coverage_exact_95_upper": upper,
                "mean_bias_irr": float(group["bias_irr"].mean()),
                "root_mean_squared_error_irr": float(
                    np.sqrt(group["squared_error_irr"].mean())
                ),
            }
        )
    pd.DataFrame(scenario_rows).to_csv(
        PROGRAM_ROOT / "coefficient_by_scenario_summary.csv",
        index=False,
    )

    suppressed = latent[latent["cell_group"].eq("suppressed_cells")].copy()
    suppressed_cells = int(suppressed["cells"].sum())
    suppressed_coverage = float(
        np.average(suppressed["coverage_95"], weights=suppressed["cells"])
    )
    suppressed_rmse = float(
        np.sqrt(
            np.average(
                np.square(suppressed["root_mean_squared_error"]),
                weights=suppressed["cells"],
            )
        )
    )

    comparator_rows: list[dict[str, object]] = []
    for (handling, parameter), group in comparators.groupby(
        ["scenario", "term"],
        sort=False,
    ):
        successes = int(group["truth_covered_by_95_interval"].astype(bool).sum())
        trials = int(len(group))
        lower, upper = exact_binomial_interval(successes, trials)
        comparator_rows.append(
            {
                "handling_scenario": handling,
                "parameter": parameter,
                "replicates": trials,
                "coverage_successes": successes,
                "coverage_fraction": successes / trials,
                "coverage_exact_95_lower": lower,
                "coverage_exact_95_upper": upper,
                "mean_bias_irr": float(group["bias_irr"].mean()),
                "root_mean_squared_error_irr": float(
                    np.sqrt(group["squared_error_irr"].mean())
                ),
            }
        )
    pd.DataFrame(comparator_rows).to_csv(
        PROGRAM_ROOT / "comparator_calibration_summary.csv",
        index=False,
    )

    total_successes = int(
        primary["truth_covered_by_95_interval"].astype(bool).sum()
    )
    total_trials = int(len(primary))
    overall_lower, overall_upper = exact_binomial_interval(
        total_successes,
        total_trials,
    )
    descriptive_reporting_authorized = bool(
        computational_pass
        and len(statuses) == sum(EXPECTED_REPLICATES.values())
        and len(coefficient) == 6
        and (coefficient["replicates"] == len(statuses)).all()
    )
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "batches": sorted(EXPECTED_REPLICATES),
        "replicates": int(len(statuses)),
        "replicates_by_batch": observed_by_batch,
        "replicates_by_truth_scenario": scenario_counts,
        "design_complete": design_complete,
        "computational_gate_pass": computational_pass,
        "replicates_passing_computational_gate": int(
            statuses["computational_gate_pass"].astype(bool).sum()
        ),
        "maximum_primary_rhat": float(statuses["maximum_primary_rhat"].max()),
        "minimum_primary_bulk_ess": float(
            statuses["minimum_primary_bulk_ess"].min()
        ),
        "minimum_primary_tail_ess": float(
            statuses["minimum_primary_tail_ess"].min()
        ),
        "coefficient_interval_coverage_successes": total_successes,
        "coefficient_interval_coverage_trials": total_trials,
        "coefficient_interval_coverage_fraction": total_successes / total_trials,
        "coefficient_interval_coverage_exact_95_lower": overall_lower,
        "coefficient_interval_coverage_exact_95_upper": overall_upper,
        "suppressed_cells_total": suppressed_cells,
        "suppressed_cell_weighted_coverage_95": suppressed_coverage,
        "suppressed_cell_pooled_rmse": suppressed_rmse,
        "descriptive_calibration_reporting_authorized": (
            descriptive_reporting_authorized
        ),
        "precise_nominal_coverage_claim_authorized": False,
        "interpretation_boundary": (
            "The 20-replicate program authorizes descriptive reporting of bias, "
            "RMSE, interval coverage, convergence, and exact binomial Monte Carlo "
            "intervals. It does not authorize a claim that coverage has been "
            "estimated precisely or proven equal to the nominal 95% level."
        ),
    }
    (PROGRAM_ROOT / "calibration_program_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    gate = {
        "passed": descriptive_reporting_authorized,
        "gate": "descriptive_calibration_reporting",
        "required_replicates": sum(EXPECTED_REPLICATES.values()),
        "observed_replicates": int(len(statuses)),
        "required_replicates_per_truth_scenario": EXPECTED_SCENARIO_REPLICATES,
        "observed_replicates_by_truth_scenario": scenario_counts,
        "computational_gate_pass": computational_pass,
        "precise_nominal_coverage_claim_authorized": False,
    }
    (PROGRAM_ROOT / "calibration_reporting_gate.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Scientific Reports v2 truth-known calibration program",
        "",
        "## Reporting gate",
        "",
        f"- Replicates completed: {len(statuses)}/20",
        f"- Replicates passing computational gates: {summary['replicates_passing_computational_gate']}/{len(statuses)}",
        f"- Descriptive calibration reporting: {'AUTHORIZED' if descriptive_reporting_authorized else 'HOLD'}",
        "- Precise nominal-coverage claim: NOT AUTHORIZED",
        "",
        "## Coefficient recovery",
        "",
        "| Parameter | Coverage | Exact 95% Monte Carlo interval | RMSE (IRR) | Median absolute relative bias |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for _, row in coefficient.iterrows():
        lines.append(
            f"| {row['parameter']} | {int(row['coverage_successes'])}/"
            f"{int(row['replicates'])} ({row['coverage_fraction']:.3f}) | "
            f"{row['coverage_exact_95_lower']:.3f}-{row['coverage_exact_95_upper']:.3f} | "
            f"{row['root_mean_squared_error_irr']:.4f} | "
            f"{row['median_absolute_relative_bias_percent']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Suppressed-cell recovery",
            "",
            f"- Suppressed cells pooled across replicates: {suppressed_cells}",
            f"- Cell-weighted 95% interval coverage: {suppressed_coverage:.3f}",
            f"- Pooled posterior-mean RMSE: {suppressed_rmse:.3f} deaths",
            "",
            summary["interpretation_boundary"],
        ]
    )
    (PROGRAM_ROOT / "calibration_program_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    if not descriptive_reporting_authorized:
        raise SystemExit(
            "Calibration program reporting gate is on HOLD; evidence was written."
        )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
