#!/bin/bash -l
#SBATCH --job-name=epi_sr_v2_spatial_final
#SBATCH --partition=timed-main
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=logs/slurm/%x_%j.out
#SBATCH --error=logs/slurm/%x_%j.err

# Merge the epoch, verify it from an isolated code path, publish the release
# manifest, then gate.  The order matters and is enforced inside the reviewed
# scripts: the gate is last and writes PASS only after every upstream hash and
# diagnostic agrees.
set -euo pipefail
PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
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
export MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

echo "hostname=$(hostname)"
echo "date=$(date -Is)"
echo "extension_epoch=$EXTENSION_EPOCH"

"$VENV_PATH/bin/python" scripts/108_merge_sr_v2_spatial_sensitivity.py \
  --extension-epoch "$EXTENSION_EPOCH"
"$VENV_PATH/bin/python" scripts/109_gate_sr_v2_spatial_sensitivity.py \
  --independent-verify --extension-epoch "$EXTENSION_EPOCH"
"$VENV_PATH/bin/python" scripts/109_gate_sr_v2_spatial_sensitivity.py \
  --write-release-manifest --extension-epoch "$EXTENSION_EPOCH"
"$VENV_PATH/bin/python" scripts/109_gate_sr_v2_spatial_sensitivity.py \
  --gate --extension-epoch "$EXTENSION_EPOCH"

echo "finalize_status=complete extension_epoch=$EXTENSION_EPOCH"
