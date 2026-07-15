# Bayesian Constrained Final Run Report

Generated: 2026-07-15T11:13:36

## Final Wahab HPC Result

The final Wahab HPC production run completed eight independent constrained Bayesian chains. All 69 retained parameters passed rank-normalized split R-hat and bulk/tail ESS criteria. The maximum R-hat was 1.008554; minimum bulk ESS was 1437.2; minimum 5%/95% tail ESS was 3199.4. All 36,000 saved latent-count draws passed constraint validation.

- National MCOD G40/G41 total: 58,380
- Model frame: 18,852 county-year rows from 3,142 counties
- Saved parameter draws in final summaries: 36,000
- Primary nonmetro nonadjacent vs large metropolitan mortality rate ratio: 1.23 (95% CrI 1.17–1.30); Pr(IRR > 1)=1.00

## Outputs

- Final submission manuscript: `outputs\submission\package\manuscript_submission_FINAL.docx`
- Final submission supplement: `outputs\submission\package\supplement_submission_FINAL.docx`
- Final QC report: `outputs\submission\qc\SUBMISSION_QC_REPORT_FINAL.md`

## Interpretation Guardrails

The outcome is a multiple-cause mortality mention of ICD-10 G40/G41, not person-level incidence or etiologic attribution. Posterior county summaries are model-derived constrained Bayesian quantities and should not be described as recovered true suppressed counts.
