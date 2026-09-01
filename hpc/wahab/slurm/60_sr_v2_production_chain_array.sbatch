#!/bin/bash -l
#SBATCH --job-name=epi_sr_v2_prod
#SBATCH --partition=main
#SBATCH --time=72:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --array=1-8%8
#SBATCH --output=logs/slurm/%x_%A_%a.out
#SBATCH --error=logs/slurm/%x_%A_%a.err
#SBATCH --signal=B:USR1@300

set -euo pipefail
PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
OUTPUT_ROOT="outputs/scientific_reports_v2/production_8chain"
mkdir -p "$PROJECT_HOME/logs/slurm" "$PROJECT_SCRATCH/logs/slurm" "$PROJECT_SCRATCH/$OUTPUT_ROOT/config"
trap 'status=$?; bash "$PROJECT_SCRATCH/hpc/wahab/sync_sr_v2_results_home.sh" || true; exit $status' EXIT

cd "$PROJECT_SCRATCH"
source "$VENV_PATH/bin/activate"
export PYTHONPATH="$PROJECT_SCRATCH/src:$PROJECT_HOME"
export MPLBACKEND=Agg
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

cp hpc/wahab/configs/sr_v2_production.yaml "$OUTPUT_ROOT/config/sr_v2_production.yaml"
cp hpc/wahab/configs/sr_v2_frozen_production_tuning.yaml "$OUTPUT_ROOT/config/frozen_production_tuning.yaml"
cp hpc/wahab/configs/sr_v2_production_preparation_manifest.json "$OUTPUT_ROOT/production_preparation_manifest.json"

echo "hostname=$(hostname)"
echo "date=$(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-}"
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-}"
echo "SLURM_MEM_PER_NODE=${SLURM_MEM_PER_NODE:-}"
echo "pwd=$(pwd)"
echo "python=$(command -v python)"
echo "git_commit=$(git -C "$PROJECT_HOME" rev-parse HEAD 2>/dev/null || echo not_available)"

python scripts/76_run_sr_v2_production_chain.py \
  --chain-id "$SLURM_ARRAY_TASK_ID" \
  --max-runtime-minutes 4260 \
  --stop-before-time-limit-minutes 15
