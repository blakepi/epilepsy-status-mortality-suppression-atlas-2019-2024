#!/bin/bash -l
#SBATCH --job-name=epi_bayes_extend
#SBATCH --partition=main
#SBATCH --time=48:00:00
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
mkdir -p "$PROJECT_HOME/logs/slurm" "$PROJECT_SCRATCH/logs/slurm"
trap 'status=$?; bash "$PROJECT_SCRATCH/hpc/wahab/sync_results_home.sh" || true; exit $status' EXIT
cd "$PROJECT_SCRATCH"
source "$VENV_PATH/bin/activate"
export PYTHONPATH="$PROJECT_HOME"
export MPLBACKEND=Agg
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
echo "hostname=$(hostname)"
echo "date=$(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-}"
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-}"
echo "SLURM_MEM_PER_NODE=${SLURM_MEM_PER_NODE:-}"
echo "pwd=$(pwd)"
echo "python=$(command -v python)"
echo "git_commit=$(git -C "$PROJECT_HOME" rev-parse HEAD 2>/dev/null || echo not_available)"
echo "HPC_EXTENSION_ROUND=${HPC_EXTENSION_ROUND:-}"
python scripts/31_fit_bayes_constrained_model.py --mode extend --config hpc/wahab/configs/bayes_constrained_hpc_extend.yaml --chain-id "$SLURM_ARRAY_TASK_ID" --array-task-id "$SLURM_ARRAY_TASK_ID" --out-dir outputs/bayes_constrained/hpc --checkpoint-every 500 --max-runtime-minutes 2820 --stop-before-time-limit-minutes 15 --resume
