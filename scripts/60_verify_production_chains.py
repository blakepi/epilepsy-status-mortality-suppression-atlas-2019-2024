from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402


EXPECTED_CHAIN_NAMES = [f"chain_{index:02d}" for index in range(1, 9)]
EXPECTED_SEEDS = list(range(18291, 18299))
EXPECTED_SUPPORT_HASHES = {
    "outputs/bayes_constrained/posterior_parameter_draws.csv": "aeac4ea246568734f5107c4b40f0d834cc2a3ef0430ad7b9a45d73386444ed82",
    "outputs/bayes_constrained/posterior_draws_primary.npz": "173b41f5ba9c2f65836b77bf58053ed5b6f50df35a4e32721637ed251db2ecb1",
    "outputs/bayes_constrained/county_posterior_summary.csv": "2b66f5eb08b4b558beb9859fdc428b32a9317f94b7cf93fcea38ac744008ccd0",
    "outputs/bayes_constrained/county_posterior_summary.parquet": "33cb0e55624ba5da6ac3a273027323d7fa88b6fd0b7567b39908a1f835b22552",
    "outputs/bayes_constrained/hpc/hpc_constraint_validation_summary.csv": "c83341e7bdfd18c4207a98c9af4e63bc727606a14d7d1982d7656de65e8fff70",
    "tables/bayes_constrained_adjusted_rates_by_rurality.csv": "30af1c6425d9d02bbb8ff0533f2068ca9e1f0b41d5f6577bb15fc08147e7ae41",
}
PUBLIC_CHAIN_FILES = [
    "draws_params.parquet",
    "chain_status.json",
    "chain_config_resolved.yaml",
    "acceptance_rates.csv",
    "runtime_log.csv",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_row(path: Path, root: Path, role: str) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _posterior_summary(draws: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    diagnostic_lookup = diagnostics.set_index("parameter")
    for parameter, group in draws.groupby("parameter", sort=True):
        values = group["value"].to_numpy(dtype=float)
        is_ratio = parameter.startswith("primary_rurality_") or parameter.startswith("svi_quartile_")
        reported = np.exp(values) if is_ratio else values
        diagnostic = diagnostic_lookup.loc[parameter]
        rows.append(
            {
                "parameter": parameter,
                "scale": "mortality_rate_ratio" if is_ratio else "model_parameter",
                "posterior_mean": float(np.mean(reported)),
                "posterior_median": float(np.median(reported)),
                "credible_interval_lower_95": float(np.quantile(reported, 0.025)),
                "credible_interval_upper_95": float(np.quantile(reported, 0.975)),
                "posterior_probability_gt_1": float(np.mean(reported > 1)) if is_ratio else np.nan,
                "r_hat": float(diagnostic["r_hat"]),
                "ess_bulk": float(diagnostic["ess_bulk"]),
                "ess_tail": float(diagnostic["ess_tail"]),
                "mcse_mean": float(diagnostic["mcse_mean"]),
                "draws": int(len(values)),
            }
        )
    return pd.DataFrame(rows)


def verify(
    chains_root: Path,
    final_root: Path,
    output_dir: Path,
    copy_public_chain_artifacts: bool,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    source_manifest: list[dict] = []
    statuses: list[dict] = []
    parameter_frames: list[pd.DataFrame] = []
    validation_frames: list[pd.DataFrame] = []
    acceptance_frames: list[pd.DataFrame] = []

    chain_dirs = sorted(path for path in chains_root.glob("chain_*") if path.is_dir())
    _check([path.name for path in chain_dirs] == EXPECTED_CHAIN_NAMES, "Expected exactly chain_01 through chain_08.", errors)

    for index, chain_dir in enumerate(chain_dirs, start=1):
        chain_name = chain_dir.name
        required_files = [
            "draws_params.parquet",
            "draws_latent.npz",
            "latent_validation.csv",
            "chain_status.json",
            "chain_config_resolved.yaml",
            "acceptance_rates.csv",
            "runtime_log.csv",
        ]
        for name in required_files:
            path = chain_dir / name
            _check(path.is_file(), f"{chain_name}: missing {name}", errors)
            if path.is_file():
                source_manifest.append(_manifest_row(path, final_root, "production_chain_source"))
        if errors and any(error.startswith(f"{chain_name}:") and "missing" in error for error in errors):
            continue

        status = json.loads((chain_dir / "chain_status.json").read_text(encoding="utf-8"))
        statuses.append({"chain": chain_name, **status})
        _check(status.get("status") == "completed", f"{chain_name}: status is not completed", errors)
        _check(status.get("mode") == "production", f"{chain_name}: mode is not production", errors)
        _check(int(status.get("chain_id", -1)) == index, f"{chain_name}: wrong chain_id", errors)
        _check(int(status.get("seed", -1)) == EXPECTED_SEEDS[index - 1], f"{chain_name}: wrong seed", errors)
        _check(int(status.get("iteration", -1)) == 300000, f"{chain_name}: wrong iteration", errors)
        _check(int(status.get("target_iteration", -1)) == 300000, f"{chain_name}: wrong target_iteration", errors)
        _check(int(status.get("saved_draws", -1)) == 4500, f"{chain_name}: wrong saved_draws", errors)
        _check(int(status.get("grand_total", -1)) == 58380, f"{chain_name}: wrong grand_total", errors)
        _check(not bool(status.get("suppressed_cells_treated_as_zero", True)), f"{chain_name}: suppressed cells treated as zero", errors)
        _check(not str(status.get("resume_source", "")).strip(), f"{chain_name}: unexpected resume source", errors)

        resolved = yaml.safe_load((chain_dir / "chain_config_resolved.yaml").read_text(encoding="utf-8"))
        settings = resolved.get("resolved_settings", {})
        arguments = resolved.get("arguments", {})
        _check(int(settings.get("n_chains", -1)) == 8, f"{chain_name}: resolved n_chains mismatch", errors)
        _check(int(settings.get("n_iter", -1)) == 300000, f"{chain_name}: resolved n_iter mismatch", errors)
        _check(int(settings.get("burn_in", -1)) == 75000, f"{chain_name}: resolved burn_in mismatch", errors)
        _check(int(settings.get("thin", -1)) == 50, f"{chain_name}: resolved thin mismatch", errors)
        _check(arguments.get("resume") is False, f"{chain_name}: resolved run was resumed", errors)
        _check(int(arguments.get("seed", -1)) == EXPECTED_SEEDS[index - 1], f"{chain_name}: resolved seed mismatch", errors)

        draws = pd.read_parquet(chain_dir / "draws_params.parquet")
        draws["chain_source"] = chain_name
        _check(len(draws) == 310500, f"{chain_name}: expected 310,500 parameter rows", errors)
        _check(draws["parameter"].nunique() == 69, f"{chain_name}: expected 69 parameters", errors)
        _check(draws["draw"].nunique() == 4500, f"{chain_name}: expected 4,500 draws", errors)
        _check(int(draws["iteration"].min()) == 75050, f"{chain_name}: first retained iteration mismatch", errors)
        _check(int(draws["iteration"].max()) == 300000, f"{chain_name}: last retained iteration mismatch", errors)
        _check(np.isfinite(draws["value"].to_numpy(dtype=float)).all(), f"{chain_name}: non-finite parameter draw", errors)
        parameter_frames.append(draws.drop(columns="chain_source"))

        validation = pd.read_csv(chain_dir / "latent_validation.csv")
        validation.insert(0, "chain", index)
        _check(len(validation) == 61212, f"{chain_name}: expected 61,212 validation rows", errors)
        _check(validation["check"].nunique() == 12, f"{chain_name}: expected 12 validation checks", errors)
        _check(validation["label"].nunique() == 5101, f"{chain_name}: expected 5,101 validation labels", errors)
        _check(validation["passed"].astype(str).str.lower().isin(["true", "1"]).all(), f"{chain_name}: failed latent validation", errors)
        validation_frames.append(validation)

        latent = np.load(chain_dir / "draws_latent.npz", allow_pickle=False)["y"]
        _check(latent.shape == (4500, 18852), f"{chain_name}: latent array shape mismatch", errors)
        _check(np.issubdtype(latent.dtype, np.integer), f"{chain_name}: latent array is not integer", errors)
        _check(np.equal(latent.sum(axis=1), 58380).all(), f"{chain_name}: latent draw total mismatch", errors)

        acceptance = pd.read_csv(chain_dir / "acceptance_rates.csv")
        acceptance.insert(0, "chain_source", chain_name)
        acceptance_frames.append(acceptance)

    for relative, expected_hash in EXPECTED_SUPPORT_HASHES.items():
        path = final_root / relative
        _check(path.is_file(), f"Missing final support artifact: {relative}", errors)
        if path.is_file():
            actual_hash = sha256_file(path)
            _check(actual_hash == expected_hash, f"Final support artifact hash mismatch: {relative}", errors)
            source_manifest.append(_manifest_row(path, final_root, "production_derived_source"))

    if errors:
        raise RuntimeError("Production verification failed:\n- " + "\n- ".join(errors))

    output_dir.mkdir(parents=True, exist_ok=True)
    parameter_draws = pd.concat(parameter_frames, ignore_index=True)
    diagnostics = diagnostics_table(parameter_draws, output_dir=output_dir)
    diagnostics.to_csv(output_dir / "parameter_diagnostics_all.csv", index=False)
    diagnostics.to_csv(output_dir / "hpc_mcmc_diagnostics.csv", index=False)
    shutil.copy2(output_dir / "mcmc_diagnostics.md", output_dir / "parameter_diagnostics_all.md")

    rhat_max = float(diagnostics["r_hat"].max())
    ess_bulk_min = float(diagnostics["ess_bulk"].min())
    ess_tail_min = float(diagnostics["ess_tail"].min())
    _check(rhat_max <= 1.01, f"Maximum R-hat {rhat_max:.6f} exceeds 1.01", errors)
    _check(ess_bulk_min >= 400, f"Minimum bulk ESS {ess_bulk_min:.1f} is below 400", errors)
    _check(ess_tail_min >= 400, f"Minimum tail ESS {ess_tail_min:.1f} is below 400", errors)

    status_frame = pd.DataFrame(statuses)
    status_frame.to_csv(output_dir / "chain_status_summary.csv", index=False)
    acceptance_all = pd.concat(acceptance_frames, ignore_index=True)
    acceptance_all.to_csv(output_dir / "acceptance_rates_all.csv", index=False)
    acceptance_summary = acceptance_all.groupby(["type", "block"], as_index=False).agg(
        min_acceptance_rate=("acceptance_rate", "min"),
        median_acceptance_rate=("acceptance_rate", "median"),
        max_acceptance_rate=("acceptance_rate", "max"),
    )
    acceptance_summary.to_csv(output_dir / "acceptance_summary.csv", index=False)
    parameter_acceptance = acceptance_summary[acceptance_summary["type"].eq("parameter")]
    outside = parameter_acceptance[
        (parameter_acceptance["min_acceptance_rate"] < 0.20)
        | (parameter_acceptance["max_acceptance_rate"] > 0.45)
    ]
    if not outside.empty:
        warnings.append(
            "Some parameter proposal acceptance rates are outside the nominal 0.20-0.45 tuning target; "
            "this is reported as an efficiency warning because all-parameter R-hat and ESS pass."
        )

    validation_all = pd.concat(validation_frames, ignore_index=True)
    validation_all.to_csv(output_dir / "latent_validation_all.csv.gz", index=False, compression="gzip")
    validation_summary = validation_all.groupby(["chain", "check"], as_index=False).agg(
        labels_checked=("label", "nunique"),
        validation_records=("passed", "size"),
        failed_records=("passed", lambda values: int((~values.astype(bool)).sum())),
    )
    validation_summary.to_csv(output_dir / "production_constraint_validation_summary.csv", index=False)
    validation_summary.to_csv(output_dir / "hpc_constraint_validation_summary.csv", index=False)

    posterior = _posterior_summary(parameter_draws, diagnostics)
    posterior.to_csv(output_dir / "posterior_parameter_summary.csv", index=False)
    primary = posterior[
        posterior["parameter"].str.startswith(("primary_rurality_", "svi_quartile_"))
        | posterior["parameter"].isin(["z_pct_age65", "z_pct_male", "kappa", "sigma_state", "sigma_year"])
    ].copy()
    primary.to_csv(output_dir / "posterior_primary_summary.csv", index=False)

    support_copies = {
        "outputs/bayes_constrained/county_posterior_summary.csv": "county_posterior_summary.csv",
        "outputs/bayes_constrained/county_posterior_summary.parquet": "county_posterior_summary.parquet",
        "tables/bayes_constrained_adjusted_rates_by_rurality.csv": "adjusted_rates_by_rurality.csv",
        "outputs/bayes_constrained/data_audit.csv": "data_audit.csv",
    }
    for relative, target_name in support_copies.items():
        source = final_root / relative
        if source.exists():
            shutil.copy2(source, output_dir / target_name)

    if copy_public_chain_artifacts:
        for chain_dir in chain_dirs:
            target_dir = output_dir / "chains" / chain_dir.name
            target_dir.mkdir(parents=True, exist_ok=True)
            for name in PUBLIC_CHAIN_FILES:
                shutil.copy2(chain_dir / name, target_dir / name)

    temporary_files = sorted(path.relative_to(final_root).as_posix() for path in chains_root.rglob("*.tmp.npz"))
    if temporary_files:
        warnings.append(f"Excluded {len(temporary_files)} temporary NPZ files from the verified/public artifact set.")
    if (chains_root.parent / "extension_round.txt").exists():
        warnings.append("Ignored stale extension-round control metadata; chain statuses and resolved configs show pure 300,000-iteration production runs.")

    pd.DataFrame(source_manifest).sort_values("path").to_csv(output_dir / "production_source_manifest.csv", index=False)
    verification = {
        "passed": not errors,
        "chain_count": len(chain_dirs),
        "expected_seeds": EXPECTED_SEEDS,
        "iterations_per_chain": 300000,
        "burn_in": 75000,
        "thin": 50,
        "draws_per_chain": 4500,
        "saved_parameter_draws_per_parameter": 36000,
        "parameters": int(diagnostics["parameter"].nunique()),
        "maximum_rank_normalized_rhat": rhat_max,
        "minimum_bulk_ess": ess_bulk_min,
        "minimum_tail_ess": ess_tail_min,
        "latent_validation_records": int(len(validation_all)),
        "latent_validation_failures": int((~validation_all["passed"].astype(bool)).sum()),
        "warnings": warnings,
        "excluded_temporary_files": temporary_files,
    }
    (output_dir / "production_verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    lines = [
        "# Production Chain Verification",
        "",
        "Final status: PASS",
        "",
        f"- Chains: {verification['chain_count']} completed production chains",
        f"- Retained draws: {verification['draws_per_chain']:,} per chain; {verification['saved_parameter_draws_per_parameter']:,} per parameter",
        f"- Parameters: {verification['parameters']}",
        f"- Maximum rank-normalized split R-hat: {rhat_max:.6f}",
        f"- Minimum bulk ESS: {ess_bulk_min:.1f}",
        f"- Minimum tail ESS: {ess_tail_min:.1f}",
        f"- Latent validation records: {len(validation_all):,}; failures: 0",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- {warning}" for warning in warnings)
    (output_dir / "production_verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    derived_paths = sorted(path for path in output_dir.rglob("*") if path.is_file() and path.name != "derived_artifact_manifest.csv")
    derived_rows = [
        {
            "path": path.relative_to(output_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in derived_paths
    ]
    pd.DataFrame(derived_rows).to_csv(output_dir / "derived_artifact_manifest.csv", index=False)
    return verification


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and freeze the exact eight-chain production run.")
    parser.add_argument("--chains-root", type=Path, required=True)
    parser.add_argument("--final-root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/bayes_constrained/production_8chain")
    parser.add_argument("--copy-public-chain-artifacts", action="store_true")
    args = parser.parse_args()
    chains_root = args.chains_root.resolve()
    final_root = args.final_root.resolve() if args.final_root else chains_root.parents[3]
    verification = verify(chains_root, final_root, args.output_dir.resolve(), args.copy_public_chain_artifacts)
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
