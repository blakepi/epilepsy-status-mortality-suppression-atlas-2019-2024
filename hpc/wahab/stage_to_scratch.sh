#!/bin/bash -l
set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"

mkdir -p "$PROJECT_SCRATCH" "$PROJECT_HOME/outputs/bayes_constrained/hpc"
RSYNC_FLAGS=(-a --info=stats2 --exclude='.git/' --exclude='.venv/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='.ruff_cache/' --exclude='*.tmp' --exclude='~$*' --exclude='Thumbs.db' --exclude='outputs/***' --exclude='logs/slurm/*.out' --exclude='logs/slurm/*.err')
if [ "$DRY_RUN" -eq 1 ]; then
  RSYNC_FLAGS+=(--dry-run)
fi

rsync "${RSYNC_FLAGS[@]}" "$PROJECT_HOME/" "$PROJECT_SCRATCH/"
mkdir -p "$PROJECT_SCRATCH/outputs/bayes_constrained/hpc" "$PROJECT_SCRATCH/logs/slurm"

if [ "$DRY_RUN" -eq 0 ]; then
  (
    cd "$PROJECT_SCRATCH"
    find config hpc scripts src data -type f -print0 | sort -z | xargs -0 sha256sum > outputs/bayes_constrained/hpc/scratch_manifest_sha256.txt
  )
  rsync -a "$PROJECT_SCRATCH/outputs/bayes_constrained/hpc/scratch_manifest_sha256.txt" "$PROJECT_HOME/outputs/bayes_constrained/hpc/"
fi

echo "staged_to=$PROJECT_SCRATCH"
