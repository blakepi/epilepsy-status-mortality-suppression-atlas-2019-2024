#!/bin/bash -l
set -euo pipefail

PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
YES=0
if [ "${1:-}" = "--yes" ]; then
  YES=1
fi
if [ ! -d "$PROJECT_SCRATCH" ]; then
  echo "Scratch directory does not exist: $PROJECT_SCRATCH"
  exit 0
fi
echo "This removes temporary scratch files only after results have been synced: $PROJECT_SCRATCH"
if [ "$YES" -ne 1 ]; then
  read -r -p "Type yes to remove scratch project directory: " answer
  if [ "$answer" != "yes" ]; then
    echo "Cancelled."
    exit 1
  fi
fi
case "$PROJECT_SCRATCH" in
  /scratch/pierpogb/EpilepsyMortalityOptionB) rm -rf "$PROJECT_SCRATCH" ;;
  *) echo "Refusing to clean unexpected scratch path: $PROJECT_SCRATCH"; exit 2 ;;
esac
echo "scratch_cleaned=1"
