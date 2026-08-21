#!/bin/bash -l
#SBATCH --job-name=epi_sr_v2_spatial
#SBATCH --partition=main
#SBATCH --time=72:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --array=1-4%2
#SBATCH --output=logs/slurm/%x_%A_%a.out
#SBATCH --error=logs/slurm/%x_%A_%a.err
#SBATCH --signal=B:USR1@300

# One BYM2 chain per array task, two at a time.  All chain custody -- resuming
# from the exact prior state, RNG, counters and chunk inventory -- is enforced
# by the reviewed Task 3 runner; this file only starts it and preserves its
# exit status.
set -euo pipefail
PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
RUN_ID="sr-v2-spatial-sensitivity-20260818-v1"
EXTENSION_EPOCH="${SR_V2_EXTENSION_EPOCH:-0}"
mkdir -p "$PROJECT_HOME/logs/slurm" "$PROJECT_SCRATCH/logs/slurm"
trap 'status=$?; bash "$PROJECT_SCRATCH/hpc/wahab/sync_sr_v2_spatial_sensitivity_results_home.sh" || true; exit $status' EXIT

case "$EXTENSION_EPOCH" in
  0|1|2|3) ;;
  *) echo "SR_V2_EXTENSION_EPOCH must be an exact integer in 0..3" >&2; exit 64 ;;
esac

cd "$PROJECT_SCRATCH"
export PYTHONPATH="$PROJECT_SCRATCH/src"
export MPLBACKEND=Agg
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

echo "hostname=$(hostname)"
echo "date=$(date -Is)"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID:-}"
echo "extension_epoch=$EXTENSION_EPOCH"

CONTROLLER="scripts/110_orchestrate_sr_v2_spatial_sensitivity.py"

# Throttling means chains 3 and 4 start after 1 and 2 have already advanced, so
# authority is checked per chain against its own exact prior epoch rather than
# against whichever status happens to be newest.
if [ "$EXTENSION_EPOCH" -ne 0 ]; then
  "$VENV_PATH/bin/python" "$CONTROLLER" chain-authorize \
    --chain-id "$SLURM_ARRAY_TASK_ID" --to-epoch "$EXTENSION_EPOCH"
fi

# Cooperative checkpoint: the runner exits 75 when it stops early on USR1, which
# is a resumable state and must not be reported as a chain failure.
set +e
"$VENV_PATH/bin/python" scripts/107_run_sr_v2_spatial_sensitivity_chain.py \
  --run-id "$RUN_ID" \
  --array-index "$SLURM_ARRAY_TASK_ID" \
  --extension-epoch "$EXTENSION_EPOCH" &
CHAIN_PID=$!
trap 'kill -USR1 "$CHAIN_PID" 2>/dev/null || true' USR1
wait "$CHAIN_PID"
CHAIN_RC=$?
set -e

if [ "$CHAIN_RC" -eq 75 ]; then
  echo "chain_status=checkpointed array_index=$SLURM_ARRAY_TASK_ID"
else
  echo "chain_status=exit_${CHAIN_RC} array_index=$SLURM_ARRAY_TASK_ID"
fi
exit "$CHAIN_RC"
