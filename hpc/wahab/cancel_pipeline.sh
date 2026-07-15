#!/bin/bash -l
set -euo pipefail

YES=0
if [ "${1:-}" = "--yes" ]; then
  YES=1
fi

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
MIDAS="${MIDAS:-pierpogb}"
cd "$PROJECT_HOME"
JOBS_TSV="outputs/bayes_constrained/hpc/submitted_jobs.tsv"
if [ ! -f "$JOBS_TSV" ]; then
  echo "No submitted_jobs.tsv found."
  exit 0
fi

mapfile -t JOBS < <(awk 'NR>1 {print $3}' "$JOBS_TSV" | sed 's/_.*//' | sort -u)
echo "Jobs to cancel for $MIDAS: ${JOBS[*]}"
if [ "$YES" -ne 1 ]; then
  read -r -p "Cancel these jobs only? Type yes: " answer
  if [ "$answer" != "yes" ]; then
    echo "Cancelled by user."
    exit 1
  fi
fi

for job in "${JOBS[@]}"; do
  if squeue -u "$MIDAS" -h -j "$job" >/dev/null 2>&1; then
    scancel "$job" || true
  fi
done
echo "cancel_requested=1"
