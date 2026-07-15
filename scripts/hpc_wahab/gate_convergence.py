from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from common import HPC_OUT, PROJECT_ROOT, write_json, rel


def _metric_ok(
    diag: pd.DataFrame,
    parameter: str,
    rhat_max: float,
    ess_bulk_min: float,
    ess_tail_min: float,
) -> tuple[bool, str]:
    row = diag[diag["parameter"].eq(parameter)]
    if row.empty:
        return False, f"{parameter}: missing diagnostics"
    rhat = float(row.iloc[0]["r_hat"])
    ess_bulk = float(row.iloc[0]["ess_bulk"])
    ess_tail = float(row.iloc[0]["ess_tail"])
    ok = rhat <= rhat_max and ess_bulk >= ess_bulk_min and ess_tail >= ess_tail_min
    return (
        ok,
        f"{parameter}: r_hat={rhat:.6f} <= {rhat_max}, "
        f"ess_bulk={ess_bulk:.1f} >= {ess_bulk_min}, ess_tail={ess_tail:.1f} >= {ess_tail_min}",
    )


def _group_ok(
    diag: pd.DataFrame,
    prefix: str,
    rhat_max: float,
    ess_bulk_min: float,
    ess_tail_min: float,
) -> list[tuple[bool, str]]:
    params = sorted(diag.loc[diag["parameter"].str.startswith(prefix), "parameter"].unique())
    if not params:
        return [(False, f"{prefix}*: missing diagnostics")]
    return [
        _metric_ok(diag, parameter, rhat_max, ess_bulk_min, ess_tail_min)
        for parameter in params
    ]


