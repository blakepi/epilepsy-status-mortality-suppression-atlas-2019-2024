#!/bin/bash -l
set -euo pipefail

DELETE_FLAG=""
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --delete) DELETE_FLAG="--delete" ;;
    --dry-run) DRY_RUN=1 ;;
  esac
done

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
RELATIVE_ROOT="outputs/scientific_reports_v2/production_8chain"
mkdir -p "$PROJECT_HOME/$RELATIVE_ROOT"

RSYNC_FLAGS=(-a --info=stats2)
if [ -n "$DELETE_FLAG" ]; then
  RSYNC_FLAGS+=("$DELETE_FLAG")
fi
if [ "$DRY_RUN" -eq 1 ]; then
  RSYNC_FLAGS+=(--dry-run)
fi

if [ -e "$PROJECT_SCRATCH/$RELATIVE_ROOT" ]; then
  rsync "${RSYNC_FLAGS[@]}" \
    "$PROJECT_SCRATCH/$RELATIVE_ROOT/" \
    "$PROJECT_HOME/$RELATIVE_ROOT/"
fi
if [ -d "$PROJECT_SCRATCH/logs/slurm" ]; then
  mkdir -p "$PROJECT_HOME/logs/slurm"
  rsync "${RSYNC_FLAGS[@]}" \
    "$PROJECT_SCRATCH/logs/slurm/" \
    "$PROJECT_HOME/logs/slurm/"
fi

echo "synced_sr_v2_results_to=$PROJECT_HOME/$RELATIVE_ROOT"
