from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "calibration_study_batch1"
REPLICATES = range(1, 5)


def exact_binomial_interval(successes: int, trials: int, alpha: float = 0.05) -> tuple[float, float]:
    if trials <= 0:
        return float("nan"), float("nan")
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    return lower, upper


def main() -> None:
    summary_rows: list[dict[str, object]] = []
    primary_frames: list[pd.DataFrame] = []
    latent_frames: list[pd.DataFrame] = []
    comparator_frames: list[pd.DataFrame] = []
    for replicate in REPLICATES:
        root = BATCH_ROOT / f"replicate_{replicate:02d}" / "summary"
        summary_path = root / "replicate_summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"Missing calibration replicate summary: {summary_path}")
        summary_rows.append(json.loads(summary_path.read_text(encoding="utf-8")))
        primary_frames.append(pd.read_csv(root / "primary_recovery.csv"))
        latent_frames.append(pd.read_csv(root / "latent_recovery_summary.csv"))
        comparator_frames.append(pd.read_csv(root / "comparator_results.csv"))

    summaries = pd.DataFrame(summary_rows).sort_values("replicate_id")
    primary = pd.concat(primary_frames, ignore_index=True)
    latent = pd.concat(latent_frames, ignore_index=True)
    comparators = pd.concat(comparator_frames, ignore_index=True)
    summaries.to_csv(BATCH_ROOT / "replicate_status.csv", index=False)
    primary.to_csv(BATCH_ROOT / "primary_recovery_all_replicates.csv", index=False)
    latent.to_csv(BATCH_ROOT / "latent_recovery_all_replicates.csv", index=False)
    comparators.to_csv(BATCH_ROOT / "comparator_results_all_replicates.csv", index=False)

    coefficient_rows: list[dict[str, object]] = []
    for parameter, group in primary.groupby("parameter", sort=False):
        successes = int(group["truth_covered_by_95_interval"].astype(bool).sum())
        trials = int(len(group))
        coverage_lower, coverage_upper = exact_binomial_interval(successes, trials)
        coefficient_rows.append(
            {
                "parameter": parameter,
                "replicates": trials,
                "coverage_successes": successes,
                "coverage_fraction": successes / trials,
                "coverage_exact_95_lower": coverage_lower,
                "coverage_exact_95_upper": coverage_upper,
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
    coefficient.to_csv(BATCH_ROOT / "coefficient_calibration_summary.csv", index=False)

    suppressed = latent[latent["cell_group"].eq("suppressed_cells")].copy()
    total_suppressed_cells = int(suppressed["cells"].sum())
    weighted_coverage = float(
        np.average(suppressed["coverage_95"], weights=suppressed["cells"])
    )
    weighted_mse = float(
        np.average(
            np.square(suppressed["root_mean_squared_error"]),
            weights=suppressed["cells"],
        )
    )
    pooled_suppressed = {
        "replicates": int(len(suppressed)),
        "suppressed_cells_total": total_suppressed_cells,
        "weighted_coverage_95": weighted_coverage,
        "pooled_root_mean_squared_error": float(np.sqrt(weighted_mse)),
        "median_replicate_coverage_95": float(suppressed["coverage_95"].median()),
        "minimum_replicate_coverage_95": float(suppressed["coverage_95"].min()),
        "maximum_replicate_coverage_95": float(suppressed["coverage_95"].max()),
        "median_replicate_interval_width": float(suppressed["mean_interval_width"].median()),
    }
    pd.DataFrame([pooled_suppressed]).to_csv(
        BATCH_ROOT / "suppressed_cell_calibration_summary.csv",
        index=False,
    )

    comparator_rows: list[dict[str, object]] = []
    for (scenario, term), group in comparators.groupby(["scenario", "term"], sort=False):
        successes = int(group["truth_covered_by_95_interval"].astype(bool).sum())
        trials = int(len(group))
        lower, upper = exact_binomial_interval(successes, trials)
        comparator_rows.append(
            {
                "handling_scenario": scenario,
                "parameter": term,
                "replicates": trials,
                "coverage_fraction": successes / trials,
                "coverage_exact_95_lower": lower,
                "coverage_exact_95_upper": upper,
                "mean_bias_irr": float(group["bias_irr"].mean()),
                "root_mean_squared_error_irr": float(
                    np.sqrt(group["squared_error_irr"].mean())
                ),
            }
        )
    comparator_summary = pd.DataFrame(comparator_rows)
    comparator_summary.to_csv(BATCH_ROOT / "comparator_calibration_summary.csv", index=False)

    computational_pass = bool(summaries["computational_gate_pass"].astype(bool).all())
    coverage_total_successes = int(primary["truth_covered_by_95_interval"].astype(bool).sum())
    coverage_total_trials = int(len(primary))
    overall_lower, overall_upper = exact_binomial_interval(
        coverage_total_successes,
        coverage_total_trials,
    )
    batch_summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "batch": 1,
        "replicates": int(len(summaries)),
        "scenarios": summaries["scenario_id"].tolist(),
        "computational_gate_pass": computational_pass,
        "replicates_passing_computational_gate": int(
            summaries["computational_gate_pass"].astype(bool).sum()
        ),
        "maximum_primary_rhat_across_replicates": float(
            summaries["maximum_primary_rhat"].max()
        ),
        "minimum_primary_bulk_ess_across_replicates": float(
            summaries["minimum_primary_bulk_ess"].min()
        ),
        "minimum_primary_tail_ess_across_replicates": float(
            summaries["minimum_primary_tail_ess"].min()
        ),
        "coefficient_interval_coverage_successes": coverage_total_successes,
        "coefficient_interval_coverage_trials": coverage_total_trials,
        "coefficient_interval_coverage_fraction": coverage_total_successes
        / coverage_total_trials,
        "coefficient_interval_coverage_exact_95_lower": overall_lower,
        "coefficient_interval_coverage_exact_95_upper": overall_upper,
        "suppressed_cell_summary": pooled_suppressed,
        "final_nominal_coverage_claim_authorized": False,
        "next_action": (
            "run_additional_prespecified_calibration_batches_before_manuscript_claims"
        ),
        "interpretation_boundary": (
            "This four-replicate batch spans event-rate and overdispersion conditions and is a substantive calibration increment, but it is too small for a precise nominal-coverage claim. Exact binomial intervals are reported to make that Monte Carlo uncertainty explicit."
        ),
    }
    (BATCH_ROOT / "batch1_summary.json").write_text(
        json.dumps(batch_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Scientific Reports v2 multi-replicate calibration, batch 1",
        "",
        "Four prespecified truth-known data sets varied the baseline event rate and negative-binomial overdispersion while preserving the same rurality, SVI, age-composition, sex-composition, state, and year effect structure.",
        "",
        "## Computational status",
        "",
        f"- Replicates completed: {len(summaries)}",
        f"- Replicates passing the computational gate: {batch_summary['replicates_passing_computational_gate']}/{len(summaries)}",
        f"- Maximum primary R-hat: {batch_summary['maximum_primary_rhat_across_replicates']:.4f}",
        f"- Minimum primary bulk ESS: {batch_summary['minimum_primary_bulk_ess_across_replicates']:.1f}",
        f"- Computational batch status: {'PASS' if computational_pass else 'HOLD'}",
        "",
        "## Coefficient recovery",
        "",
        "| Parameter | Coverage | Exact 95% interval for coverage | RMSE (IRR) | Median absolute relative bias |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for _, row in coefficient.iterrows():
        lines.append(
            f"| {row['parameter']} | {int(row['coverage_successes'])}/{int(row['replicates'])} "
            f"({row['coverage_fraction']:.3f}) | "
            f"{row['coverage_exact_95_lower']:.3f}–{row['coverage_exact_95_upper']:.3f} | "
            f"{row['root_mean_squared_error_irr']:.4f} | "
            f"{row['median_absolute_relative_bias_percent']:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Suppressed-cell recovery",
            "",
            f"- Pooled suppressed cells: {total_suppressed_cells}",
            f"- Cell-weighted 95% interval coverage: {weighted_coverage:.3f}",
            f"- Pooled posterior-mean RMSE: {np.sqrt(weighted_mse):.3f} deaths",
            "",
            "This batch is deliberately reported with exact binomial uncertainty. Four replicates cannot establish nominal 95% coverage; additional prespecified batches are required before the manuscript makes a calibration-performance claim.",
        ]
    )
    (BATCH_ROOT / "batch1_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not computational_pass:
        raise SystemExit(
            "Calibration batch 1 is on HOLD; aggregate evidence was written."
        )
    print(json.dumps(batch_summary, sort_keys=True))


if __name__ == "__main__":
    main()