def gate(config_path: Path, hpc_out: Path = HPC_OUT) -> dict:
    hpc_out.mkdir(parents=True, exist_ok=True)
    diagnostics_path = hpc_out / "hpc_mcmc_diagnostics.csv"
    validation_path = hpc_out / "hpc_constraint_validation_summary.csv"
    status_path = hpc_out / "chain_status_summary.csv"
    failures = []
    checks = []
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {"run": {}}
    diagnostic_config = config.get("diagnostics", {})
    rhat_max = float(diagnostic_config.get("rhat_max", 1.01))
    ess_bulk_min = float(diagnostic_config.get("ess_bulk_min", 400))
    ess_tail_min = float(diagnostic_config.get("ess_tail_min", 400))
    expected_parameters = int(diagnostic_config.get("expected_parameters", 69))
    expected_chains = int(config.get("run", {}).get("n_chains", 8))
    expected_seeds = [int(seed) for seed in config.get("run", {}).get("random_seeds", [])]

    if diagnostics_path.exists():
        diag = pd.read_csv(diagnostics_path)
        required_columns = {"parameter", "r_hat", "ess_bulk", "ess_tail", "chains", "draws_per_chain"}
        missing_columns = sorted(required_columns - set(diag.columns))
        modern_columns_ok = not missing_columns
        detail = "all required modern diagnostic columns present" if modern_columns_ok else f"missing columns: {missing_columns}"
        checks.append({"check": "modern_diagnostics_schema", "passed": modern_columns_ok, "detail": detail})
        if not modern_columns_ok:
            failures.append(detail)
        parameter_count_ok = diag["parameter"].nunique() == expected_parameters
        detail = f"{diag['parameter'].nunique()} parameters; expected {expected_parameters}"
        checks.append({"check": "complete_parameter_set", "passed": parameter_count_ok, "detail": detail})
        if not parameter_count_ok:
            failures.append(detail)
        if modern_columns_ok:
            finite = diag[["r_hat", "ess_bulk", "ess_tail"]].apply(pd.to_numeric, errors="coerce").notna().all().all()
            checks.append({"check": "diagnostics_are_finite", "passed": bool(finite), "detail": "R-hat and ESS columns"})
            if not finite:
                failures.append("one or more convergence diagnostics are non-finite")
            for _, diagnostic_row in diag.sort_values("parameter").iterrows():
                parameter = str(diagnostic_row["parameter"])
                ok, metric_detail = _metric_ok(diag, parameter, rhat_max, ess_bulk_min, ess_tail_min)
                checks.append({"check": f"parameter_{parameter}", "passed": ok, "detail": metric_detail})
                if not ok:
                    failures.append(metric_detail)
            for prefix in ["primary_rurality_", "svi_quartile_", "state_effect[", "year_effect["]:
                prefix_ok = bool(diag["parameter"].astype(str).str.startswith(prefix, na=False).any())
                prefix_detail = f"required parameter family {prefix}* present"
                checks.append({"check": f"parameter_family_{prefix}", "passed": prefix_ok, "detail": prefix_detail})
                if not prefix_ok:
                    failures.append(prefix_detail)
    else:
        failures.append("missing hpc_mcmc_diagnostics.csv")
        checks.append({"check": "diagnostics_file_exists", "passed": False, "detail": str(diagnostics_path)})

    if validation_path.exists():
        validation = pd.read_csv(validation_path)
        if "passed" in validation:
            passed = validation["passed"].astype(str).str.lower().isin(["true", "1"]).all()
            detail = f"{len(validation)} validation rows"
        elif {"validation_records", "failed_records"}.issubset(validation.columns):
            passed = pd.to_numeric(validation["failed_records"], errors="coerce").eq(0).all()
            detail = f"{int(validation['validation_records'].sum())} validation records summarized in {len(validation)} chain-check rows"
        else:
            passed = False
            detail = "validation schema is missing passed or failed_records columns"
        checks.append({"check": "all_saved_latent_draw_validations_passed", "passed": bool(passed), "detail": detail})
        if not passed:
            failures.append("one or more latent draw constraint validations failed")
    else:
        failures.append("missing hpc_constraint_validation_summary.csv")
        checks.append({"check": "latent_validation_file_exists", "passed": False, "detail": str(validation_path)})

    if status_path.exists():
        status = pd.read_csv(status_path)
        exact_chain_count = len(status) == expected_chains
        checks.append({"check": "expected_chain_count", "passed": exact_chain_count, "detail": f"{len(status)} chains; expected {expected_chains}"})
        if not exact_chain_count:
            failures.append(f"found {len(status)} chain statuses; expected {expected_chains}")
        statuses = status.get("status", pd.Series(dtype=str)).astype(str)
        completed = statuses.eq("completed").all() and len(status) > 0
        checks.append({"check": "no_chain_status_failure", "passed": bool(completed), "detail": ",".join(sorted(statuses.unique()))})
        if not completed:
            failures.append("one or more chain_status.json files are missing or not completed")
        if "grand_total" in status:
            grand_ok = status["grand_total"].astype(int).eq(58380).all()
            checks.append({"check": "grand_total_remains_58380", "passed": bool(grand_ok), "detail": str(status["grand_total"].tolist())})
            if not grand_ok:
                failures.append("grand total differs from 58,380 in one or more chains")
        if "suppressed_cells_treated_as_zero" in status:
            supp_ok = ~status["suppressed_cells_treated_as_zero"].astype(str).str.lower().isin(["true", "1"]).any()
            checks.append({"check": "no_suppressed_cells_treated_as_zero", "passed": bool(supp_ok), "detail": ""})
            if not supp_ok:
                failures.append("a chain reported suppressed cells treated as zero")
        if {"iteration", "target_iteration"}.issubset(status.columns):
            iteration_ok = status["iteration"].astype(int).eq(status["target_iteration"].astype(int)).all()
            checks.append({"check": "all_chains_reached_target_iteration", "passed": bool(iteration_ok), "detail": "iteration equals target_iteration"})
            if not iteration_ok:
                failures.append("one or more chains did not reach the target iteration")
        expected_saved = None
        run_config = config.get("run", {})
        if all(key in run_config for key in ["n_iter", "burn_in", "thin"]):
            expected_saved = (int(run_config["n_iter"]) - int(run_config["burn_in"])) // int(run_config["thin"])
        if expected_saved is not None and "saved_draws" in status:
            saved_ok = status["saved_draws"].astype(int).eq(expected_saved).all()
            checks.append({"check": "expected_saved_draws", "passed": bool(saved_ok), "detail": f"expected {expected_saved} per chain"})
            if not saved_ok:
                failures.append(f"one or more chains do not contain {expected_saved} saved draws")
        seed_column = "seed" if "seed" in status.columns else "random_seed" if "random_seed" in status.columns else None
        if expected_seeds:
            actual_seeds = sorted(status[seed_column].astype(int).tolist()) if seed_column else []
            seeds_ok = actual_seeds == sorted(expected_seeds)
            checks.append({"check": "expected_unique_seeds", "passed": seeds_ok, "detail": str(actual_seeds)})
            if not seeds_ok:
                failures.append("chain seeds do not match the production configuration")
        if "mode" in status:
            mode_ok = status["mode"].astype(str).eq("production").all()
            checks.append({"check": "production_mode_only", "passed": bool(mode_ok), "detail": ",".join(sorted(status["mode"].astype(str).unique()))})
            if not mode_ok:
                failures.append("one or more chains are not production-mode outputs")
    else:
        failures.append("missing chain_status_summary.csv")
        checks.append({"check": "chain_status_summary_exists", "passed": False, "detail": str(status_path)})

    max_extensions = int(config.get("run", {}).get("max_extensions", 4))
    round_path = hpc_out / "extension_round.txt"
    extension_round = int(round_path.read_text(encoding="utf-8").strip()) if round_path.exists() and round_path.read_text(encoding="utf-8").strip() else 0
    passed = not failures
    if passed:
        action = "finalize"
    elif extension_round < max_extensions:
        action = "extend"
    else:
        action = "stop_nonfinal"
    worst = []
    if diagnostics_path.exists():
        diag = pd.read_csv(diagnostics_path)
        diag["rhat_rank"] = pd.to_numeric(diag["r_hat"], errors="coerce")
        diag["ess_bulk_rank"] = pd.to_numeric(diag.get("ess_bulk"), errors="coerce")
        diag["ess_tail_rank"] = pd.to_numeric(diag.get("ess_tail"), errors="coerce")
        columns = [column for column in ["parameter", "r_hat", "ess_bulk", "ess_tail"] if column in diag]
        worst = diag.sort_values(["rhat_rank", "ess_bulk_rank", "ess_tail_rank"], ascending=[False, True, True]).head(10)[columns].to_dict("records")
    return {
        "passed": passed,
        "action": action,
        "extension_round": extension_round,
        "max_extensions": max_extensions,
        "recommended_extension_n_iter": int(config.get("run", {}).get("extension_n_iter", 150000)),
        "thresholds": {
            "rhat_max": rhat_max,
            "ess_bulk_min": ess_bulk_min,
            "ess_tail_min": ess_tail_min,
            "expected_parameters": expected_parameters,
        },
        "failures": failures,
        "checks": checks,
        "worst_parameters": worst,
    }


