# Epilepsy Mortality Option B

Standalone Phase 9 + Phase 10 analysis project for suppression-aware epilepsy/status epilepticus mortality analyses.

## Scope

- Source extraction project: validated CDC WONDER extraction outputs staged under `data/raw/wonder`
- Validated inputs: Q001-Q015 CDC WONDER processed CSV/parquet outputs
- Primary outcome: multiple-cause ICD-10 G40/G41, 2019-2024
- Sensitivity outcome: underlying-cause ICD-10 G40/G41, 2019-2024
- COVID co-mention syntax: `U07.1 (COVID-19)`

This project reads and copies validated extraction outputs. It does not rerun CDC WONDER queries and does not modify the prior manuscript package.

## Reproducible Run Order

Run from the repository root:

```powershell
python src\00_import_wonder_outputs.py
python src\01_import_covariates.py
python src\02_build_county_period_dataset.py
python src\03_build_county_year_dataset.py
python src\04_suppression_bounds_models.py
python src\05_interval_likelihood_models.py
python src\06_temporal_urbanization_state_models.py
python src\07_descriptive_context_modules.py
python src\08_make_maps_and_figures.py
python src\09_make_tables.py
python src\10_phase10_audit_and_story_selection.py
```

Or run:

```powershell
python src\run_all.py
```

## Main Outputs

- Analytic datasets: `data\processed\county_period_analysis.csv`, `data\processed\county_year_analysis.csv`
- Model results: `tables\suppression_bounds_model_results.csv`, `tables\interval_model_results.csv`
- Manuscript tables: `tables\manuscript_tables.xlsx`
- Descriptive workbook: `tables\descriptive_context_tables.xlsx`
- Figures and maps: `figures\plots`, `figures\maps`
- Phase 9 report: `reports\phase9_final_report.md`
- Phase 10 handoff: `reports\manuscript_prep_handoff.md`
