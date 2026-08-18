from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.model import Theta, make_design, mu  # noqa: E402
from bayes_constrained.spatial_diagnostics import (  # noqa: E402
    CENSUS_COUNTY_ADJACENCY_2024_URL,
    download_county_adjacency,
    neighbor_map,
    permutation_morans_i,
    read_county_adjacency,
    row_standardized_weights,
    sha256_file,
    within_group_morans_i,
)


PRODUCTION_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "production_8chain"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "spatial_residual_diagnostics"
GLOBAL_PERMUTATIONS = 9999
WITHIN_STATE_PERMUTATIONS = 999
MATERIAL_POSITIVE_I = 0.02
MATERIAL_P_VALUE = 0.05
PRODUCTION_INPUTS = (
    Path("outputs/scientific_reports_v2/production_8chain/production_gate.json"),
    Path(
        "outputs/scientific_reports_v2/production_8chain/"
        "posterior_parameter_draws.parquet"
    ),
    Path(
        "outputs/scientific_reports_v2/production_8chain/"
        "county_posterior_summary.csv"
    ),
    Path("data/processed/bayes_constrained/model_frame.parquet"),
)


def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Required corrected-production artifact is missing: {path}. "
            "Spatial residual diagnostics must not run on pilot or archived v1.1.1 outputs."
        )
    return path


