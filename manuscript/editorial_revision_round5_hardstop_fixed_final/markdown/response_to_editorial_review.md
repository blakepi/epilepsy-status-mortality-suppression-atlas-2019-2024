# Response To Editorial Review

Manuscript: Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024

Author: Gregory Pierpoint, B.S.

## Overview

The revised submission package addresses all major issues, minor issues, author questions, Round 2 completeness checks, the latest figure/age-adjustment editorial review, and the hard-stop package-assembly concerns. The revisions preserve the paper's conservative suppression-sensitive framing while correcting actual DOCX table structure, active figure bytes, figure layout, age-structure wording, supplement self-containment, cover-letter precision, and model-total labeling.

## Hard-Stop Package Assembly Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
| HS-1 | addressed | Rebuilt the main manuscript DOCX and verified with Word COM and python-docx that it contains 5 actual Word tables, not only table-title paragraphs. |
| HS-2 | addressed | Canonical Figure 2 now uses the two-panel rurality/SVI IRR image; the active Figure 2 filename no longer carries the old dense single-panel plot. |
| HS-3 | addressed | Figure 4 remains the 2019-2024 temporal/COVID co-mention figure and is embedded byte-for-byte in the main manuscript DOCX. |
| HS-4 | addressed | Removed the separate figure-legend block from the main DOCX so captions do not appear as orphan paragraphs before the figures; each figure is inserted on its own page with the caption immediately below. |
| HS-5 | addressed | Verified the active abstract DOCX omits the county-year exact-deaths sentence and uses the newer age-adjustment wording. |
| HS-6 | addressed | Verified the active cover-letter DOCX uses reconciled CDC WONDER aggregate outputs rather than stronger validation wording. |
| HS-7 | addressed | Revised Table 3 and related text to distinguish assigned deaths in the full county extract from analytic model deaths after covariate restriction. |
| HS-8 | addressed | Added an `UPLOAD_THESE_FILES_ONLY` folder containing only the current corrected DOCX files to prevent accidental use of stale baseline attachments. |

## Round 3 Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
| R3-1 | addressed | Rebuilt Figure 4 as the corrected 2019-2024 urbanization-year temporal figure with an explicit COVID-19 co-mention panel/context and revised the legend to match the rendered panels. |
| R3-2 | addressed | Replaced Figure 2 with a two-panel plot: nonmetro nonadjacent IRRs and highest-SVI-quartile IRRs, using shorter scenario labels and larger readable axes. |
| R3-3 | addressed | Rebuilt the main manuscript DOCX with one figure per page, caption immediately following each figure, and whitespace-trimmed map images to reduce dead space and avoid cramped figure placement. |
| R3-4 | addressed | Added a dedicated Methods subsection explaining why direct county age-standardization was not used, and clarified that all primary county models adjust for county percentage aged >=65 years and percentage male. |
| R3-5 | addressed | Removed the confusing county-year exact-death sentence from the abstract and main manuscript summary so visible county-year deaths are not mistaken for total mortality. |
| R3-6 | addressed | Tightened repetitive wording by replacing some repeated suppression-aware phrasing with interval-preserving, bounded, reconciliation, and data-visibility language while preserving the conservative scientific frame. |
| R3-7 | addressed | Expanded the supplement language and DOCX content so the full model table, interval results, descriptive context, merge exceptions, and geography notes are embedded rather than merely deferred to the repository. |
| R3-8 | addressed | Revised cover-letter and availability wording to use reconciled CDC WONDER aggregate outputs rather than stronger validation language. |

## Round 2 Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
| B1 | addressed | Restored and embedded Figures 1-4 in the main manuscript DOCX and supplied the same figure files in the package figures folder. |
| B2 | addressed | Restored populated supplementary Tables S1-S10 in the supplement DOCX and supplied supporting CSV/XLSX files. |
| r1 | addressed | Revised the abstract to name the population-scaled residual allocation and interval model as the primary read, and clarified the uniform constant-mean allocation as total-preserving but exposure-ignoring. |
| r2 | addressed | Added a Table 4 footnote that yearly COVID co-mention intervals are suppression-bounded and midpoint sums need not equal the aggregate exactly. |
| r3 | addressed | Restored funding, conflicts, ethics, data/code availability, author contributions, and AI declaration blocks on the title page while retaining them in the main manuscript. |

## Round 1 Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
| M1 | addressed | Reframed suppression scenarios into visible-only, residual-allocation total-preserving, constant-count stress-test, fixed-value stress-test, and interval-model tiers; added residual mean and constant mean scenario; revised abstract/results/discussion. |
| M2 | addressed | Embedded populated Tables 1-5 in the main manuscript DOCX and supplied CSV/XLSX copies. |
| M3 | addressed | Replaced Figure 4 with a 2019-2024 temporal/COVID context figure and corrected legend. |
| M4 | addressed | Added Introduction and Discussion comparison to Quick 2019, distinguishing Bayesian smoothing from reconciliation/bounding/interval methods. |
| m1/m2 | addressed | Removed the orphan county-year exact-death abstract statistic and separated death counts from row counts. |
| m3 | addressed | Rebuilt Figure 2 with publication labels and legend stating 95% CIs on a log scale. |
| m4/m5/m10 | addressed | Added methods limitations for alpha=1 working variance, interval model non-conditioning on the known marginal total, and unadjusted p-values/multiplicity. |
| m6/m9 | addressed | Clarified map viewport/model inclusion and color-scale handling; regenerated Figure 1 with higher zero/missing contrast and hatching. |
| m7 | addressed | Audited residual allocation totals after [1,9] clipping; all residual allocation scenarios preserve 58,380 deaths. |
| m8 | addressed | Replaced vague VIF statement with maximum 2.92 for median household income/poverty component diagnostics. |
| m11 | addressed | Harmonized the corresponding author block to the full affiliation name. |
| m12 | addressed | Confirmed repository README and CITATION metadata identify Gregory Pierpoint; data/code statement names repository and DOI. |
| Author question 8 | addressed | Added Connecticut geography limitation statement noting no crosswalk correction and possible period comparability limitation. |

## Key Interpretive Change

The revised manuscript no longer gives equal interpretive weight to fixed-value scenarios that do not respect the reconciled total. It distinguishes visible-only models, total-preserving residual allocations, a constant-count total-preserving stress test, non-total-preserving fixed-value stress tests, and interval-likelihood models. The main interpretive range is the residual-allocation/interval-model result; fixed-value results are retained to show sensitivity, not to claim a plausible recovered truth.

## Package Completeness

The main manuscript DOCX now contains populated Tables 1-5 and embedded Figures 1-4. Figure 4 has been replaced with a 2019-2024 temporal/COVID context figure. Figure 2 uses publication labels and explicitly reports 95% CIs on a log scale. Figure 1 has increased contrast and hatching for explicit-zero rows. The supplement DOCX contains populated Tables S1-S10 and embedded Figures S1-S3.
