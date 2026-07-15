# Publication Figure and Manuscript Polish Revision Log

Generated: 2026-06-16 13:04:39

## Scope

- Added a repository-local visualization dependency workflow using `requirements-viz.txt`.
- Added `scripts/check_viz_environment.py` to verify required packages, Matplotlib PNG/SVG/PDF export, and GeoPandas/Pyogrio county-GeoJSON reads.
- Added `scripts/visualization/pub_style.py` for shared journal figure typography, palettes, bundle export, checksums, manifests, and QA.
- Added `scripts/generate_publication_figures.py` as the single publication-figure entrypoint.
- Rebuilt Figures 1-4 from frozen analytic outputs only.
- Added PDF, SVG, EPS, TIFF, and PNG artwork bundles for main figures; TIFF and EPS outputs are checksum-tracked in the figure manifest.
- Preserved mortality counts, IRRs, confidence intervals, captions' scientific interpretation, and the conservative suppression-sensitive framing.
- Rebuilt the final DOCX package and included figure manifest/checksum artifacts.

## Figure Changes

- Figure 1: removed the redundant in-map legend, retained the right-side count/proportion panel, and strengthened the unmatched/missing-covariate overlay.
- Figure 2: expanded the shared log-scale x-axis so the Panel B interval-model CI is fully visible and not silently clipped.
- Figure 3: replaced the main residual-allocation map with a scenario-envelope figure for the nonmetro nonadjacent IRR; moved the residual-allocation atlas to Supplementary Figure S3.
- Figure 4: clarified that COVID bars are midpoint values with lower-upper interval bounds and made interval whiskers more visible.
- Supplementary figures: regenerated S1-S3 with the shared publication style; S3 carries the residual-allocation atlas warning.

## Manuscript Changes

- Compressed main Table 3 to Tier, Scenario, assigned deaths, analytic model deaths, the "Preserves reconciled total?" flag, IRR, and 95% CI.
- Moved long scenario interpretation notes out of main Table 3 while retaining the full scenario audit and full model table in the supplement.
- Converted visible manuscript references to deterministic manually numbered paragraphs beginning at 1.
- Added QA checks for figure formats, manifest checksums, Figure 2 clipping, Figure 3 decision, Figure 4 frozen-input consistency, Table 3 compression, Table 3 total-preservation mapping, final-folder stale states, reference numbering, broken text artifacts, stale filenames, hidden footers, and DOI/repository wording.

## Scientific Guardrails

- CDC WONDER was not re-queried.
- Raw mortality/covariate files were not modified.
- The known core totals and model estimates are preserved in the rebuilt manuscript.
- Residual-allocation county rates remain labeled as illustrative and not recovered true county rates in Supplementary Figure S3.
- The live public GitHub repository and Zenodo DOI wording was retained consistently across submission documents, with the repository/archive citation normalized to v1.0.1.
