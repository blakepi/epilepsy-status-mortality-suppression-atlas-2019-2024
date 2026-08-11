from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"
CONFIG_PATH = OUTPUT_ROOT / "config" / "sr_v2_production.yaml"
PRIMARY_PARAMETERS = [
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
    "svi_quartile_Q2",
    "svi_quartile_Q3",
    "svi_quartile_Q4_highest",
    "z_pct_age65",
    "z_pct_male",
]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def diagnostic_record(row: pd.Series) -> dict[str, object]:
    return {
        "parameter": str(row["parameter"]),
        "r_hat": float(row["r_hat"]),
        "ess_bulk": float(row["ess_bulk"]),
        "ess_tail": float(row["ess_tail"]),
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    thresholds = config["diagnostics"]
    status = pd.read_csv(OUTPUT_ROOT / "chain_status_summary.csv")
    parameters = pd.read_csv(OUTPUT_ROOT / "parameter_diagnostics_all.csv")
    latent = pd.read_csv(OUTPUT_ROOT / "latent_summary_diagnostics.csv")
    latent_draws = pd.read_parquet(OUTPUT_ROOT / "latent_summary_draws.parquet")
    validation = pd.read_csv(OUTPUT_ROOT / "constraint_validation_summary.csv")
    primary = parameters[parameters["parameter"].isin(PRIMARY_PARAMETERS)].copy()

    checks: list[dict[str, object]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    add(
        "eight_completed_chains",
        len(status) == 8 and status["status"].eq("completed").all(),
        f"chains={len(status)} statuses={sorted(status['status'].astype(str).unique())}",
    )
    add(
        "expected_iterations",
        (status["iteration"].astype(int) == 300000).all(),
        f"iterations={sorted(status['iteration'].astype(int).unique().tolist())}",
    )
    add(
        "expected_draws_per_chain",
        (status["saved_draws"].astype(int) == 4500).all(),
        f"draws={sorted(status['saved_draws'].astype(int).unique().tolist())}",
    )
    add(
        "unique_prespecified_seeds",
        sorted(status["seed"].astype(int).tolist()) == list(range(58291, 58299)),
        f"seeds={sorted(status['seed'].astype(int).tolist())}",
    )
    add(
        "grand_total_preserved",
        (status["grand_total"].astype(int) == 58380).all(),
        f"totals={sorted(status['grand_total'].astype(int).unique().tolist())}",
    )
    add(
        "zero_constraint_failures",
        int(validation["failures"].sum()) == 0,
        f"failures={int(validation['failures'].sum())} records={int(validation['records'].sum())}",
    )
    add(
        "complete_parameter_set",
        len(parameters) == int(thresholds["expected_parameters"]),
        f"parameters={len(parameters)} expected={thresholds['expected_parameters']}",
    )
    parameter_finite = np.isfinite(
        parameters[["r_hat", "ess_bulk", "ess_tail", "mcse_mean"]].to_numpy(dtype=float)
    ).all()
    add("parameter_diagnostics_finite", parameter_finite, f"finite={parameter_finite}")
    add(
        "all_parameter_rhat",
        float(parameters["r_hat"].max()) <= float(thresholds["rhat_max_all"]),
        f"maximum={float(parameters['r_hat'].max()):.6f} threshold={thresholds['rhat_max_all']}",
    )
    add(
        "all_parameter_bulk_ess",
        float(parameters["ess_bulk"].min()) >= float(thresholds["ess_bulk_min_all"]),
        f"minimum={float(parameters['ess_bulk'].min()):.1f} threshold={thresholds['ess_bulk_min_all']}",
    )
    add(
        "all_parameter_tail_ess",
        float(parameters["ess_tail"].min()) >= float(thresholds["ess_tail_min_all"]),
        f"minimum={float(parameters['ess_tail'].min()):.1f} threshold={thresholds['ess_tail_min_all']}",
    )
    add(
        "primary_bulk_ess",
        float(primary["ess_bulk"].min()) >= float(thresholds["ess_bulk_min_primary"]),
        f"minimum={float(primary['ess_bulk'].min()):.1f} threshold={thresholds['ess_bulk_min_primary']}",
    )
    add(
        "primary_tail_ess",
        float(primary["ess_tail"].min()) >= float(thresholds["ess_tail_min_primary"]),
        f"minimum={float(primary['ess_tail'].min()):.1f} threshold={thresholds['ess_tail_min_primary']}",
    )

    deterministic = (
        latent_draws.groupby("parameter")["value"].nunique().rename("unique_values").reset_index()
    )
    latent_eval = latent.merge(deterministic, on="parameter", how="left")
    stochastic = latent_eval[latent_eval["unique_values"] > 1].copy()
    deterministic_count = int((latent_eval["unique_values"] <= 1).sum())
    latent_finite = np.isfinite(
        stochastic[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(dtype=float)
    ).all()
    add(
        "latent_summary_diagnostics_finite",
        latent_finite,
        f"stochastic={len(stochastic)} deterministic={deterministic_count} finite={latent_finite}",
    )
    add(
        "latent_summary_rhat",
        not stochastic.empty
        and float(stochastic["r_hat"].max()) <= float(thresholds["latent_summary_rhat_max"]),
        (
            f"maximum={float(stochastic['r_hat'].max()):.6f} "
            f"threshold={thresholds['latent_summary_rhat_max']}"
            if not stochastic.empty
            else "no stochastic latent summaries"
        ),
    )
    add(
        "latent_summary_bulk_ess",
        not stochastic.empty
        and float(stochastic["ess_bulk"].min()) >= float(thresholds["latent_summary_ess_bulk_min"]),
        (
            f"minimum={float(stochastic['ess_bulk'].min()):.1f} "
            f"threshold={thresholds['latent_summary_ess_bulk_min']}"
            if not stochastic.empty
            else "no stochastic latent summaries"
        ),
    )
    add(
        "latent_summary_tail_ess",
        not stochastic.empty
        and float(stochastic["ess_tail"].min()) >= float(thresholds["latent_summary_ess_tail_min"]),
        (
            f"minimum={float(stochastic['ess_tail'].min()):.1f} "
            f"threshold={thresholds['latent_summary_ess_tail_min']}"
            if not stochastic.empty
            else "no stochastic latent summaries"
        ),
    )

    exact = load_json(
        ROOT / "outputs" / "scientific_reports_v2" / "exact_kernel_validation" / "exact_kernel_validation.json"
    )
    random_exact = load_json(
        ROOT / "outputs" / "scientific_reports_v2" / "random_exact_validation" / "random_exact_validation_summary.json"
    )
    geometry = load_json(
        ROOT / "outputs" / "scientific_reports_v2" / "constraint_geometry" / "constraint_geometry.json"
    )
    extended = load_json(
        ROOT / "outputs" / "scientific_reports_v2" / "extended_joint_pilot" / "extended_joint_summary.json"
    )
    calibration_design = load_json(
        ROOT / "outputs" / "scientific_reports_v2" / "calibration_design_smoke" / "calibration_design_summary.json"
    )
    calibration_pilot = load_json(
        ROOT
        / "outputs"
        / "scientific_reports_v2"
        / "calibration_pilot"
        / "replicate_001"
        / "calibration_pilot_summary.json"
    )
    add("exact_kernel_gate", bool(exact.get("pass")), str(exact.get("pass")))
    add(
        "randomized_exact_kernel_gate",
        bool(random_exact.get("pass")),
        str(random_exact.get("pass")),
    )
    geometry_pass = (
        int(geometry.get("latent_variables", -1)) == 9695
        and int(geometry.get("independent_equalities", -1)) == 1256
        and int(geometry.get("equality_nullity", -1)) == 8439
    )
    add(
        "constraint_geometry_recorded",
        geometry_pass,
        (
            f"latent_variables={geometry.get('latent_variables')} "
            f"rank={geometry.get('independent_equalities')} "
            f"nullity={geometry.get('equality_nullity')}"
        ),
    )
    add("extended_pilot_gate", bool(extended.get("pilot_pass")), str(extended.get("pilot_pass")))
    add(
        "calibration_design_gate",
        bool(calibration_design.get("design_pass")),
        str(calibration_design.get("design_pass")),
    )
    add(
        "calibration_computational_gate",
        bool(calibration_pilot.get("computational_gate_pass")),
        str(calibration_pilot.get("computational_gate_pass")),
    )

    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(OUTPUT_ROOT / "production_gate_checks.csv", index=False)
    passed = bool(checks_df["passed"].all())
    worst_parameter = parameters.sort_values("r_hat", ascending=False).iloc[0]
    worst_latent = stochastic.sort_values("r_hat", ascending=False).iloc[0] if not stochastic.empty else None
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "action": "freeze_corrected_results" if passed else "hold_or_extend",
        "checks": checks,
        "worst_parameter": diagnostic_record(worst_parameter),
        "worst_stochastic_latent_summary": diagnostic_record(worst_latent) if worst_latent is not None else None,
        "interpretation_boundary": (
            "Passing this gate freezes corrected computational results. Manuscript submission "
            "still requires multi-replicate calibration and prespecified epidemiologic robustness analyses."
        ),
    }
    (OUTPUT_ROOT / "production_gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 corrected production gate",
        "",
        f"Final status: **{'PASS' if passed else 'HOLD'}**",
        f"Action: `{result['action']}`",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for row in checks:
        lines.append(f"| {row['check']} | {row['passed']} | {row['detail']} |")
    lines.extend(
        [
            "",
            "Passing this gate authorizes freezing the corrected computational results only. It does not by itself authorize Scientific Reports submission.",
        ]
    )
    (OUTPUT_ROOT / "production_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit("Scientific Reports v2 production gate is on HOLD; evidence was written.")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
