# Suppression-Aware Bayesian Analysis of County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024

Code, processed public aggregate data, parameter draws, validation evidence, tables, figures, and manuscript text for a constrained Bayesian analysis of county-level epilepsy/status epilepticus mortality mentions in the United States.

Version 1.1.0 adds the exact eight-chain Wahab HPC production results and replaces the earlier provisional Bayesian handoff with checksum-verified production artifacts.

## Primary result

The primary nonmetro nonadjacent versus large metropolitan mortality rate ratio was 1.23 (95% credible interval, 1.17–1.30). Across all 69 retained parameters, the maximum rank-normalized split R-hat was 1.0086, the minimum bulk ESS was 1437.2, and the minimum 5%/95% tail ESS was 3199.4. All 36,000 saved latent-count draws passed 489,696 recorded constraint checks.

These are ecological, model-derived county estimates. They are not recovered suppressed counts or person-level risks.

## Repository map

- `src/bayes_constrained/`: constrained latent-count model, sampler, summaries, and modern diagnostics.
- `scripts/30_*.py` through `scripts/34_*.py`: data preparation, fitting, summarization, and Bayesian manuscript outputs.
- `hpc/wahab/` and `scripts/hpc_wahab/`: Slurm production workflow, merge logic, convergence gate, and reporting.
- `outputs/bayes_constrained/production_8chain/`: public per-chain parameter draws, resolved configurations, statuses, acceptance summaries, all-parameter diagnostics, validation summaries, and manifests.
- `outputs/submission/`: final public tables, figures, manuscript Markdown, supplement Markdown, and QC report.
- `data/processed/bayes_constrained/`: frozen model frame and initialization artifacts.
- `docs/production_chain_verification.md`: production-chain provenance, checks, and retained limitations.
- `data/raw/`, `data/processed/`, `src/00_*.py` through `src/10_*.py`: the original aggregate-data and sensitivity-analysis workflow retained from v1.0.x.

No person-level data are included.

## Environment and tests

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-bayes.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The release-time public convergence gate can be rerun without the large latent arrays:

```powershell
.\.venv\Scripts\python.exe scripts\hpc_wahab\gate_convergence.py `
  --hpc-out outputs\bayes_constrained\production_8chain `
  --fail-on-stop-nonfinal
```

To re-verify an extracted full production archive, including every latent-count array and its totals, provide its chain root:

```powershell
.\.venv\Scripts\python.exe scripts\60_verify_production_chains.py `
  --chains-root C:\path\to\bayes_hpc_extract\outputs\bayes_constrained\hpc\chains `
  --output-dir outputs\bayes_constrained\production_8chain
```

## Publication artifacts

- Manuscript: `outputs/submission/manuscript/manuscript_submission.md`
- Supplement: `outputs/submission/manuscript/supplement_submission.md`
- Final QC: `outputs/submission/qc/SUBMISSION_QC_REPORT_FINAL.md`
- Convergence gate: `outputs/bayes_constrained/production_8chain/convergence_gate.md`
- Production verification: `outputs/bayes_constrained/production_8chain/production_verification.md`
- Full file checksums: `repository_file_checksums.csv`

## Retained limitations

Several parameter proposal blocks had acceptance rates outside the nominal 0.20–0.45 tuning target. This is reported as an efficiency warning, not a convergence failure, because all-parameter R-hat and bulk/tail ESS criteria passed.

The custom constraint-preserving latent-count kernel has extensive empirical invariant checks but does not yet have an exact enumerated small-state stationary-distribution and irreducibility test. That targeted methodological test remains recommended before journal submission. Large latent arrays are excluded from the public release because of size; their hashes, full compressed validation records, and derived summaries are included.

## Citation

Pierpoint G. *Suppression-Aware Bayesian Analysis of County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024*. Version 1.1.0. Zenodo. https://doi.org/10.5281/zenodo.20691622

The DOI above is the concept DOI and resolves to the latest published Zenodo version.

## Contact

Gregory Pierpoint, B.S.

ORCID: https://orcid.org/0000-0001-8288-8549

Email: pierpogb@odu.edu
