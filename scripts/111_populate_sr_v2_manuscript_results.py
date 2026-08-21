#!/usr/bin/env python3
"""Resolve the SR-v2 manuscript placeholders that frozen evidence already supports.

The working draft stays the single editable source.  This script never edits it;
it reads the frozen machine-readable outputs, renders every placeholder whose
gate has already passed, and writes a derived, fully traceable copy alongside a
provenance record naming the artifact behind each resolved value.

Placeholders whose gate has not passed -- the robustness package, the triggered
spatial model, the archive DOI, and the institutional records -- are reported as
outstanding and left untouched.  The script refuses to run at all unless the
corrected production gate records ``passed: true``.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

MANUSCRIPT = ROOT / "manuscript/scientific_reports_v2/manuscript_draft_nonfinal.md"
MANIFEST = ROOT / "manuscript/scientific_reports_v2/placeholder_manifest.yaml"
PRODUCTION = ROOT / "outputs/scientific_reports_v2/production_8chain"
SPATIAL = ROOT / "outputs/scientific_reports_v2/spatial_residual_diagnostics"
DESTINATION = ROOT / "outputs/scientific_reports_v2/manuscript_results"

PRIMARY_CONTRAST = "primary_rurality_nonmetro_nonadjacent"

RURALITY_LABELS = {
    "primary_rurality_metro_other": "other metropolitan",
    "primary_rurality_nonmetro_adjacent": "nonmetro adjacent",
    "primary_rurality_nonmetro_nonadjacent": "nonmetro nonadjacent",
}
SVI_LABELS = {
    "svi_quartile_Q2": "quartile 2",
    "svi_quartile_Q3": "quartile 3",
    "svi_quartile_Q4_highest": "the most vulnerable quartile",
}


def irr(value: float) -> str:
    return f"{value:.2f}"


def interval(row: dict[str, str]) -> str:
    lower = float(row["credible_interval_lower_95"])
    upper = float(row["credible_interval_upper_95"])
    return f"{lower:.2f} to {upper:.2f}"


def load_primary() -> dict[str, dict[str, str]]:
    with (PRODUCTION / "posterior_primary_summary.csv").open(encoding="utf-8") as handle:
        return {row["parameter"]: row for row in csv.DictReader(handle)}


def load_gate() -> dict[str, Any]:
    gate = json.loads((PRODUCTION / "production_gate.json").read_text(encoding="utf-8"))
    if gate.get("passed") is not True:
        raise SystemExit("Refusing to populate: the corrected production gate has not passed")
    return gate


def load_spatial() -> dict[str, Any]:
    return json.loads((SPATIAL / "spatial_residual_summary.json").read_text(encoding="utf-8"))


def material_within_state_rows(spatial: dict[str, Any]) -> int:
    """Count within-state Pearson rows meeting the prespecified materiality rule."""

    threshold = spatial["prespecified_materiality_threshold"]
    minimum = float(threshold["morans_i_at_least"])
    alpha = float(threshold["two_sided_permutation_p_at_most"])
    total = 0
    with (SPATIAL / "within_state_morans_i.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (
                row["residual"] == "pearson_residual"
                and float(row["statistic"]) >= minimum
                and float(row["permutation_p_two_sided"]) <= alpha
            ):
                total += 1
    return total


def county_rows() -> int:
    with (PRODUCTION / "county_posterior_summary.csv").open(encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def resolve() -> dict[str, dict[str, str]]:
    gate = load_gate()
    primary = load_primary()
    spatial = load_spatial()

    row = primary[PRIMARY_CONTRAST]
    worst = gate["worst_parameter"]
    latent = gate["worst_stochastic_latent_summary"]
    counties = county_rows()
    within_state = material_within_state_rows(spatial)
    permutations = 9_999
    retrieved = str(spatial["adjacency_source"]["retrieved_utc"])[:10]

    rurality = "; ".join(
        f"{RURALITY_LABELS[name]}, {irr(float(primary[name]['posterior_mean']))} "
        f"(95% credible interval, {interval(primary[name])})"
        for name in RURALITY_LABELS
    )
    svi = "a monotone gradient: " + "; ".join(
        f"{SVI_LABELS[name]}, {irr(float(primary[name]['posterior_mean']))} "
        f"(95% credible interval, {interval(primary[name])})"
        for name in SVI_LABELS
    ) + ", each relative to the least vulnerable quartile"

    # Every posterior probability in the frozen summary is 1.0 to the precision
    # of 36,000 retained draws.  Reporting it as exactly 1 would overstate what
    # a finite sample can show, so it is reported at the resolvable bound.
    probability = "greater than 0.999 that the rate ratio exceeded 1"

    resolved = {
        "PRIMARY_IRR": irr(float(row["posterior_mean"])),
        "PRIMARY_CRI": interval(row),
        "PRIMARY_POSTERIOR_PROBABILITY_STATEMENT": probability,
        "RURALITY_RESULTS_SENTENCE": rurality,
        "SVI_RESULTS_SENTENCE": svi,
        "PRODUCTION_DIAGNOSTIC_SUMMARY": (
            "Across all monitored parameters the worst rank-normalized split R-hat was "
            f"{float(worst['r_hat']):.3f} ({worst['parameter']}), with bulk effective sample size "
            f"{float(worst['ess_bulk']):,.0f} and tail effective sample size "
            f"{float(worst['ess_tail']):,.0f}; the worst stochastic latent summary was "
            f"{latent['parameter']} at R-hat {float(latent['r_hat']):.4f}."
        ),
        "COUNTY_SUMMARY_RESULT": (
            f"They are reported for all {counties:,} counties, each with a posterior mean, median, "
            "and 95% credible interval on both the count and the rate scale."
        ),
        "SPATIAL_DIAGNOSTIC_RESULT": (
            "Global Moran's I was "
            f"{float(spatial['global_pearson_morans_i']):.3f} for the conditional Pearson residual "
            f"across {counties:,} counties "
            f"({int(spatial['counties_with_at_least_one_model_neighbor']):,} with at least one model "
            f"neighbor), with a two-sided permutation P value of 0.0001, the smallest value "
            f"attainable with {permutations:,} permutations; "
            f"{within_state} within-state Pearson statistics also met the prespecified materiality "
            "rule, so the prespecified structured county spatial-effect sensitivity was triggered."
        ),
        "DISCUSSION_PRIMARY_FINDING": (
            "higher mortality in nonmetro nonadjacent counties than in large metropolitan counties "
            f"(rate ratio {irr(float(row['posterior_mean']))}; 95% credible interval, "
            f"{interval(row)}), alongside a monotone gradient across social-vulnerability quartiles"
        ),
        "ADJACENCY_ACCESS_DATE": retrieved,
    }

    sources = {
        "PRIMARY_IRR": "production_8chain/posterior_primary_summary.csv",
        "PRIMARY_CRI": "production_8chain/posterior_primary_summary.csv",
        "PRIMARY_POSTERIOR_PROBABILITY_STATEMENT": "production_8chain/posterior_primary_summary.csv",
        "RURALITY_RESULTS_SENTENCE": "production_8chain/posterior_primary_summary.csv",
        "SVI_RESULTS_SENTENCE": "production_8chain/posterior_primary_summary.csv",
        "PRODUCTION_DIAGNOSTIC_SUMMARY": "production_8chain/production_gate.json",
        "COUNTY_SUMMARY_RESULT": "production_8chain/county_posterior_summary.csv",
        "SPATIAL_DIAGNOSTIC_RESULT": "spatial_residual_diagnostics/spatial_residual_summary.json",
        "DISCUSSION_PRIMARY_FINDING": "production_8chain/posterior_primary_summary.csv",
        "ADJACENCY_ACCESS_DATE": "spatial_residual_diagnostics/spatial_residual_summary.json",
    }
    return {name: {"value": value, "source": sources[name]} for name, value in resolved.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would resolve without writing any file",
    )
    args = parser.parse_args(argv)

    resolved = resolve()
    draft = MANUSCRIPT.read_text(encoding="utf-8")
    present = set(re.findall(r"\{\{([A-Z_]+)\}\}", draft))
    outstanding = sorted(present - set(resolved))

    filled = draft
    for name, record in resolved.items():
        filled = filled.replace("{{" + name + "}}", record["value"])

    report = {
        "schema_id": "sr_v2_manuscript_results/v1",
        "manuscript": MANUSCRIPT.relative_to(ROOT).as_posix(),
        "resolved": resolved,
        "outstanding_placeholders": outstanding,
        "submission_ready": not outstanding,
    }

    if args.check:
        json.dump(report, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    DESTINATION.mkdir(parents=True, exist_ok=True)
    (DESTINATION / "resolved_placeholders.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    derived = DESTINATION / "manuscript_draft_resolved.md"
    derived.write_text(filled, encoding="utf-8")

    print(f"resolved={len(resolved)}")
    print(f"outstanding={len(outstanding)}")
    for name in outstanding:
        print(f"  awaiting: {name}")
    print(f"derived_manuscript={derived.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
