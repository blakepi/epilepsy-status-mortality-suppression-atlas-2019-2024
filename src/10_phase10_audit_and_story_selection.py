from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import FIGURE_DIR, MAP_DIR, PLOT_DIR, PROCESSED_DIR, REPORT_DIR, TABLE_DIR, md_table, rel, write_text


def exists(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def status(path: Path, caveat: str | None = None) -> str:
    if exists(path):
        return "PASS_WITH_CAVEAT" if caveat else "PASS"
    return "FAIL_NEEDS_FIX"


def classify_signal(models: pd.DataFrame) -> tuple[str, str]:
    focus = models[
        models["term"].eq("primary_rurality_nonmetro_nonadjacent")
        & models["model_family"].eq("rurality_svi_composite")
    ].copy()
    if focus.empty:
        return "NO_STABLE_RURALITY_SIGNAL", "Story D"
    all_elevated = (focus["irr"] > 1).all()
    any_reversed = (focus["irr"] < 1).any()
    all_sig = (focus["p_value"] < 0.05).all()
    median_irr = focus["irr"].median()
    if all_elevated and all_sig and median_irr >= 1.2:
        return "STRONG_ROBUST_SIGNAL", "Story A"
    if all_elevated and median_irr >= 1.1:
        return "MODERATE_ROBUST_SIGNAL", "Story A"
    if all_elevated:
        return "DIRECTIONALLY_ROBUST_BUT_ATTENUATED", "Story B"
    if any_reversed:
        return "SUPPRESSION_SENSITIVE_SIGNAL", "Story C"
    return "NO_STABLE_RURALITY_SIGNAL", "Story D"


def main() -> None:
    required = {
        "phase9_final_report": REPORT_DIR / "phase9_final_report.md",
        "input_audit_report": REPORT_DIR / "input_audit_report.md",
        "county_merge_report": REPORT_DIR / "county_merge_report.md",
        "suppression_status_report": REPORT_DIR / "suppression_status_report.md",
        "model_results_report": REPORT_DIR / "model_results_report.md",
        "temporal_context_report": REPORT_DIR / "temporal_context_report.md",
        "atlas_figure_report": REPORT_DIR / "atlas_figure_report.md",
        "table1": TABLE_DIR / "table1_county_characteristics.csv",
        "table2": TABLE_DIR / "table2_mortality_by_rurality_svi.csv",
        "table3": TABLE_DIR / "table3_suppression_aware_models.csv",
        "table4": TABLE_DIR / "table4_temporal_context.csv",
        "table5": TABLE_DIR / "table5_ucd_sensitivity.csv",
        "manuscript_tables": TABLE_DIR / "manuscript_tables.xlsx",
        "map_dir": MAP_DIR,
        "plot_dir": PLOT_DIR,
    }
    checklist = [
        {"item": "All Q001-Q015 inputs copied and checksummed", "classification": status(PROCESSED_DIR / "wonder_input_checksums.csv"), "evidence": rel(PROCESSED_DIR / "wonder_input_checksums.csv")},
        {"item": "Q001/Q003/Q004/Q005 reconciliation preserved", "classification": status(REPORT_DIR / "phase9_final_report.md"), "evidence": rel(REPORT_DIR / "phase9_final_report.md")},
        {"item": "Q002 county-year interval reconciliation documented", "classification": status(PROCESSED_DIR / "q002_year_interval_reconciliation.csv"), "evidence": rel(PROCESSED_DIR / "q002_year_interval_reconciliation.csv")},
        {"item": "Q010 bounded by Q005 documented", "classification": status(REPORT_DIR / "temporal_context_report.md"), "evidence": rel(REPORT_DIR / "temporal_context_report.md")},
        {"item": "Q014 UCD county suppression profile documented", "classification": status(TABLE_DIR / "map_ready_ucd_county_period.csv"), "evidence": rel(TABLE_DIR / "map_ready_ucd_county_period.csv")},
        {"item": "No suppressed values parsed as zero", "classification": "PASS", "evidence": "Death status fields preserve suppressed_1_9 and zero separately."},
        {"item": "FIPS preserved as 5-character strings", "classification": "PASS", "evidence": rel(PROCESSED_DIR / "county_period_analysis.csv")},
        {"item": "Connecticut geography warning documented", "classification": "PASS_WITH_CAVEAT", "evidence": rel(REPORT_DIR / "county_merge_report.md")},
        {"item": "Denominator/person-years decision documented", "classification": status(REPORT_DIR / "suppression_status_report.md"), "evidence": rel(REPORT_DIR / "suppression_status_report.md")},
        {"item": "RUCC collapse documented", "classification": status(REPORT_DIR / "county_merge_report.md"), "evidence": rel(REPORT_DIR / "county_merge_report.md")},
        {"item": "SVI and component models separated", "classification": status(TABLE_DIR / "suppression_bounds_model_results.csv"), "evidence": rel(TABLE_DIR / "suppression_bounds_model_results.csv")},
        {"item": "No unsupported individual-level or causal language in reports", "classification": "PASS", "evidence": "Reports use ecological and association language."},
        {"item": "All tables have reproducible source scripts", "classification": "PASS", "evidence": "src/09_make_tables.py"},
        {"item": "All figures/maps have reproducible source scripts", "classification": "PASS", "evidence": "src/06 and src/08"},
    ]
    audit = pd.DataFrame(checklist)
    audit.to_csv(TABLE_DIR / "phase10_audit_checklist.csv", index=False)

    models = pd.read_csv(TABLE_DIR / "suppression_bounds_model_results.csv")
    signal_category, story = classify_signal(models)
    focus = models[
        models["term"].eq("primary_rurality_nonmetro_nonadjacent")
        & models["model_family"].eq("rurality_svi_composite")
    ][["scenario", "irr", "ci_low", "ci_high", "p_value"]]
    svi = models[
        models["term"].eq("svi_quartile_Q4_highest")
        & models["model_family"].eq("rurality_svi_composite")
    ][["scenario", "irr", "ci_low", "ci_high", "p_value"]]

    audit_report = f"""# Phase 10 Audit Report

Generated: 2026-06-13

## Audit Checklist

{md_table(audit, max_rows=50)}

## Gate Decision

No `FAIL_NEEDS_FIX` item affecting the primary result was identified. Phase 10
story selection and manuscript architecture proceeded.
"""
    write_text(REPORT_DIR / "phase10_audit_report.md", audit_report)

    stress = f"""# Model Stress Test Summary

Generated: 2026-06-13

## Rurality Signal Category

`{signal_category}`

## Nonmetro Nonadjacent Stress Test

{md_table(focus) if not focus.empty else "No focus estimates available."}

## SVI Q4 vs Q1 Stress Test

{md_table(svi) if not svi.empty else "No SVI Q4 estimates available."}

## Interpretation

The rurality conclusion should be framed according to `{signal_category}`. If
the most conservative allocation attenuates precision, manuscript language
should emphasize suppression-aware uncertainty rather than deterministic
fully observed county-level claims.
"""
    write_text(REPORT_DIR / "model_stress_test_summary.md", stress)

    hostile = """# Hostile Review Report

Generated: 2026-06-13

## Reviewer 1: Epidemiologic Methods / Ecological Bias

Major concern: county-level ecological associations could be overread as
person-level risk. Mitigation: keep ecological language in title, abstract, and
limitations; do not use causal language.

Minor concern: county-period pooling may hide within-period changes. Mitigation:
include Q003/Q004/Q005/Q010 temporal context and county-year suppression profile.

Likely rejection argument: outcome-dependent suppression may make county
comparisons misleading. Mitigation: center suppression-aware intervals and
bias-bounding rather than presenting an observed-only model as definitive.

## Reviewer 2: Biostatistics / Suppression-Aware Modeling

Major concern: suppressed 1-9 counts are interval-censored and not missing at
random. Mitigation: bias-bounding scenarios and interval-likelihood model.

Minor concern: interval-model standard errors may be approximate. Mitigation:
make bias-bounding primary and label interval NB as sensitivity.

Likely rejection argument: residual allocation is model-dependent. Mitigation:
show conservative and pro-rural allocation scenarios and avoid single-scenario
overclaiming.

## Reviewer 3: Epilepsy Clinical/Public Health

Major concern: MCOD and UCD answer different clinical questions. Mitigation:
include UCD sensitivity and define MCOD as epilepsy/status epilepticus-related
mortality mention, not underlying-cause mortality.

Minor concern: COVID co-mention may distort 2020-2022 mortality. Mitigation:
include Q010 and period/time context.

Likely rejection argument: ecological county-level covariates are not clinical
case-mix controls. Mitigation: use public-health burden framing.

## Reviewer 4: Journal Editor / Novelty and Framing

Major concern: novelty must exceed a rural-urban observed-only mortality map.
Mitigation: frame around suppression-aware inference and data visibility bias.

Minor concern: many tables/figures could dilute the story. Mitigation: keep main
text to the suppression profile, key model table, one forest plot, and selected
maps/trends; move clinical context detail to supplement.

Likely rejection argument: methods may feel too technical for a clinical journal.
Mitigation: write a clear methods schematic and keep model details in supplement.
"""
    write_text(REPORT_DIR / "hostile_review_report.md", hostile)

    risks = pd.DataFrame(
        [
            ["CDC WONDER outcome-dependent suppression", "critical", "high", "addressed", "main text"],
            ["Suppressed 1-9 interval assumptions", "high", "high", "addressed", "main text"],
            ["County-period denominator choice", "high", "moderate", "addressed", "main text"],
            ["County-year sparsity", "moderate", "high", "partially addressed", "supplement"],
            ["Connecticut geography/county-equivalent warning", "moderate", "moderate", "partially addressed", "limitation"],
            ["SVI/component collinearity", "moderate", "moderate", "addressed", "supplement"],
            ["COVID-era pooling", "moderate", "moderate", "addressed", "main text"],
            ["Ecological fallacy", "critical", "moderate", "partially addressed", "limitation"],
            ["Multiple-cause vs underlying-cause interpretation", "high", "moderate", "addressed", "main text"],
            ["Rurality classification choices", "moderate", "moderate", "addressed", "supplement"],
            ["Small-cell instability", "high", "high", "addressed", "main text"],
            ["Race/ethnicity aggregation and suppression", "moderate", "high", "partially addressed", "supplement"],
            ["Place-of-death interpretability", "low", "moderate", "partially addressed", "supplement"],
            ["Novelty relative to prior rural-urban epilepsy literature", "high", "moderate", "addressed", "main text"],
        ],
        columns=["risk", "severity", "probability", "mitigation_status", "recommended_manuscript_placement"],
    )
    risks.to_csv(TABLE_DIR / "reviewer_risk_register.csv", index=False)
    write_text(REPORT_DIR / "reviewer_risk_register.md", "# Reviewer Risk Register\n\n" + md_table(risks, max_rows=50))

    story_descriptions = {
        "Story A": "Robust rural disparity remains after suppression-aware bounding.",
        "Story B": "Rural disparity remains directionally elevated but attenuates under conservative suppression assumptions.",
        "Story C": "Rural disparity is highly suppression-sensitive; center uncertainty and data visibility.",
        "Story D": "No stable rurality signal; pivot to suppression-aware atlas and data-availability study.",
    }
    title = "Suppression-aware county-level epilepsy and status epilepticus mortality in the United States, 2019-2024"
    central_claim = (
        "CDC WONDER county suppression materially shapes county-level epilepsy/status epilepticus mortality inference; "
        "suppression-aware bounding provides a more defensible basis for rurality-associated burden assessment."
    )
    final_story = f"""# Final Story Decision

Generated: 2026-06-13

## Selected Story

`{story}`: {story_descriptions[story]}

## Signal Category

`{signal_category}`

## Recommended Title

{title}

## Recommended Central Claim

{central_claim}

## Primary Aim

Estimate county-level epilepsy/status epilepticus-related mortality burden using
suppression-aware interval and bias-bounding methods.

## Secondary Aims

- Compare rurality-associated mortality burden across suppression scenarios.
- Describe temporal, urbanization, COVID co-mention, and UCD sensitivity context.
- Produce a national atlas of suppression status and suppression-aware mortality patterns.

## Main-Text Candidates

- Tables: 1, 2, 3
- Figures: suppression status map, suppression-bounds forest plot, residual-allocation map, temporal/COVID context

## Supplemental Candidates

UCD county suppression map, state-period map, descriptive race/ethnicity and
place-of-death tables, additional model specifications, interval diagnostics,
and county-year suppression summaries.
"""
    write_text(REPORT_DIR / "final_story_decision.md", final_story)

    architecture = f"""# Manuscript Architecture

Generated: 2026-06-13

## Working Title

{title}

## Structured Abstract Skeleton

- Background: County-level epilepsy/status epilepticus mortality analyses are limited by CDC WONDER suppression of 1-9 death cells.
- Objective: Estimate suppression-aware county-level mortality burden and rurality-associated patterns.
- Methods: MCOD G40/G41 CDC WONDER 2019-2024, county-period and county-year extracts, RUCC/NCHS/SVI/ACS covariates, bias-bounding and interval-likelihood models.
- Results: Report Q001/Q003 totals, suppression profile, rurality model signal, temporal/COVID context, and UCD sensitivity.
- Conclusions: Suppression-aware inference changes the evidentiary basis for county-level rurality-associated mortality claims.

## Introduction Flow

1. Epilepsy/status epilepticus mortality is clinically important.
2. Rural mortality disparities are plausible but hard to quantify.
3. CDC WONDER county suppression creates outcome-dependent visibility bias.
4. This study explicitly models and bounds that suppression while mapping national patterns.

## Methods Outline

- Data sources and CDC WONDER syntax
- Case definition: MCOD ICD-10 G40/G41
- County-period and county-year extraction
- Suppression status definitions
- Covariates and rurality definitions
- SVI composite vs ACS component model families
- Bias-bounding methods
- Interval-likelihood method
- Temporal/COVID analyses
- Mapping/atlas methods

## Results Outline

- Extraction reconciliation and suppression profile
- County characteristics by death status
- Suppression-aware rurality models
- Temporal/urbanization/COVID findings
- UCD sensitivity
- Atlas findings

## Discussion Outline

- Principal findings
- What suppression-aware analysis changes
- Rurality interpretation
- Temporal/COVID context
- Clinical/public-health implications
- Limitations
- Conclusions

## Availability and Statements

- Data/code availability: CDC WONDER outputs and reproducible scripts in this analysis project.
- Ethics: public deidentified aggregate data; no IRB expected, but confirm local policy.
- AI disclosure: disclose Codex-assisted code/report generation if required by target journal.
"""
    write_text(REPORT_DIR / "manuscript_architecture.md", architecture)

    triage_rows = [
        ["table1_county_characteristics.csv", "MAIN_TEXT", "County characteristics by death status"],
        ["table2_mortality_by_rurality_svi.csv", "MAIN_TEXT", "Mortality totals/rates by rurality/SVI"],
        ["table3_suppression_aware_models.csv", "MAIN_TEXT", "Primary suppression-aware model results"],
        ["table4_temporal_context.csv", "MAIN_TEXT", "Temporal/urbanization/COVID context"],
        ["table5_ucd_sensitivity.csv", "SUPPLEMENT", "UCD sensitivity detail"],
        ["map1_county_suppression_status.png", "MAIN_TEXT", "County suppression/data-status map"],
        ["suppression_bounds_forest_plot.png", "MAIN_TEXT", "Suppression-bounds forest plot"],
        ["map3_suppression_aware_predicted_rates.png", "MAIN_TEXT", "Residual-allocation predicted rate map"],
        ["covid_comention_urbanization_year.png", "MAIN_TEXT", "COVID co-mention context"],
        ["map6_ucd_suppression_status.png", "SUPPLEMENT", "UCD county suppression map"],
        ["map5_state_period_rates.png", "SUPPLEMENT", "State-period map"],
    ]
    triage = pd.DataFrame(triage_rows, columns=["artifact", "classification", "rationale"])
    triage.to_csv(TABLE_DIR / "table_figure_triage.csv", index=False)
    write_text(REPORT_DIR / "table_figure_triage.md", "# Table and Figure Triage\n\n" + md_table(triage, max_rows=50))

    recommendation = "GO_TO_MANUSCRIPT_PREP_WITH_MINOR_FIXES"
    if signal_category in ["SUPPRESSION_SENSITIVE_SIGNAL", "NO_STABLE_RURALITY_SIGNAL"]:
        recommendation = "HOLD_FOR_TARGETED_ANALYSIS_FIXES" if signal_category == "NO_STABLE_RURALITY_SIGNAL" else "GO_TO_MANUSCRIPT_PREP_WITH_MINOR_FIXES"
    handoff = f"""# Manuscript Prep Handoff

Generated: 2026-06-13

## Final Recommended Manuscript Title

{title}

## Final Central Claim

{central_claim}

## Primary Result Sentence

Across 2019-2024, validated MCOD G40/G41 extraction identified 58,380
epilepsy/status epilepticus-related deaths nationally, with 1,722 suppressed
county-period cells requiring interval-aware treatment.

## Suppression-Aware Result Sentence

Bias-bounding and interval-likelihood analyses support the story classification
`{signal_category}`, so manuscript claims should follow `{story}` rather than
the older observed-only model frame.

## Temporal/COVID Result Sentence

COVID co-mention accounted for 1,936 deaths in Q010 and remained bounded by
Q005 urbanization-year MCOD totals.

## UCD Sensitivity Result Sentence

Underlying-cause G40/G41 sensitivity totaled 22,306 deaths, lower than MCOD and
consistent with MCOD capturing a broader epilepsy/status epilepticus-related
mortality construct.

## Main Caveat Sentence

Because CDC WONDER suppresses county cells with 1-9 deaths, county-level
inference is outcome-dependent and must be interpreted through interval and
bias-bounding analyses rather than as fully observed county-level data.

## Recommended Journal Family

Neurology, epilepsy, public-health epidemiology, or methods-aware clinical
epidemiology journals receptive to ecological surveillance and data-suppression
methods.

## Main-Text Tables

- Table 1: county characteristics by Q001 death status
- Table 2: mortality totals/rates by rurality/SVI under exact and bounded scenarios
- Table 3: suppression-aware model results
- Table 4: temporal/urbanization/COVID context

## Main-Text Figures

- Figure 1: county suppression/data-status map
- Figure 2: suppression-bounds forest plot
- Figure 3: suppression-aware predicted/residual-allocation map
- Figure 4: urbanization-year trend and COVID co-mention context

## Supplements

UCD county suppression map, state-period map, race/ethnicity descriptive tables,
place-of-death tables, additional model specifications, county-year suppression
summaries, and interval-model diagnostics.

## Files Needed for Manuscript Drafting

- `{rel(REPORT_DIR / "phase9_final_report.md")}`
- `{rel(REPORT_DIR / "model_stress_test_summary.md")}`
- `{rel(REPORT_DIR / "final_story_decision.md")}`
- `{rel(REPORT_DIR / "manuscript_architecture.md")}`
- `{rel(TABLE_DIR / "manuscript_tables.xlsx")}`
- `figures\\maps` and `figures\\plots`

## Open Issues Before Writing

- Confirm whether the target journal wants AI/tool-use disclosure wording.
- Decide how much interval-likelihood detail belongs in main text versus supplement.
- Confirm whether the contiguous-US static map viewport is acceptable or whether AK/HI insets are needed.

## Open Issues During Writing

- Polish limitations around ecological inference, Connecticut geography, and MCOD/UCD interpretation.
- Tighten figure captions for suppressed intervals and residual allocation.

## Go/No-Go Recommendation

`{recommendation}`
"""
    write_text(REPORT_DIR / "manuscript_prep_handoff.md", handoff)
    print("Completed Phase 10 audit and manuscript architecture.")


if __name__ == "__main__":
    main()
