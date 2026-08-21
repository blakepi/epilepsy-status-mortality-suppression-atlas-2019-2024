#!/bin/bash -l
#SBATCH --job-name=epi_sr_v2_spatial_bench
#SBATCH --partition=main
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=logs/slurm/%x_%j.out
#SBATCH --error=logs/slurm/%x_%j.err

# Throughput canary.  Runs exactly 2,000 iterations of the prepared target and
# refuses the launch unless the reviewed validator agrees the full chain fits
# inside 65 projected hours and 56 GiB.  Publishes no scientific draws.
set -euo pipefail
PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
mkdir -p "$PROJECT_HOME/logs/slurm" "$PROJECT_SCRATCH/logs/slurm"
trap 'status=$?; bash "$PROJECT_SCRATCH/hpc/wahab/sync_sr_v2_spatial_sensitivity_results_home.sh" || true; exit $status' EXIT

cd "$PROJECT_SCRATCH"
# The venv interpreter is addressed by absolute path rather than by activation:
# it cannot be defeated by PATH order, and only the staged, validated scratch
# tree is importable.
export PYTHONPATH="$PROJECT_SCRATCH/src"
export MPLBACKEND=Agg
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

echo "hostname=$(hostname)"
echo "date=$(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "python=$VENV_PATH/bin/python"

CONTROLLER="scripts/110_orchestrate_sr_v2_spatial_sensitivity.py"

set +e
"$VENV_PATH/bin/python" "$CONTROLLER" benchmark-run
BENCHMARK_RC=$?
if [ "$BENCHMARK_RC" -eq 0 ]; then
  "$VENV_PATH/bin/python" "$CONTROLLER" benchmark-validate
  BENCHMARK_RC=$?
fi
set -e

if [ "$BENCHMARK_RC" -ne 0 ]; then
  "$VENV_PATH/bin/python" "$CONTROLLER" benchmark-hold \
    --reason "benchmark_rc_${BENCHMARK_RC}" || true
  echo "benchmark_status=failed rc=$BENCHMARK_RC" >&2
  exit "$BENCHMARK_RC"
fi

echo "benchmark_status=passed"
