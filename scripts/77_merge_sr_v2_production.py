from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import GRAND_TOTAL, RURAL_ORDER, SVI_ORDER, load_model_frame  # noqa: E402
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402
from bayes_constrained.model import PRIMARY_TERMS, term_to_label  # noqa: E402


OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_representative_interval_counties(frame: pd.DataFrame, per_rurality: int = 6) -> list[str]:
    county = frame.drop_duplicates("county_fips").copy()
    county = county[county["q001_period_status"].eq("suppressed_1_9")]
    selected: list[str] = []
    for rurality in RURAL_ORDER:
        group = county[county["primary_rurality"].eq(rurality)].sort_values("county_fips")
        if group.empty:
            continue
        n = min(per_rurality, len(group))
        positions = np.unique(np.rint(np.linspace(0, len(group) - 1, n)).astype(int))
        selected.extend(group.iloc[positions]["county_fips"].astype(str).tolist())
    return selected


def posterior_parameter_summary(draws: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    diag = diagnostics.set_index("parameter")
    rows: list[dict[str, object]] = []
    for parameter in sorted(draws["parameter"].astype(str).unique()):
        values = draws.loc[draws["parameter"].eq(parameter), "value"].to_numpy(dtype=float)
        is_irr = parameter.startswith("primary_rurality_") or parameter.startswith("svi_quartile_")
        reported = np.exp(values) if is_irr else values
        lower, median, upper = np.quantile(reported, [0.025, 0.5, 0.975])
        diagnostic = diag.loc[parameter]
        rows.append(
            {
                "parameter": parameter,
                "label": term_to_label(parameter),
                "scale": "IRR" if is_irr else "model_parameter",
                "posterior_mean": float(reported.mean()),
                "posterior_median": float(median),
                "credible_interval_lower_95": float(lower),
                "credible_interval_upper_95": float(upper),
                "posterior_probability_gt_1": float((reported > 1.0).mean()) if is_irr else np.nan,
                "r_hat": float(diagnostic["r_hat"]),
                "ess_bulk": float(diagnostic["ess_bulk"]),
                "ess_tail": float(diagnostic["ess_tail"]),
                "mcse_mean": float(diagnostic["mcse_mean"]),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    chain_dirs = sorted((OUTPUT_ROOT / "chains").glob("chain_*"))
    if len(chain_dirs) != 8:
        raise SystemExit(f"Expected eight production chains; found {len(chain_dirs)}.")

    frame = load_model_frame()
    county_order = frame.drop_duplicates("county_fips")["county_fips"].astype(str).tolist()
    county_codes = frame["county_fips"].astype(str).to_numpy()
    expected_codes = np.repeat(np.asarray(county_order, dtype=object), frame["year"].astype(str).nunique())
    if not np.array_equal(county_codes, expected_codes):
        raise SystemExit("Model-frame county-year ordering is not contiguous; cannot reshape safely.")
    years_per_county = frame["year"].astype(str).nunique()
    representative_counties = select_representative_interval_counties(frame)
    representative_index = {county: county_order.index(county) for county in representative_counties}

    parameter_frames: list[pd.DataFrame] = []
    acceptance_frames: list[pd.DataFrame] = []
    validation_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, object]] = []
    latent_summary_frames: list[pd.DataFrame] = []
    county_draw_blocks: list[np.ndarray] = []
    source_files: list[dict[str, object]] = []

    category_masks: dict[str, np.ndarray] = {}
    for rurality in RURAL_ORDER:
        category_masks[f"latent_rurality_total[{rurality}]"] = frame["primary_rurality"].eq(rurality).to_numpy()
    for svi in SVI_ORDER:
        category_masks[f"latent_svi_total[{svi}]"] = frame["svi_quartile"].eq(svi).to_numpy()

    for chain_dir in chain_dirs:
        chain = int(chain_dir.name.split("_")[-1])
        status_path = chain_dir / "chain_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status_rows.append({"chain": chain, **status})
        paths = {
            "draws_params": chain_dir / "draws_params.parquet",
            "draws_latent": chain_dir / "draws_latent.npz",
            "acceptance_rates": chain_dir / "acceptance_rates.csv",
            "latent_validation": chain_dir / "latent_validation.csv",
            "resolved_config": chain_dir / "chain_config_resolved.yaml",
            "status": status_path,
        }
        for label, path in paths.items():
            if not path.exists():
                raise FileNotFoundError(f"Missing chain {chain} artifact {label}: {path}")
            source_files.append(
                {
                    "chain": chain,
                    "artifact": label,
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": int(path.stat().st_size),
                    "sha256": sha256(path),
                }
            )
        parameter_frames.append(pd.read_parquet(paths["draws_params"]))
        acceptance_frames.append(pd.read_csv(paths["acceptance_rates"]))
        validation = pd.read_csv(paths["latent_validation"])
        validation["chain"] = chain
        validation_frames.append(validation)

        latent = np.load(paths["draws_latent"], allow_pickle=True)["y"].astype(np.int32)
        if latent.shape != (4500, len(frame)):
            raise SystemExit(
                f"Chain {chain} latent shape is {latent.shape}; expected {(4500, len(frame))}."
            )
        draw_number = np.arange(1, latent.shape[0] + 1, dtype=int)
        summary_columns: dict[str, np.ndarray] = {}
        for parameter, mask in category_masks.items():
            summary_columns[parameter] = latent[:, mask].sum(axis=1)
        county_sums = latent.reshape(latent.shape[0], len(county_order), years_per_county).sum(axis=2)
        county_draw_blocks.append(county_sums.astype(np.int32))
        for county, index in representative_index.items():
            summary_columns[f"latent_county_period[{county}]"] = county_sums[:, index]
        latent_summary_frames.extend(
            pd.DataFrame(
                {
                    "chain": chain,
                    "draw": draw_number,
                    "parameter": parameter,
                    "value": values,
                }
            )
            for parameter, values in summary_columns.items()
        )

    status_df = pd.DataFrame(status_rows).sort_values("chain")
    if not status_df["status"].eq("completed").all():
        incomplete = status_df.loc[~status_df["status"].eq("completed"), ["chain", "status"]]
        raise SystemExit(f"Production chains are incomplete:\n{incomplete.to_string(index=False)}")
    if not (status_df["saved_draws"].astype(int) == 4500).all():
        raise SystemExit("Not every chain has exactly 4,500 retained draws.")

    parameter_draws = pd.concat(parameter_frames, ignore_index=True)
    parameter_draws.to_parquet(OUTPUT_ROOT / "posterior_parameter_draws.parquet", index=False)
    parameter_diagnostics = diagnostics_table(parameter_draws, output_dir=None)
    parameter_diagnostics.to_csv(OUTPUT_ROOT / "parameter_diagnostics_all.csv", index=False)
    parameter_summary = posterior_parameter_summary(parameter_draws, parameter_diagnostics)
    parameter_summary.to_csv(OUTPUT_ROOT / "posterior_parameter_summary.csv", index=False)
    parameter_summary[
        parameter_summary["parameter"].isin(PRIMARY_TERMS)
    ].to_csv(OUTPUT_ROOT / "posterior_primary_summary.csv", index=False)

    acceptance = pd.concat(acceptance_frames, ignore_index=True)
    acceptance.to_csv(OUTPUT_ROOT / "acceptance_rates_all.csv", index=False)
    acceptance_summary = (
        acceptance.groupby(["type", "block"])["acceptance_rate"]
        .agg(["min", "median", "max"])
        .reset_index()
    )
    acceptance_summary.to_csv(OUTPUT_ROOT / "acceptance_summary.csv", index=False)

    validation = pd.concat(validation_frames, ignore_index=True)
    validation.to_csv(OUTPUT_ROOT / "latent_validation_all.csv.gz", index=False, compression="gzip")
    validation_summary = (
        validation.groupby(["chain", "check"], as_index=False)
        .agg(records=("passed", "size"), failures=("passed", lambda values: int((~values.astype(bool)).sum())))
    )
    validation_summary.to_csv(OUTPUT_ROOT / "constraint_validation_summary.csv", index=False)
    status_df.to_csv(OUTPUT_ROOT / "chain_status_summary.csv", index=False)

    latent_summary_draws = pd.concat(latent_summary_frames, ignore_index=True)
    latent_summary_draws.to_parquet(OUTPUT_ROOT / "latent_summary_draws.parquet", index=False)
    latent_diagnostics = diagnostics_table(latent_summary_draws, output_dir=None)
    latent_diagnostics.to_csv(OUTPUT_ROOT / "latent_summary_diagnostics.csv", index=False)

    county_draws = np.concatenate(county_draw_blocks, axis=0)
    exposure = frame.groupby("county_fips", sort=False)["population"].sum().loc[county_order].to_numpy(dtype=float)
    rates = county_draws / exposure[None, :] * 100000.0
    national_rate = GRAND_TOTAL / float(frame["population"].sum()) * 100000.0
    base = frame.drop_duplicates("county_fips").set_index("county_fips").loc[county_order].reset_index()
    county_summary = base[["county_fips", "county_name", "state_fips", "state_name", "primary_rurality", "svi_quartile", "q001_period_status"]].copy()
    county_summary["posterior_mean_county_period_deaths"] = county_draws.mean(axis=0)
    county_summary["posterior_median_county_period_deaths"] = np.quantile(county_draws, 0.5, axis=0)
    county_summary["deaths_credible_interval_lower_95"] = np.quantile(county_draws, 0.025, axis=0)
    county_summary["deaths_credible_interval_upper_95"] = np.quantile(county_draws, 0.975, axis=0)
    county_summary["posterior_mean_rate_per_100k"] = rates.mean(axis=0)
    county_summary["posterior_median_rate_per_100k"] = np.quantile(rates, 0.5, axis=0)
    county_summary["rate_credible_interval_lower_95"] = np.quantile(rates, 0.025, axis=0)
    county_summary["rate_credible_interval_upper_95"] = np.quantile(rates, 0.975, axis=0)
    county_summary["posterior_probability_rate_exceeds_national_rate"] = (rates > national_rate).mean(axis=0)
    county_summary["posterior_quantity_note"] = (
        "Corrected constrained Bayesian posterior summary; not an observed or recovered suppressed count."
    )
    county_summary.to_csv(OUTPUT_ROOT / "county_posterior_summary.csv", index=False)
    county_summary.to_parquet(OUTPUT_ROOT / "county_posterior_summary.parquet", index=False)

    source_manifest = pd.DataFrame(source_files)
    source_manifest.to_csv(OUTPUT_ROOT / "production_source_manifest.csv", index=False)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "chains": 8,
        "draws_per_chain": 4500,
        "parameter_draws": int(parameter_draws[["chain", "draw"]].drop_duplicates().shape[0]),
        "parameters": int(parameter_draws["parameter"].nunique()),
        "latent_validation_records": int(len(validation)),
        "latent_validation_failures": int((~validation["passed"].astype(bool)).sum()),
        "latent_summary_parameters": int(latent_summary_draws["parameter"].nunique()),
        "representative_interval_counties": representative_counties,
        "county_summaries": int(len(county_summary)),
        "status": "merged_not_yet_gated",
    }
    (OUTPUT_ROOT / "production_merge_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
