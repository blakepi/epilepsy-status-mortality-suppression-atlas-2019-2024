# Publication Figure and Manuscript Polish Revision Log

Generated: 2026-06-16 12:01:23

## Scope

- Added a repository-local visualization dependency workflow using `requirements-viz.txt`.
- Added `scripts/check_viz_environment.py` to verify required packages, Matplotlib PNG/SVG/PDF export, and GeoPandas/Pyogrio county-GeoJSON reads.
- Added `scripts/visualization/pub_style.py` for shared journal figure typography, palettes, bundle export, checksums, manifests, and QA.
- Added `scripts/generate_publication_figures.py` as the single publication-figure entrypoint.
- Rebuilt Figures 1-4 from frozen analytic outputs only.
- Preserved mortality counts, IRRs, confidence intervals, captions' scientific interpretation, and the conservative suppression-sensitive framing.
- Rebuilt the final DOCX package and included figure manifest/checksum artifacts.

## Figure Changes

- Figure 1: GeoPandas-based contiguous-US data visibility map with exact, suppressed-positive, explicit-zero categories and missing-covariate hatch overlay.
- Figure 2: Two-panel forest plot with scenario tiers grouped visually and total-preserving residual allocations emphasized.
- Figure 3: GeoPandas-based residual-allocation/data-visibility atlas with discrete rate bins and unavoidable allocation warning.
- Figure 4: Polished temporal/COVID context figure with direct line labels and explicit denominator caveat.

## Scientific Guardrails

- CDC WONDER was not re-queried.
- Raw mortality/covariate files were not modified.
- The known core totals and model estimates are preserved in the rebuilt manuscript.
- Residual-allocation county rates remain labeled as illustrative and not recovered true county rates.
