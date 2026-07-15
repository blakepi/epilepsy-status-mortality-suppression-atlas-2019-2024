# Manuscript Build Report

Generated: 2026-06-13

## Files Read

- `reports\phase9_final_report.md`
- `reports\phase10_audit_report.md`
- `reports\model_stress_test_summary.md`
- `reports\final_story_decision.md`
- `reports\manuscript_architecture.md`
- `reports\manuscript_prep_handoff.md`
- `reports\hostile_review_report.md`
- `reports\reviewer_risk_register.md`
- `reports\table_figure_triage.md`
- `reports\model_results_report.md`
- `reports\suppression_status_report.md`
- `reports\temporal_context_report.md`
- `reports\atlas_figure_report.md`
- `reports\county_merge_report.md`
- `tables\manuscript_tables.xlsx`
- `tables\table1_county_characteristics.csv`
- `tables\table2_mortality_by_rurality_svi.csv`
- `tables\table3_suppression_aware_models.csv`
- `tables\table4_temporal_context.csv`
- `tables\table5_ucd_sensitivity.csv`
- `figures\maps`
- `figures\plots`
- Old candidate reference metadata: `C:\Users\gbp34\OneDrive\Documents\Epilepsy Mortality\epilepsy_mortality_feasibility\submission\epilepsy_behavior\references\reference_metadata_phase9.csv`

## Tables Used

- Table 1: county characteristics by death status.
- Table 2: mortality totals/rates by rurality and SVI.
- Table 3: suppression-aware model results.
- Table 4: temporal/urbanization/COVID context.
- Table 5: UCD sensitivity, recommended for supplement unless retained after target-journal decision.

## Figures Used

- Figure 1: `figures\maps\map1_county_suppression_status.png`
- Figure 2: `figures\plots\suppression_bounds_forest_plot.png`
- Figure 3: `figures\maps\map3_suppression_aware_predicted_rates.png`
- Figure 4: `figures\plots\urbanization_year_trend.png` and `figures\plots\covid_comention_urbanization_year.png` as paired temporal/COVID context

## Main Story Selected

Phase 10 selected Story C: rurality findings were highly suppression-sensitive. The manuscript was rebuilt around suppression-aware uncertainty, data visibility, bounded inference, and national mortality mapping.

## Key Results Inserted

- Q003 MCOD total, 2019-2024: 58,380.
- Q001 county-period total row: 58,380.
- Q001 exact county death sum: 51,388.
- Q001 suppressed county rows: 1,722.
- Q001 explicit zero county rows: 335.
- Q002 county-year exact death sum: 33,217.
- Q010 COVID co-mention total: 1,936.
- Q012 UCD total: 22,306.
- Q014 UCD exact county death sum: 16,650.
- Q014 UCD suppressed county rows: 1,866.
- Q014 UCD explicit zero county rows: 772.
- Nonmetro nonadjacent IRR scenarios from the rurality plus SVI composite family.
- Interval-likelihood nonmetro nonadjacent estimates.
- Denominator decision using summed Q002 annual county populations as person-years.
- RUCC collapse and SVI/ACS family separation.

## Results Not Inserted and Why

- Full race/ethnicity and place-of-death descriptive tables were not inserted into the main text because Phase 10 triage placed detailed descriptive modules in the supplement.
- State-period map details were not inserted into the main text because the county suppression atlas is more central to Story C.
- Full interval-model diagnostics were summarized but not fully inserted because Phase 9 identified approximate standard errors and bias-bounding as the primary evidence.

## Missing Files

No required Phase 11 source files were missing. All required tables, reports, and figure directories were present.

## Inconsistencies Found

The temporal/context source report contained wording that should not be carried into the Phase 11 draft because the prompt requested avoidance of certain overclaiming language. The Phase 11 manuscript uses person-level and ecological wording instead.

## Language Changed to Avoid Overclaiming

- Avoided stating that rurality was definitively associated with higher mortality.
- Avoided treating exact-count counties as the complete county universe.
- Avoided describing suppressed cells as zero or missing.
- Used "suppression-sensitive," "bounded," "outcome-dependent suppression," "data visibility," and "ecological county-level analysis."
- Avoided prohibited phrases from the prompt in deliverables.

## Quality-Control Checks

- Story C framing appears in Abstract, Results, Discussion, and Conclusions.
- Key totals match Phase 9/10 source reports.
- Suppressed cells are described as intervals of 1-9 deaths.
- Table and figure callouts are ordered.
- Abbreviations are defined at first use in the main draft.
- No `.docx` or journal submission files were created.
- CDC WONDER was not rerun.
- `C:\Research\CDCWonderExtraction` was not modified.
- The old Epilepsy & Behavior submission package was read only for candidate reference metadata and was not modified.

## Remaining Tasks Before Phase 12

- Human scientific review of the manuscript logic and results emphasis.
- Decide final target journal.
- Verify all references and replace placeholders with final citations.
- Complete author metadata, funding, disclosures, acknowledgments, and contribution statements.
- Decide whether Table 5 belongs in main text or supplement.
- Decide whether maps require Alaska/Hawaii insets for the chosen journal.
- Prepare `.docx`, journal-specific formatting, and submission package only in Phase 12.

## Final Recommendation

READY_WITH_MINOR_OPEN_ITEMS
