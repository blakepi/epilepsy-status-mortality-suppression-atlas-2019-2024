#!/bin/bash -l
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"

cd "$PROJECT_HOME"
source "$VENV_PATH/bin/activate"
python scripts/75_prepare_sr_v2_production.py
bash hpc/wahab/stage_to_scratch.sh

cd "$PROJECT_SCRATCH"
mkdir -p logs/slurm outputs/scientific_reports_v2/production_8chain
production_job="$(sbatch --parsable hpc/wahab/slurm/60_sr_v2_production_chain_array.sbatch)"
finalize_job="$(sbatch --parsable --dependency="afterok:${production_job}" hpc/wahab/slurm/61_sr_v2_finalize_production.sbatch)"

submitted_at="$(date -Is)"
record="$PROJECT_HOME/outputs/scientific_reports_v2/production_8chain/submitted_jobs.tsv"
mkdir -p "$(dirname "$record")"
if [ ! -e "$record" ]; then
  printf 'submitted_at\tstage\tjob_id\tdependency\tscript\n' > "$record"
fi
printf '%s\tproduction_array\t%s\t\t%s\n' \
  "$submitted_at" "$production_job" "hpc/wahab/slurm/60_sr_v2_production_chain_array.sbatch" >> "$record"
printf '%s\tfinalize\t%s\tafterok:%s\t%s\n' \
  "$submitted_at" "$finalize_job" "$production_job" "hpc/wahab/slurm/61_sr_v2_finalize_production.sbatch" >> "$record"

echo "production_job=$production_job"
echo "finalize_job=$finalize_job"
echo "submission_record=$record"
