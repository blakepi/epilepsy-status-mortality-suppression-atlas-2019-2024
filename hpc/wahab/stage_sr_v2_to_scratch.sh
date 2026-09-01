#!/bin/bash -l
set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"

base_args=()
if [ "$DRY_RUN" -eq 1 ]; then
  base_args+=(--dry-run)
fi
bash "$PROJECT_HOME/hpc/wahab/stage_to_scratch.sh" "${base_args[@]}"

required_paths=(
  "outputs/scientific_reports_v2/exact_kernel_validation"
  "outputs/scientific_reports_v2/random_exact_validation"
  "outputs/scientific_reports_v2/constraint_geometry"
  "outputs/scientific_reports_v2/extended_joint_pilot"
  "outputs/scientific_reports_v2/calibration_design_smoke"
  "outputs/scientific_reports_v2/calibration_pilot/replicate_001"
  "outputs/scientific_reports_v2/production_8chain/config"
  "outputs/scientific_reports_v2/production_8chain/production_preparation_manifest.json"
)

RSYNC_FLAGS=(-a --info=stats2)
if [ "$DRY_RUN" -eq 1 ]; then
  RSYNC_FLAGS+=(--dry-run)
fi

for relative in "${required_paths[@]}"; do
  source_path="$PROJECT_HOME/$relative"
  if [ ! -e "$source_path" ]; then
    echo "Missing required Scientific Reports v2 staging input: $source_path" >&2
    exit 1
  fi
  destination_parent="$PROJECT_SCRATCH/$(dirname "$relative")"
  mkdir -p "$destination_parent"
  if [ -d "$source_path" ]; then
    mkdir -p "$PROJECT_SCRATCH/$relative"
    rsync "${RSYNC_FLAGS[@]}" "$source_path/" "$PROJECT_SCRATCH/$relative/"
  else
    rsync "${RSYNC_FLAGS[@]}" "$source_path" "$destination_parent/"
  fi
done

if [ "$DRY_RUN" -eq 0 ]; then
  manifest="$PROJECT_SCRATCH/outputs/scientific_reports_v2/production_8chain/sr_v2_staged_evidence_sha256.txt"
  mkdir -p "$(dirname "$manifest")"
  (
    cd "$PROJECT_SCRATCH"
    find \
      outputs/scientific_reports_v2/exact_kernel_validation \
      outputs/scientific_reports_v2/random_exact_validation \
      outputs/scientific_reports_v2/constraint_geometry \
      outputs/scientific_reports_v2/extended_joint_pilot \
      outputs/scientific_reports_v2/calibration_design_smoke \
      outputs/scientific_reports_v2/calibration_pilot/replicate_001 \
      outputs/scientific_reports_v2/production_8chain/config \
      -type f -print0 | sort -z | xargs -0 sha256sum > "$manifest"
  )
  rsync -a "$manifest" "$PROJECT_HOME/outputs/scientific_reports_v2/production_8chain/"
fi

echo "staged_sr_v2_to=$PROJECT_SCRATCH"
