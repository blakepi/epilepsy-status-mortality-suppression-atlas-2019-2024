#!/bin/bash -l
# Stage the reviewed tree to scratch for the SR-v2 BYM2 spatial sensitivity.
#
# The scientific source envelope is verified by the reviewed Task 3 validator
# (validate_prepared_source_envelope), not here.  This script only puts the
# bytes in place and records a manifest so a stale scratch tree is visible.
set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
RUN_ID="sr-v2-spatial-sensitivity-20260818-v1"

base_args=()
if [ "$DRY_RUN" -eq 1 ]; then
  base_args+=(--dry-run)
fi
bash "$PROJECT_HOME/hpc/wahab/stage_to_scratch.sh" "${base_args[@]}"

# The prepared validator reads every one of these; a missing input must stop the
# launch here rather than after four chains have been queued.
required_paths=(
  "config/sr_v2_spatial_sensitivity_execution.yaml"
  "config/scientific_reports_v2_robustness_registry.yaml"
  "data/processed/bayes_constrained/model_frame.parquet"
  "outputs/scientific_reports_v2/production_8chain"
  "outputs/scientific_reports_v2/spatial_residual_diagnostics"
)

RSYNC_FLAGS=(-a --info=stats2)
if [ "$DRY_RUN" -eq 1 ]; then
  RSYNC_FLAGS+=(--dry-run)
fi

for relative in "${required_paths[@]}"; do
  source_path="$PROJECT_HOME/$relative"
  if [ ! -e "$source_path" ]; then
    echo "Missing required spatial-sensitivity staging input: $source_path" >&2
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
  manifest_relative="outputs/scientific_reports_v2/spatial_sensitivity/$RUN_ID/staged_inputs_sha256.txt"
  mkdir -p "$PROJECT_SCRATCH/$(dirname "$manifest_relative")"
  (
    cd "$PROJECT_SCRATCH"
    find config hpc scripts src data \
      outputs/scientific_reports_v2/production_8chain \
      outputs/scientific_reports_v2/spatial_residual_diagnostics \
      -type f -print0 | sort -z | xargs -0 sha256sum > "$manifest_relative"
    sha256sum "$manifest_relative" | awk '{print $1}' > "$manifest_relative.sha256"
  )
  mkdir -p "$PROJECT_HOME/$(dirname "$manifest_relative")"
  rsync -a "$PROJECT_SCRATCH/$manifest_relative" "$PROJECT_SCRATCH/$manifest_relative.sha256" \
    "$PROJECT_HOME/$(dirname "$manifest_relative")/"
fi

echo "staged_spatial_sensitivity_to=$PROJECT_SCRATCH"
