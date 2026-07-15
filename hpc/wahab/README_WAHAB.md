# Wahab HPC Workflow

## What Codex Generated

This folder contains a complete Wahab SLURM workflow for the Bayesian constrained county-level epilepsy/status epilepticus mortality analysis. It adds:

- local Windows upload/download helpers;
- login-node environment bootstrap and optional wheelhouse build scripts;
- scratch staging and home-result synchronization scripts;
- a single `submit_pipeline.sh` dependency DAG;
- Slurm batch scripts for smoke, preparation, tuning, production chains, extension chains, convergence gating, finalization, and failure reporting;
- HPC YAML configs for smoke, tuning, production, and extension;
- Python helpers in `scripts/hpc_wahab/` for environment validation, tuning selection, output merging, convergence gating, continuation, and reporting.

## Manual Steps Left

The user still needs to authenticate, satisfy DUO prompts, upload or sync the prepared project, run bootstrap, stage to scratch, submit the pipeline, monitor jobs, and fetch results. No passwords, tokens, or DUO details are stored in this repository.

## Why CPU Main Is Used

The sampler is CPU-oriented Python/NumPy/SciPy code with integer latent-count moves and sparse MILP initialization. The workflow does not request GPU resources because no code path uses GPU acceleration. Production jobs use the standard CPU `main` partition; short smoke and tuning pilots use `timed-main` because that partition is capped at two hours.

## Home, Scratch, And RC

- `/home/pierpogb/EpilepsyMortalityOptionB` is the canonical project location, virtual-environment anchor, final-output mirror, and backed-up record.
- `/scratch/pierpogb/EpilepsyMortalityOptionB` is the active compute run directory for high-I/O chain files and checkpoints.
- `/RC` is for long-term/archive storage on login nodes only; compute jobs in this workflow do not run from `/RC`.

## Exact Commands

Upload from Windows:

```powershell
cd C:\Research\EpilepsyMortalityOptionB
.\hpc\wahab\local_pack_and_upload.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu
```

SSH:

```bash
ssh pierpogb@wahab.hpc.odu.edu
cd /home/pierpogb/EpilepsyMortalityOptionB
```

Bootstrap:

```bash
bash hpc/wahab/bootstrap_env.sh
```

Stage to scratch:

```bash
bash hpc/wahab/stage_to_scratch.sh
```

Submit the full pipeline:

```bash
bash hpc/wahab/submit_pipeline.sh
```

Monitor:

```bash
squeue -u pierpogb
bash hpc/wahab/monitor.sh
```

Cancel without deleting outputs:

```bash
bash hpc/wahab/cancel_pipeline.sh
```

Fetch results from Windows:

```powershell
cd C:\Research\EpilepsyMortalityOptionB
.\hpc\wahab\local_fetch_results.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu
```

## Output Files To Inspect

- `outputs/bayes_constrained/hpc/environment_wahab_report.txt`
- `outputs/bayes_constrained/hpc/submitted_jobs.tsv`
- `outputs/bayes_constrained/hpc/chain_status_summary.csv`
- `outputs/bayes_constrained/hpc/convergence_gate.json`
- `outputs/bayes_constrained/hpc/convergence_gate.md`
- `outputs/bayes_constrained/hpc/hpc_mcmc_diagnostics.csv`
- `outputs/bayes_constrained/hpc/Wahab_HPC_Final_Report.md`
- `RUN_BAYES_CONSTRAINED_REPORT.md`

## Convergence Thresholds

The final manuscript is blocked unless all of these pass:

- primary nonmetro nonadjacent IRR split R-hat <= 1.05 and ESS >= 400;
- all rurality IRRs split R-hat <= 1.05 and ESS >= 300;
- all SVI IRRs split R-hat <= 1.08 and ESS >= 200;
- kappa, sigma_state, and sigma_year split R-hat <= 1.10;
- every saved latent draw validation passes;
- no chain reports failure or missing outputs;
- the grand total remains 58,380;
- suppressed cells are never treated as zero.

If the gate fails and extension rounds remain, `45_decide_next.sbatch` submits another extension array, then another summarize/gate job, then itself again. If extension rounds are exhausted, it submits the failure-report job and does not create an inferential final manuscript.

## If Jobs Fail

Run:

```bash
bash hpc/wahab/diagnose_failure.sh
```

Then inspect:

- `outputs/bayes_constrained/hpc/failure_diagnosis.md`
- `logs/slurm/*.err`
- `outputs/bayes_constrained/hpc/output_completion_check.md`

## What To Send ODU RCC

If support is needed, send the job IDs from `outputs/bayes_constrained/hpc/submitted_jobs.tsv`, the relevant `logs/slurm/*err` and `*out` files, the command that failed, and this project path:

```text
/home/pierpogb/EpilepsyMortalityOptionB
```

Do not send passwords, DUO codes, or private tokens.
