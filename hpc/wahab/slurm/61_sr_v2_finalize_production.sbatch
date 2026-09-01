#!/bin/bash -l
#SBATCH --job-name=epi_sr_v2_finalize
#SBATCH --partition=timed-main
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=logs/slurm/%x_%j.out
#SBATCH --error=logs/slurm/%x_%j.err

set -euo pipefail
PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
mkdir -p "$PROJECT_HOME/logs/slurm" "$PROJECT_SCRATCH/logs/slurm"
trap 'status=$?; bash "$PROJECT_SCRATCH/hpc/wahab/sync_sr_v2_results_home.sh" || true; exit $status' EXIT

cd "$PROJECT_SCRATCH"
source "$VENV_PATH/bin/activate"
export PYTHONPATH="$PROJECT_SCRATCH/src:$PROJECT_HOME"
export MPLBACKEND=Agg
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

python scripts/77_merge_sr_v2_production.py
python scripts/78_gate_sr_v2_production.py
