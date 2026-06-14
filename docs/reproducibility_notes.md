# Reproducibility Notes

## Purpose

This release supports reproduction of the suppression-aware aggregate-data analysis for county-level epilepsy/status epilepticus mortality in the United States, 2019-2024.

## Inputs

The repository includes staged aggregate CDC WONDER outputs and public covariate/geography inputs. It does not include person-level data and does not automate CDC WONDER browser extraction.

## Environment

Create a Python environment and install dependencies:

```bash
pip install -r requirements.txt
```

## Run order

The script `src/run_all.py` executes the main analysis pipeline. Individual numbered scripts can also be inspected and run in order:

1. `00_import_wonder_outputs.py`
2. `01_import_covariates.py`
3. `02_build_county_period_dataset.py`
4. `03_build_county_year_dataset.py`
5. `04_suppression_bounds_models.py`
6. `05_interval_likelihood_models.py`
7. `06_temporal_urbanization_state_models.py`
8. `07_descriptive_context_modules.py`
9. `08_make_maps_and_figures.py`
10. `09_make_tables.py`
11. `10_phase10_audit_and_story_selection.py`

## Expected outputs

Outputs are written under `data/processed/`, `tables/`, `figures/`, and `reports/`. The analysis preserves suppressed counts as bounded intervals and keeps explicit zeros distinct from suppression.

## Important interpretation note

The analysis is ecological and county-level. It does not estimate person-level risk and should not be interpreted as causal evidence.
