# Wahab HPC Run Plan

## Rationale

The confirmatory Bayesian constrained run uses CPU `main` because the sampler is CPU Python/NumPy/SciPy code and does not use GPU kernels. GPU partitions and GPU resource flags are not requested. Job arrays are used because independent MCMC chains and short tuning pilots map naturally to separate Slurm array tasks without reserving full nodes.

`timed-main` is used only for the smoke test, tuning pilots, and short finalization/failure jobs expected to finish under two hours. Production and extension chains use `main`.

## Resource Requests

| Stage | Partition | Time | CPUs | Memory | Purpose |
| --- | --- | ---: | ---: | ---: | --- |
| 00 smoke | timed-main | 01:30:00 | 4 | 16G | imports, environment check, tiny sampler smoke, pytest subset |
| 10 prepare | main | 04:00:00 | 8 | 64G | model frame, reconciliation, MILP starts |
| 20 tune | timed-main | 01:50:00 | 4 | 32G | 16 short tuning configurations |
| 25 select | main | 01:00:00 | 2 | 16G | choose tuning configuration |
| 30 production | main | 72:00:00 | 4 | 64G | 8 independent production chains |
| 35 extend | main | 48:00:00 | 4 | 64G | resume/extend chains from checkpoints |
| 40 summarize/gate | main | 08:00:00 | 8 | 96G | merge, validate, diagnostics, convergence gate |
| 45 decide | main | 00:30:00 | 1 | 8G | submit extension, finalization, or failure report |
| 50 finalize | timed-main | 01:30:00 | 4 | 16G | regenerate tables, figures, manuscript, reports |
| 99 failure | timed-main | 00:30:00 | 1 | 8G | parse logs and write diagnostic report |

## Expected Outputs

- `outputs/bayes_constrained/hpc/environment_wahab_report.txt`
- `outputs/bayes_constrained/hpc/submitted_jobs.tsv`
- `outputs/bayes_constrained/hpc/chain_status_summary.csv`
- `outputs/bayes_constrained/hpc/convergence_gate.json`
- `outputs/bayes_constrained/hpc/convergence_gate.md`
- `outputs/bayes_constrained/hpc/hpc_runtime_summary.csv`
- `outputs/bayes_constrained/hpc/hpc_constraint_validation_summary.csv`
- `outputs/bayes_constrained/hpc/hpc_mcmc_diagnostics.csv`
- `outputs/bayes_constrained/hpc/Wahab_HPC_Final_Report.md` after a passing gate
- refreshed Bayesian tables, figures, manuscript, supplement, and run report

## Manual Steps Left

Authenticate to Wahab, upload or sync the project, run bootstrap, stage to scratch, submit the pipeline, monitor jobs, and fetch results.

## Commands

```powershell
cd C:\Research\EpilepsyMortalityOptionB
.\hpc\wahab\local_pack_and_upload.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu
```

```bash
ssh pierpogb@wahab.hpc.odu.edu
cd /home/pierpogb/EpilepsyMortalityOptionB
bash hpc/wahab/bootstrap_env.sh
bash hpc/wahab/stage_to_scratch.sh
bash hpc/wahab/submit_pipeline.sh
bash hpc/wahab/monitor.sh
```

```powershell
cd C:\Research\EpilepsyMortalityOptionB
.\hpc\wahab\local_fetch_results.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu
```

## Resume And Continuation

Each chain writes checkpoints under `outputs/bayes_constrained/hpc/chains/chain_XX/checkpoints/`. Extension jobs resume from the latest valid checkpoint. `45_decide_next.sbatch` reads `convergence_gate.json`, increments `extension_round.txt` when needed, and submits the next extension and gate jobs automatically.

## Convergence Gate

Final manuscript generation is blocked unless the convergence gate passes all requested R-hat, ESS, latent-validation, chain-status, grand-total, and suppression-handling checks. A failed gate writes exact reasons and either requests extension or stops with a non-final diagnostic report.