def build_input_manifest(
    root: Path,
    relative_paths: tuple[Path, ...],
) -> dict[str, dict[str, object]]:
    manifest: dict[str, dict[str, object]] = {}
    for relative_path in relative_paths:
        key = relative_path.as_posix()
        path = require(root / relative_path)
        manifest[key] = {
            "path": key,
            "bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        }
    return manifest


def production_input_manifest() -> dict[str, dict[str, object]]:
    return build_input_manifest(ROOT, PRODUCTION_INPUTS)


def verify_input_manifest(
    root: Path,
    manifest: dict[str, dict[str, object]],
) -> None:
    for relative_path, expected in manifest.items():
        path = require(root / relative_path)
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected["sha256"]:
            raise RuntimeError(
                "Production input SHA-256 changed during spatial diagnostics: "
                f"{relative_path}; expected {expected['sha256']}, got {actual_sha256}."
            )


def posterior_mean_theta(frame: pd.DataFrame, draws: pd.DataFrame) -> Theta:
    design = make_design(frame)
    means = draws.groupby("parameter")["value"].mean()
    missing_beta = [term for term in design.columns if term not in means.index]
    if missing_beta:
        raise ValueError(f"Posterior draws are missing fixed effects: {missing_beta}")
    beta = np.asarray([float(means[term]) for term in design.columns], dtype=float)
    state_effect = np.asarray(
        [float(means[f"state_effect[{state}]"]) for state in design.states],
        dtype=float,
    )
    year_effect = np.asarray(
        [float(means[f"year_effect[{year}]"]) for year in design.years],
        dtype=float,
    )
    sigma_state = float(means.get("sigma_state", np.nan))
    sigma_year = float(means.get("sigma_year", np.nan))
    kappa = float(means.get("kappa", np.nan))
    if not np.isfinite(kappa) or kappa <= 0:
        raise ValueError("Posterior draws do not contain a finite positive kappa mean.")
    return Theta(
        beta=beta,
        state_effect=state_effect,
        year_effect=year_effect,
        log_sigma_state=float(np.log(sigma_state)) if np.isfinite(sigma_state) and sigma_state > 0 else np.log(0.2),
        log_sigma_year=float(np.log(sigma_year)) if np.isfinite(sigma_year) and sigma_year > 0 else np.log(0.2),
        log_kappa=float(np.log(kappa)),
    )


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_manifest = production_input_manifest()
    pd.DataFrame(input_manifest.values()).to_csv(
        OUTPUT_ROOT / "production_input_sha256.csv",
        index=False,
    )

    gate = json.loads(
        require(PRODUCTION_ROOT / "production_gate.json").read_text(encoding="utf-8")
    )
    if not gate.get("passed", False):
        raise SystemExit("Corrected production gate did not pass; spatial interpretation is blocked.")

    parameter_draws = pd.read_parquet(
        require(PRODUCTION_ROOT / "posterior_parameter_draws.parquet")
    )
    county_posterior = pd.read_csv(
        require(PRODUCTION_ROOT / "county_posterior_summary.csv"),
        dtype={"county_fips": str, "state_fips": str},
    )
    frame = load_model_frame().copy()
    frame["county_fips"] = frame["county_fips"].astype(str).str.zfill(5)
    frame["state_fips"] = frame["state_fips"].astype(str).str.zfill(2)

    theta = posterior_mean_theta(frame, parameter_draws)
    design = make_design(frame)
    expected = mu(theta, design)
    kappa = float(np.exp(theta.log_kappa))
    conditional_variance = expected + np.square(expected) / kappa
    fitted = frame[["county_fips", "state_fips"]].copy()
    fitted["posterior_mean_expected_county_year_deaths"] = expected
    fitted["posterior_mean_conditional_variance"] = conditional_variance
    fitted_county = (
        fitted.groupby(["county_fips", "state_fips"], as_index=False)
        .agg(
            posterior_mean_expected_county_period_deaths=(
                "posterior_mean_expected_county_year_deaths",
                "sum",
            ),
            posterior_mean_county_period_conditional_variance=(
                "posterior_mean_conditional_variance",
                "sum",
            ),
        )
    )

    county_posterior["county_fips"] = county_posterior["county_fips"].astype(str).str.zfill(5)
    county_posterior["state_fips"] = county_posterior["state_fips"].astype(str).str.zfill(2)
    residuals = county_posterior.merge(
        fitted_county,
        on=["county_fips", "state_fips"],
        how="left",
        validate="one_to_one",
    )
    if residuals["posterior_mean_expected_county_period_deaths"].isna().any():
        missing = residuals.loc[
            residuals["posterior_mean_expected_county_period_deaths"].isna(),
            "county_fips",
        ].tolist()
        raise ValueError(f"Expected-count reconstruction missed counties: {missing[:10]}")
    residuals["raw_residual"] = (
        residuals["posterior_mean_county_period_deaths"]
        - residuals["posterior_mean_expected_county_period_deaths"]
    )
    denominator = np.sqrt(
        residuals["posterior_mean_county_period_conditional_variance"].clip(lower=1e-12)
    )
    residuals["pearson_residual"] = residuals["raw_residual"] / denominator

    adjacency_path = OUTPUT_ROOT / "county_adjacency2024.txt"
    source_manifest = download_county_adjacency(adjacency_path)
    adjacency = read_county_adjacency(adjacency_path)
    counties = residuals["county_fips"].tolist()
    neighbors = neighbor_map(adjacency, counties)
    weights = row_standardized_weights(counties, neighbors)

    global_rows: list[dict[str, object]] = []
    for index, column in enumerate(["raw_residual", "pearson_residual"]):
        result = permutation_morans_i(
            residuals[column].to_numpy(dtype=float),
            weights,
            permutations=GLOBAL_PERMUTATIONS,
            seed=20260811 + index,
        )
        global_rows.append({"residual": column, **result.to_dict()})
    global_table = pd.DataFrame(global_rows)
    global_table.to_csv(OUTPUT_ROOT / "global_morans_i.csv", index=False)

    within_frames: list[pd.DataFrame] = []
    for index, column in enumerate(["raw_residual", "pearson_residual"]):
        table = within_group_morans_i(
            residuals,
            neighbors,
            value_column=column,
            minimum_counties=10,
            permutations=WITHIN_STATE_PERMUTATIONS,
            seed=20260821 + index * 1000,
        )
        if not table.empty:
            table.insert(0, "residual", column)
            within_frames.append(table)
    within_state = (
        pd.concat(within_frames, ignore_index=True)
        if within_frames
        else pd.DataFrame()
    )
    within_state.to_csv(OUTPUT_ROOT / "within_state_morans_i.csv", index=False)

    index_by_county = {county: index for index, county in enumerate(counties)}
    neighbor_mean = []
    for county in counties:
        adjacent = [index_by_county[value] for value in neighbors.get(county, ()) if value in index_by_county]
        if adjacent:
            neighbor_mean.append(float(residuals.iloc[adjacent]["pearson_residual"].mean()))
        else:
            neighbor_mean.append(np.nan)
    residuals["mean_neighbor_pearson_residual"] = neighbor_mean
    residuals["adjacent_model_counties"] = [len(neighbors.get(county, ())) for county in counties]
    residuals.to_csv(OUTPUT_ROOT / "county_spatial_residuals.csv", index=False)

    primary = global_table.loc[global_table["residual"].eq("pearson_residual")].iloc[0]
    material_signal = bool(
        float(primary["statistic"]) >= MATERIAL_POSITIVE_I
        and float(primary["permutation_p_two_sided"]) <= MATERIAL_P_VALUE
    )
    repeated_state_signal = False
    if not within_state.empty:
        state_signal = within_state[
            within_state["residual"].eq("pearson_residual")
            & (within_state["statistic"] >= MATERIAL_POSITIVE_I)
            & (within_state["permutation_p_two_sided"] <= MATERIAL_P_VALUE)
        ]
        repeated_state_signal = len(state_signal) >= 3
    recommendation = (
        "run_spatial_random_effect_sensitivity"
        if material_signal or repeated_state_signal
        else "report_residual_spatial_diagnostic_and_retain_spatial_model_as_prespecified_secondary_sensitivity"
    )
    verify_input_manifest(ROOT, input_manifest)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "production_gate_commit_context": gate,
        "adjacency_source": source_manifest,
        "adjacency_documentation_url": CENSUS_COUNTY_ADJACENCY_2024_URL,
        "counties": int(len(residuals)),
        "counties_with_at_least_one_model_neighbor": int((weights.sum(axis=1) > 0).sum()),
        "posterior_mean_kappa": kappa,
        "global_pearson_morans_i": float(primary["statistic"]),
        "global_pearson_permutation_p_two_sided": float(primary["permutation_p_two_sided"]),
        "material_positive_signal": material_signal,
        "repeated_within_state_signal": repeated_state_signal,
        "prespecified_materiality_threshold": {
            "morans_i_at_least": MATERIAL_POSITIVE_I,
            "two_sided_permutation_p_at_most": MATERIAL_P_VALUE,
            "repeated_states_at_least": 3,
        },
        "recommended_action": recommendation,
        "interpretation_boundary": (
            "Residual spatial autocorrelation is a model diagnostic. It does not identify a causal geographic process, and a non-significant statistic does not prove spatial independence."
        ),
    }
    (OUTPUT_ROOT / "spatial_residual_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 residual spatial-dependence diagnostic",
        "",
        "This analysis is conditional on a passed corrected eight-chain production gate. County-period posterior-mean count residuals were compared with county adjacency using global and within-state Moran statistics.",
        "",
        "| Residual | Moran's I | Expected under randomization | Two-sided permutation p | Nonisolated counties |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in global_table.iterrows():
        lines.append(
            f"| {row['residual']} | {row['statistic']:.5f} | "
            f"{row['expected_under_randomization']:.5f} | "
            f"{row['permutation_p_two_sided']:.5f} | "
            f"{int(row['nonisolated_observations'])} |"
        )
    lines.extend(
        [
            "",
            f"Prespecified action: **{recommendation}**.",
            "",
            "The diagnostic uses the posterior-mean conditional expectation and therefore does not propagate the full posterior distribution into the Moran statistic. It is intended as a transparent residual check and trigger for the separately prespecified spatial sensitivity model.",
        ]
    )
    (OUTPUT_ROOT / "spatial_residual_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
