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
mkdir -p "$PROJECT_HOME/outputs/bayes_constrained/hpc"

RSYNC_FLAGS=(-a --info=stats2)
if [ -n "$DELETE_FLAG" ]; then
  RSYNC_FLAGS+=("$DELETE_FLAG")
fi
if [ "$DRY_RUN" -eq 1 ]; then
  RSYNC_FLAGS+=(--dry-run)
fi

for item in outputs/bayes_constrained outputs/bayes_constrained/hpc tables figures manuscript supplement RUN_BAYES_CONSTRAINED_REPORT.md logs/slurm; do
  if [ -e "$PROJECT_SCRATCH/$item" ]; then
    mkdir -p "$PROJECT_HOME/$(dirname "$item")"
    rsync "${RSYNC_FLAGS[@]}" "$PROJECT_SCRATCH/$item" "$PROJECT_HOME/$(dirname "$item")/"
  fi
done

echo "synced_results_to=$PROJECT_HOME"
