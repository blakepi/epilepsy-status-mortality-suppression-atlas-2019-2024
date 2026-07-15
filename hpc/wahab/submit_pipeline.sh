#!/bin/bash -l
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
cd "$PROJECT_HOME"
mkdir -p logs/slurm outputs/bayes_constrained/hpc
JOBS_TSV="outputs/bayes_constrained/hpc/submitted_jobs.tsv"
printf "submitted_at\tstage\tjob_id\tdependency\tscript\n" > "$JOBS_TSV"

submit_job() {
  local stage="$1"
  local script="$2"
  local dependency="${3:-}"
  local job_id
  if [ -n "$dependency" ]; then
    job_id=$(sbatch --parsable --dependency="$dependency" "$script" | cut -d';' -f1)
  else
    job_id=$(sbatch --parsable "$script" | cut -d';' -f1)
  fi
  printf "%s\t%s\t%s\t%s\t%s\n" "$(date -Is)" "$stage" "$job_id" "$dependency" "$script" >> "$JOBS_TSV"
  echo "$job_id"
}

smoke=$(submit_job smoke hpc/wahab/slurm/00_smoke_timed.sbatch)
prepare=$(submit_job prepare_initialize hpc/wahab/slurm/10_prepare_initialize.sbatch "afterok:$smoke")
tune=$(submit_job tune_array hpc/wahab/slurm/20_tune_array_timed.sbatch "afterok:$prepare")
select=$(submit_job select_tuning hpc/wahab/slurm/25_select_tuning.sbatch "afterok:$tune")
production=$(submit_job production_chain_array hpc/wahab/slurm/30_production_chain_array.sbatch "afterok:$select")
summarize=$(submit_job summarize_gate hpc/wahab/slurm/40_summarize_gate.sbatch "afterok:$production")
decide=$(submit_job decide_next hpc/wahab/slurm/45_decide_next.sbatch "afterok:$summarize")
failure=$(submit_job failure_report hpc/wahab/slurm/99_failure_report.sbatch "afternotok:$smoke:$prepare:$tune:$select:$production:$summarize:$decide")
mkdir -p "$PROJECT_SCRATCH/outputs/bayes_constrained/hpc"
cp "$JOBS_TSV" "$PROJECT_SCRATCH/$JOBS_TSV"

echo "submitted_jobs=$JOBS_TSV"
echo "smoke=$smoke prepare=$prepare tune=$tune select=$select production=$production summarize=$summarize decide=$decide failure=$failure"