def write_markdown(result: dict, path: Path) -> None:
    lines = [
        "# Wahab Convergence Gate",
        "",
        f"Passed: `{result['passed']}`",
        f"Action: `{result['action']}`",
        f"Extension round: `{result['extension_round']}` of `{result['max_extensions']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in result["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['check']} | {check['passed']} | {detail} |")
    lines.extend(["", "## Failures", ""])
    if result["failures"]:
        lines.extend([f"- {failure}" for failure in result["failures"]])
    else:
        lines.append("- None")
    lines.extend(["", "## Worst Parameters", ""])
    for row in result["worst_parameters"]:
        lines.append(
            f"- {row['parameter']}: R-hat={row.get('r_hat')}, "
            f"bulk ESS={row.get('ess_bulk')}, tail ESS={row.get('ess_tail')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="hpc/wahab/configs/bayes_constrained_hpc_production.yaml")
    parser.add_argument("--fail-on-stop-nonfinal", action="store_true")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    result = gate(config_path)
    write_json(HPC_OUT / "convergence_gate.json", result)
    write_markdown(result, HPC_OUT / "convergence_gate.md")
    print(f"convergence_gate={rel(HPC_OUT / 'convergence_gate.json')}")
    print(f"action={result['action']}")
    if args.fail_on_stop_nonfinal and result["action"] == "stop_nonfinal":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
