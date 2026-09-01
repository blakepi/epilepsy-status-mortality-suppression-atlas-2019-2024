#!/bin/bash -l
# Copy the spatial-sensitivity run tree and its Slurm logs back to $PROJECT_HOME.
#
# This is transport only.  Immutability, no-clobber publication, chain custody
# and the gate are enforced by the reviewed Task 3 code that produced these
# files; re-implementing those checks here would duplicate reviewed logic in a
# second language.  --delete is deliberately not offered: the home copy is the
# durable record and must never be pruned by a transport script.
set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "Unsupported argument: $arg" >&2; exit 64 ;;
  esac
done

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
RUN_ID="sr-v2-spatial-sensitivity-20260818-v1"
RELATIVE_ROOT="outputs/scientific_reports_v2/spatial_sensitivity/$RUN_ID"
mkdir -p "$PROJECT_HOME/$RELATIVE_ROOT"

RSYNC_FLAGS=(-a --info=stats2)
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

echo "synced_spatial_sensitivity_to=$PROJECT_HOME/$RELATIVE_ROOT"
