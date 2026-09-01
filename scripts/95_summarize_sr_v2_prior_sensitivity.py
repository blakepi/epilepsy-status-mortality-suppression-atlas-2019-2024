from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402
from bayes_constrained.model import PRIMARY_TERMS  # noqa: E402


PRODUCTION_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"
SENSITIVITY_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "prior_sensitivity"
PROFILES = ("broader", "regularizing")


def quantiles(values: np.ndarray) -> tuple[float, float, float]:
    lower, median, upper = np.quantile(
        np.asarray(values, dtype=float),
        [0.025, 0.5, 0.975],
    )
    return float(median), float(lower), float(upper)


def main() -> None:
    gate_path = PRODUCTION_ROOT / "production_gate.json"
    if not gate_path.exists():
        raise FileNotFoundError(gate_path)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if not gate.get("passed", False):
        raise SystemExit(
            "Corrected production gate did not pass; prior sensitivity is not interpretable."
        )
    primary_path = PRODUCTION_ROOT / "posterior_primary_summary.csv"
    if not primary_path.exists():
        raise FileNotFoundError(primary_path)
    production_primary = pd.read_csv(primary_path).set_index("parameter")

    comparison_frames: list[pd.DataFrame] = []
    profile_summaries: list[dict[str, object]] = []
    for profile in PROFILES:
        root = SENSITIVITY_ROOT / profile
        config_path = root / "config" / "prior_sensitivity.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        chain_dirs = sorted((root / "chains").glob("chain_*"))
        if len(chain_dirs) != 4:
            raise SystemExit(
                f"Expected four {profile} prior-sensitivity chains; found {len(chain_dirs)}."
            )
        parameter_frames: list[pd.DataFrame] = []
        acceptance_frames: list[pd.DataFrame] = []
        validation_frames: list[pd.DataFrame] = []
        status_rows: list[dict[str, object]] = []
        for chain_dir in chain_dirs:
            chain = int(chain_dir.name.split("_")[-1])
            status = json.loads(
                (chain_dir / "chain_status.json").read_text(encoding="utf-8")
            )
            status_rows.append({"chain": chain, **status})
            parameter_frames.append(
                pd.read_parquet(chain_dir / "draws_params.parquet")
            )
            acceptance = pd.read_csv(chain_dir / "acceptance_rates.csv")
            acceptance["chain"] = chain
            acceptance_frames.append(acceptance)
            validation = pd.read_csv(chain_dir / "latent_validation.csv")
            validation["chain"] = chain
            validation_frames.append(validation)

        status = pd.DataFrame(status_rows).sort_values("chain")
        parameter_draws = pd.concat(parameter_frames, ignore_index=True)
        acceptance = pd.concat(acceptance_frames, ignore_index=True)
        validation = pd.concat(validation_frames, ignore_index=True)
        diagnostics = diagnostics_table(parameter_draws, output_dir=None)
        diagnostics.to_csv(root / "parameter_diagnostics.csv", index=False)
        status.to_csv(root / "chain_status_summary.csv", index=False)
        acceptance.to_csv(root / "acceptance_rates.csv", index=False)
        (
            acceptance.groupby(["type", "block"])["acceptance_rate"]
            .agg(["min", "median", "max"])
            .reset_index()
            .to_csv(root / "acceptance_summary.csv", index=False)
        )
        validation.to_csv(
            root / "latent_validation.csv.gz",
            index=False,
            compression="gzip",
        )

        diagnostic_index = diagnostics.set_index("parameter")
        rows: list[dict[str, object]] = []
        for parameter in PRIMARY_TERMS:
            values = parameter_draws.loc[
                parameter_draws["parameter"].eq(parameter),
                "value",
            ].to_numpy(dtype=float)
            reported = np.exp(values) if parameter.startswith(("primary_rurality_", "svi_quartile_")) else values
            median, lower, upper = quantiles(reported)
            production = production_primary.loc[parameter]
            production_median = float(production["posterior_median"])
            diagnostic = diagnostic_index.loc[parameter]
            rows.append(
                {
                    "profile": profile,
                    "parameter": parameter,
                    "sensitivity_median": median,
                    "sensitivity_lower_95": lower,
                    "sensitivity_upper_95": upper,
                    "sensitivity_interval_width": upper - lower,
                    "primary_median": production_median,
                    "primary_lower_95": float(
                        production["credible_interval_lower_95"]
                    ),
                    "primary_upper_95": float(
                        production["credible_interval_upper_95"]
                    ),
                    "absolute_shift": median - production_median,
                    "relative_shift_percent": (
                        (median / production_median - 1.0) * 100.0
                        if production_median != 0
                        else np.nan
                    ),
                    "primary_value_inside_sensitivity_interval": bool(
                        lower <= production_median <= upper
                    ),
                    "r_hat": float(diagnostic["r_hat"]),
                    "ess_bulk": float(diagnostic["ess_bulk"]),
                    "ess_tail": float(diagnostic["ess_tail"]),
                }
            )
        comparison = pd.DataFrame(rows)
        comparison.to_csv(root / "primary_comparison.csv", index=False)
        comparison_frames.append(comparison)

        thresholds = config["diagnostics"]
        primary_diagnostics = diagnostics[
            diagnostics["parameter"].isin(PRIMARY_TERMS)
        ]
        validation_failures = int(
            (~validation["passed"].astype(bool)).sum()
        )
        profile_pass = bool(
            status["status"].eq("completed").all()
            and validation_failures == 0
            and np.isfinite(
                diagnostics[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(
                    dtype=float
                )
            ).all()
            and float(diagnostics["r_hat"].max())
            <= float(thresholds["rhat_max_all"])
            and float(diagnostics["ess_bulk"].min())
            >= float(thresholds["ess_bulk_min_all"])
            and float(diagnostics["ess_tail"].min())
            >= float(thresholds["ess_tail_min_all"])
            and float(primary_diagnostics["r_hat"].max())
            <= float(thresholds["rhat_max_primary"])
            and float(primary_diagnostics["ess_bulk"].min())
            >= float(thresholds["ess_bulk_min_primary"])
            and float(primary_diagnostics["ess_tail"].min())
            >= float(thresholds["ess_tail_min_primary"])
        )
        profile_summary = {
            "profile": profile,
            "chains_completed": int(status["status"].eq("completed").sum()),
            "draws_per_chain": int(status["saved_draws"].min()),
            "validation_failures": validation_failures,
            "maximum_all_parameter_rhat": float(diagnostics["r_hat"].max()),
            "minimum_all_parameter_bulk_ess": float(
                diagnostics["ess_bulk"].min()
            ),
            "minimum_all_parameter_tail_ess": float(
                diagnostics["ess_tail"].min()
            ),
            "maximum_primary_rhat": float(
                primary_diagnostics["r_hat"].max()
            ),
            "minimum_primary_bulk_ess": float(
                primary_diagnostics["ess_bulk"].min()
            ),
            "minimum_primary_tail_ess": float(
                primary_diagnostics["ess_tail"].min()
            ),
            "maximum_absolute_primary_relative_shift_percent": float(
                comparison["relative_shift_percent"].abs().max()
            ),
            "all_primary_values_inside_sensitivity_intervals": bool(
                comparison[
                    "primary_value_inside_sensitivity_interval"
                ].all()
            ),
            "computational_gate_pass": profile_pass,
        }
        (root / "summary.json").write_text(
            json.dumps(profile_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        profile_summaries.append(profile_summary)

    combined = pd.concat(comparison_frames, ignore_index=True)
    combined.to_csv(
        SENSITIVITY_ROOT / "prior_sensitivity_primary_comparison.csv",
        index=False,
    )
    all_passed = all(
        bool(summary["computational_gate_pass"])
        for summary in profile_summaries
    )
    batch = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "profiles": profile_summaries,
        "computational_gate_pass": all_passed,
        "maximum_absolute_primary_relative_shift_percent": float(
            combined["relative_shift_percent"].abs().max()
        ),
        "all_primary_values_inside_sensitivity_intervals": bool(
            combined["primary_value_inside_sensitivity_interval"].all()
        ),
        "interpretation_boundary": (
            "Prior sensitivity quantifies model dependence around the passed corrected primary analysis. Agreement is judged by direction, interval overlap, and material effect-size change rather than third-decimal identity."
        ),
    }
    (SENSITIVITY_ROOT / "prior_sensitivity_summary.json").write_text(
        json.dumps(batch, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 prior sensitivity",
        "",
        f"Computational status: **{'PASS' if all_passed else 'HOLD'}**",
        "",
        "| Profile | Chains | Maximum primary R-hat | Minimum primary bulk ESS | Maximum absolute primary shift | Primary values inside sensitivity intervals |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for summary in profile_summaries:
        lines.append(
            f"| {summary['profile']} | {summary['chains_completed']}/4 | "
            f"{summary['maximum_primary_rhat']:.4f} | "
            f"{summary['minimum_primary_bulk_ess']:.1f} | "
            f"{summary['maximum_absolute_primary_relative_shift_percent']:.2f}% | "
            f"{summary['all_primary_values_inside_sensitivity_intervals']} |"
        )
    lines.extend(
        [
            "",
            "Complete parameter diagnostics and contrast-level shifts are retained in the profile directories. These analyses do not replace the prespecified primary posterior.",
        ]
    )
    (SENSITIVITY_ROOT / "prior_sensitivity_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not all_passed:
        raise SystemExit(
            "Prior-sensitivity computational gate is on HOLD; evidence was written."
        )
    print(json.dumps(batch, sort_keys=True))


if __name__ == "__main__":
    main()
