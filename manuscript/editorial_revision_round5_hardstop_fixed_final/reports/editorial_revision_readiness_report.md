# Editorial Revision Hard-Stop Fix Readiness Report

Generated: 2026-06-15 20:03:09

## Final Recommendation

READY_FOR_EDITORIAL_REVIEW_WITH_STANDARD_HUMAN_FINAL_CHECKS

## Core Editorial Fixes

- Hard-stop package assembly fixed: `UPLOAD_THESE_FILES_ONLY` contains only the current corrected DOCX files, with no baseline snapshot files or stale duplicate submissions.
- Main manuscript table gate fixed: Word COM and python-docx read-back confirm 5 actual Word tables in `manuscript_main_revised.docx`.
- Figure file ambiguity fixed: canonical Figure 2 file now points to the two-panel rurality/SVI figure, and old dense single-panel Figure 2 bytes are not retained under the active Figure 2 filename.
- Figure caption/layout fixed: separate orphan figure-legend paragraphs were removed from the main DOCX; each figure page contains the image followed immediately by its caption.
- Model-total labeling fixed: Table 3 separates assigned deaths in the full county extract from analytic model deaths after covariate restriction.
- Round 3 Figure 4 fixed: main manuscript Figure 4 displays 2019-2024 urbanization-year MCOD counts and COVID-19 co-mention context, with caption wording matched to the rendered panels.
- Round 3 Figure 2 fixed: replaced dense single diagnostic plot with a two-panel rurality/SVI IRR figure using cleaner scenario labels.
- Round 3 layout fixed: main manuscript figures are placed one per page with captions immediately beneath each figure; map figures use whitespace-trimmed image assets.
- Round 3 age-adjustment concern addressed: Methods, Results, and Limitations clarify the age-structure rationale, the absence of direct county age-standardization, and the use of county age/sex covariates in primary models.
- Round 3 abstract fixed: the confusing county-year exact-death sentence is removed from active manuscript and abstract files.
- Round 3 supplement fixed: supplement DOCX embeds full model, interval, descriptive, merge, and geography tables rather than requiring repository lookup for interpretation.
- Round 3 cover-letter wording fixed: "validated CDC WONDER outputs" changed to "reconciled CDC WONDER aggregate outputs."
- Round 2 B1 fixed: main manuscript DOCX contains embedded Figures 1-4; supplement DOCX contains embedded Figures S1-S3.
- Round 2 B2 fixed: supplement DOCX contains populated Tables S1-S10.
- Round 2 r1-r3 fixed: abstract clarifies the primary population-scaled/interval read and uniform allocation interpretation; Table 4 explains COVID midpoint intervals; title page includes declaration blocks.
- M1 reframed: scenario hierarchy now distinguishes visible-only models, total-preserving residual allocations, constant-count stress tests, non-total-preserving fixed stress tests, and interval models.
- M2 fixed: main manuscript DOCX contains populated Tables 1-5.
- M3 fixed: Figure 4 now covers 2019-2024 and includes COVID co-mention context.
- M4 fixed: Introduction and Discussion now position the work relative to Quick 2019.
- Minor issues addressed: abstract unit mix, orphan Q002 statistic removed, Figure 2 labels, alpha/interval/multiplicity caveats, map scope, residual allocation clipping audit, VIF maximum, affiliation consistency, repository author consistency, and Connecticut geography limitation.

## Reconciliation Audit

- MCOD total: 58,380
- Exact county deaths: 51,388
- Suppressed residual: 6,992
- Suppressed rows: 1,722
- Mean deaths per suppressed row: 4.060
- Residual allocation totals preserved after 1-9 clipping: True

## Package Contents

- DOCX files: 8
- Markdown files: 8
- Figure files: 9
- Revised table files: 10
- Main manuscript embedded media count: 4
- Supplement embedded media count: 3
- Main manuscript table count: 5
- Supplement table count: 10

## QC

- DOCX read-back readable files: 8/8
- Forbidden-language scan hits: 0
- Overclaim scan hits: 0
- DOI present: True
- GitHub URL present: True

## Word/Visual QA

LibreOffice/soffice was not available on PATH in this environment, so the packaged LibreOffice DOCX-to-PNG render gate could not be used. Microsoft Word COM was available and used for authoritative document-open, table-count, and image-count checks. Human Microsoft Word/PDF visual inspection remains a standard final portal check.

## Remaining Human Checks

- Final reference-manager formatting check.
- Microsoft Word visual inspection and journal portal PDF check.
- Confirmation that the target journal wants tables embedded in the main manuscript versus uploaded as separate table files.
