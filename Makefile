PYTHON := .venv/Scripts/python.exe

.PHONY: check-viz-env figures qa-figures manuscript bayes_prepare bayes_initialize bayes_fit_quick bayes_fit bayes_summarize bayes_figures bayes_manuscript bayes_validate bayes_all production_gate submission_figures submission_tables submission_manuscript submission_supplement submission_qc submission_package submission_all

check-viz-env:
	$(PYTHON) scripts/check_viz_environment.py

figures:
	$(PYTHON) scripts/generate_publication_figures.py

qa-figures:
	$(PYTHON) scripts/generate_publication_figures.py --qa-only

manuscript:
	$(PYTHON) src/editorial_revision_package.py

bayes_prepare:
	$(PYTHON) scripts/30_prepare_bayes_constrained_frame.py

bayes_initialize: bayes_prepare

bayes_fit_quick: bayes_prepare
	$(PYTHON) scripts/31_fit_bayes_constrained_model.py --mode quick

bayes_fit: bayes_prepare
	$(PYTHON) scripts/31_fit_bayes_constrained_model.py --mode production

bayes_summarize:
	$(PYTHON) scripts/32_summarize_bayes_constrained_model.py

bayes_figures:
	$(PYTHON) scripts/33_make_bayes_tables_figures.py

bayes_manuscript:
	$(PYTHON) scripts/34_update_manuscript_bayes.py

bayes_validate:
	$(PYTHON) -m pytest tests/test_bayes_constrained.py

bayes_all: bayes_prepare bayes_fit_quick bayes_fit bayes_summarize bayes_validate

production_gate:
	$(PYTHON) scripts/hpc_wahab/gate_convergence.py --hpc-out outputs/bayes_constrained/production_8chain --fail-on-stop-nonfinal

submission_figures:
	$(PYTHON) scripts/50_build_submission_figures.py

submission_tables:
	$(PYTHON) scripts/51_build_submission_tables.py

submission_manuscript:
	$(PYTHON) scripts/52_polish_manuscript_submission.py

submission_supplement:
	$(PYTHON) scripts/53_build_submission_supplement.py

submission_qc:
	$(PYTHON) scripts/54_qc_submission_package.py

submission_package:
	$(PYTHON) scripts/55_package_submission_assets.py

submission_all: submission_figures submission_tables submission_manuscript submission_supplement submission_package
