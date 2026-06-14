from __future__ import annotations

from utils import run_script


SCRIPTS = [
    "00_import_wonder_outputs.py",
    "01_import_covariates.py",
    "02_build_county_period_dataset.py",
    "03_build_county_year_dataset.py",
    "04_suppression_bounds_models.py",
    "05_interval_likelihood_models.py",
    "06_temporal_urbanization_state_models.py",
    "07_descriptive_context_modules.py",
    "08_make_maps_and_figures.py",
    "09_make_tables.py",
    "10_phase10_audit_and_story_selection.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"=== {script} ===", flush=True)
        run_script(script)


if __name__ == "__main__":
    main()
