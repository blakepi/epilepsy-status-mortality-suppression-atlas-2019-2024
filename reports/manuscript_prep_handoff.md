# Manuscript Prep Handoff

Generated: 2026-06-13

## Final Recommended Manuscript Title

Suppression-aware county-level epilepsy and status epilepticus mortality in the United States, 2019-2024

## Final Central Claim

CDC WONDER county suppression materially shapes county-level epilepsy/status epilepticus mortality inference; suppression-aware bounding provides a more defensible basis for rurality-associated burden assessment.

## Primary Result Sentence

Across 2019-2024, validated MCOD G40/G41 extraction identified 58,380
epilepsy/status epilepticus-related deaths nationally, with 1,722 suppressed
county-period cells requiring interval-aware treatment.

## Suppression-Aware Result Sentence

Bias-bounding and interval-likelihood analyses support the story classification
`SUPPRESSION_SENSITIVE_SIGNAL`, so manuscript claims should follow `Story C` rather than
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

- `reports\phase9_final_report.md`
- `reports\model_stress_test_summary.md`
- `reports\final_story_decision.md`
- `reports\manuscript_architecture.md`
- `tables\manuscript_tables.xlsx`
- `figures\maps` and `figures\plots`

## Open Issues Before Writing

- Confirm whether the target journal wants AI/tool-use disclosure wording.
- Decide how much interval-likelihood detail belongs in main text versus supplement.
- Confirm whether the contiguous-US static map viewport is acceptable or whether AK/HI insets are needed.

## Open Issues During Writing

- Polish limitations around ecological inference, Connecticut geography, and MCOD/UCD interpretation.
- Tighten figure captions for suppressed intervals and residual allocation.

## Go/No-Go Recommendation

`GO_TO_MANUSCRIPT_PREP_WITH_MINOR_FIXES`
