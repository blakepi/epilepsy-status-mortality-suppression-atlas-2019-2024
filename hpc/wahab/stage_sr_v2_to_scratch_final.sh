#!/bin/bash -l
set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"

args=()
if [ "$DRY_RUN" -eq 1 ]; then
  args+=(--dry-run)
fi
bash "$PROJECT_HOME/hpc/wahab/stage_sr_v2_to_scratch.sh" "${args[@]}"

relative="outputs/scientific_reports_v2/calibration_pilot/replicate_001_extended"
source_path="$PROJECT_HOME/$relative"
if [ ! -d "$source_path" ]; then
  echo "Missing tuned calibration-extension evidence: $source_path" >&2
  exit 1
fi
mkdir -p "$PROJECT_SCRATCH/$relative"
rsync_flags=(-a --info=stats2)
if [ "$DRY_RUN" -eq 1 ]; then
  rsync_flags+=(--dry-run)
fi
rsync "${rsync_flags[@]}" "$source_path/" "$PROJECT_SCRATCH/$relative/"

if [ "$DRY_RUN" -eq 0 ]; then
  manifest="$PROJECT_SCRATCH/outputs/scientific_reports_v2/production_8chain/sr_v2_staged_evidence_sha256.txt"
  (
    cd "$PROJECT_SCRATCH"
    find \
      outputs/scientific_reports_v2/exact_kernel_validation \
      outputs/scientific_reports_v2/random_exact_validation \
      outputs/scientific_reports_v2/constraint_geometry \
      outputs/scientific_reports_v2/extended_joint_pilot \
      outputs/scientific_reports_v2/calibration_design_smoke \
      outputs/scientific_reports_v2/calibration_pilot/replicate_001 \
      outputs/scientific_reports_v2/calibration_pilot/replicate_001_extended \
      outputs/scientific_reports_v2/production_8chain/config \
      -type f -print0 | sort -z | xargs -0 sha256sum > "$manifest"
  )
  rsync -a "$manifest" "$PROJECT_HOME/outputs/scientific_reports_v2/production_8chain/"
fi

echo "staged_final_sr_v2_to=$PROJECT_SCRATCH"
