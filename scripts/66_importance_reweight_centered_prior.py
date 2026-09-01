from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.reweight import reweighted_parameter_summary  # noqa: E402


def main() -> None:
    chain_root = ROOT / "outputs" / "bayes_constrained" / "production_8chain" / "chains"
    paths = sorted(chain_root.glob("chain_*/draws_params.parquet"))
    if len(paths) != 8:
        raise SystemExit(f"Expected eight archived parameter-draw files; found {len(paths)}.")
    draws = pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)
    summary, diagnostics = reweighted_parameter_summary(draws)

    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "prior_reweighting"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "centered_prior_reweighted_parameters.csv", index=False)
    (output_dir / "centered_prior_reweighting_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    focus_parameters = [
        "primary_rurality_metro_other",
        "primary_rurality_nonmetro_adjacent",
        "primary_rurality_nonmetro_nonadjacent",
        "svi_quartile_Q4_highest",
        "sigma_state",
        "sigma_year",
    ]
    focus = summary[summary["parameter"].isin(focus_parameters)].copy()
    focus.to_csv(output_dir / "centered_prior_reweighted_focus.csv", index=False)
    lines = [
        "# Importance reweighting for the centered-prior normalization correction",
        "",
        "The corrected target differs from the archived v1.1.1 target by the exact multiplicative factor sigma_state × sigma_year. Archived joint parameter draws were therefore importance-reweighted to estimate the isolated effect of this prior-normalization correction before launching a new production run.",
        "",
        "This calculation does not repair or assess latent-state mixing and does not replace the corrected rerun. It is an efficient diagnostic of whether the prior correction alone is likely to move the principal parameter estimates.",
        "",
        "## Weight diagnostics",
        "",
        f"- Draws: {int(diagnostics['draws']):,}",
        f"- Importance ESS: {diagnostics['importance_effective_sample_size']:.1f}",
        f"- ESS fraction: {diagnostics['importance_ess_fraction']:.4f}",
        f"- Maximum normalized weight: {diagnostics['maximum_normalized_weight']:.8f}",
        f"- Weight coefficient of variation: {diagnostics['weight_coefficient_of_variation']:.4f}",
        "",
        "## Focus estimates",
        "",
        "| Parameter | v1.1.1 median | Reweighted median | v1.1.1 95% interval | Reweighted 95% interval | Relative median shift |",
        "| --- | ---: | ---: | --- | --- | ---: |",
    ]
    for _, row in focus.iterrows():
        lines.append(
            f"| {row['parameter']} | {row['v111_median']:.6f} | "
            f"{row['corrected_prior_reweighted_median']:.6f} | "
            f"{row['v111_lower_95']:.6f}–{row['v111_upper_95']:.6f} | "
            f"{row['corrected_prior_reweighted_lower_95']:.6f}–{row['corrected_prior_reweighted_upper_95']:.6f} | "
            f"{row['median_relative_shift_percent']:.4f}% |"
        )
    lines.extend(
        [
            "",
            "Interpretation is conditional on the archived joint sample adequately representing the v1.1.1 target. The final Scientific Reports v2 estimates must come from newly sampled corrected chains.",
        ]
    )
    (output_dir / "centered_prior_reweighting.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(diagnostics, sort_keys=True))


if __name__ == "__main__":
    main()
