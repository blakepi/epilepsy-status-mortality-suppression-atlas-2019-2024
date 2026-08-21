#!/bin/bash -l
# Resume the SR-v2 BYM2 run: either retry the chains that did not finish this
# epoch, or start a reviewed convergence-only extension epoch.
#
#   resume_sr_v2_spatial_sensitivity.sh --retry            --epoch N
#   resume_sr_v2_spatial_sensitivity.sh --extend-to-epoch  N
#
# Which chains may run, and whether an extension is authorized at all, are
# decided by the reviewed Task 3 validators through the controller.  This script
# never chooses chains itself.
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
RUN_ID="sr-v2-spatial-sensitivity-20260818-v1"
RELATIVE_ROOT="outputs/scientific_reports_v2/spatial_sensitivity/$RUN_ID"
CONTROLLER="scripts/110_orchestrate_sr_v2_spatial_sensitivity.py"

MODE=""
EPOCH=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --retry) MODE="retry"; shift ;;
    --epoch) EPOCH="${2:-}"; shift 2 ;;
    --extend-to-epoch) MODE="extend"; EPOCH="${2:-}"; shift 2 ;;
    *) echo "Unsupported argument: $1" >&2; exit 64 ;;
  esac
done
case "$MODE" in retry|extend) ;; *) echo "Specify --retry --epoch N or --extend-to-epoch N" >&2; exit 64 ;; esac
case "$EPOCH" in 0|1|2|3) ;; *) echo "Epoch must be an exact integer in 0..3" >&2; exit 64 ;; esac
if [ "$MODE" = "extend" ] && [ "$EPOCH" = "0" ]; then
  echo "An extension epoch must be in 1..3" >&2
  exit 64
fi

cd "$PROJECT_SCRATCH"
export PYTHONPATH="$PROJECT_SCRATCH/src"
mkdir -p logs/slurm "$RELATIVE_ROOT"

if [ "$MODE" = "extend" ]; then
  # Refuses unless a reviewed convergence-only authorization exists for exactly
  # this epoch transition.
  "$VENV_PATH/bin/python" "$CONTROLLER" extension-authorize --to-epoch "$EPOCH" >/dev/null
  ARRAY_SPEC="1-4"
else
  set +e
  ARRAY_SPEC="$("$VENV_PATH/bin/python" "$CONTROLLER" retry-select --extension-epoch "$EPOCH")"
  SELECT_RC=$?
  set -e
  if [ "$SELECT_RC" -eq 3 ]; then
    echo "resume_status=nothing_to_do extension_epoch=$EPOCH"
    exit 0
  fi
  if [ "$SELECT_RC" -ne 0 ]; then
    echo "retry selector refused (rc=$SELECT_RC)" >&2
    exit "$SELECT_RC"
  fi
fi

chain_job="$(sbatch --parsable --array="${ARRAY_SPEC}%2" \
  --export=ALL,SR_V2_EXTENSION_EPOCH="$EPOCH" \
  hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch)"
finalize_job="$(sbatch --parsable --dependency="afterok:${chain_job}" \
  --export=ALL,SR_V2_EXTENSION_EPOCH="$EPOCH" \
  hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch)"

submitted_at="$(date -Is)"
record="$PROJECT_HOME/$RELATIVE_ROOT/submitted_jobs.tsv"
mkdir -p "$(dirname "$record")"
if [ ! -e "$record" ]; then
  printf 'submitted_at\tstage\tjob_id\tdependency\tscript\n' > "$record"
fi
printf '%s\t%s_epoch%s_array_%s\t%s\t\t%s\n' \
  "$submitted_at" "$MODE" "$EPOCH" "$ARRAY_SPEC" "$chain_job" \
  "hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch" >> "$record"
printf '%s\t%s_epoch%s_finalize\t%s\tafterok:%s\t%s\n' \
  "$submitted_at" "$MODE" "$EPOCH" "$finalize_job" "$chain_job" \
  "hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch" >> "$record"

echo "resume_mode=$MODE"
echo "extension_epoch=$EPOCH"
echo "array_spec=$ARRAY_SPEC"
echo "chain_job=$chain_job"
echo "finalize_job=$finalize_job"
