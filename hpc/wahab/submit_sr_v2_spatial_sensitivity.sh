#!/bin/bash -l
# Submit the SR-v2 BYM2 spatial-sensitivity DAG: benchmark -> 4 chains -> finalize.
#
# The benchmark runs first and everything downstream is afterok-dependent on it,
# so a run that cannot fit the cluster envelope never reaches the chain array.
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
RUN_ID="sr-v2-spatial-sensitivity-20260818-v1"
RELATIVE_ROOT="outputs/scientific_reports_v2/spatial_sensitivity/$RUN_ID"

LAUNCH_ENVELOPE="${LAUNCH_ENVELOPE:-}"
if [ -z "$LAUNCH_ENVELOPE" ] || [ ! -f "$LAUNCH_ENVELOPE" ]; then
  echo "LAUNCH_ENVELOPE must point at the reviewed launch envelope JSON" >&2
  exit 64
fi

cd "$PROJECT_HOME"
# Preparation runs from $PROJECT_HOME so the reviewed validator sees the tree
# the envelope was signed against, then that prepared tree is staged.
PYTHONPATH="$PROJECT_HOME/src" "$VENV_PATH/bin/python" \
  scripts/106_prepare_sr_v2_spatial_sensitivity.py --launch-envelope "$LAUNCH_ENVELOPE"
bash hpc/wahab/stage_sr_v2_spatial_sensitivity_to_scratch.sh

cd "$PROJECT_SCRATCH"
mkdir -p logs/slurm "$RELATIVE_ROOT"

benchmark_job="$(sbatch --parsable hpc/wahab/slurm/65_sr_v2_spatial_sensitivity_benchmark.sbatch)"
chain_job="$(sbatch --parsable --dependency="afterok:${benchmark_job}" \
  --export=ALL,SR_V2_EXTENSION_EPOCH=0 \
  hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch)"
finalize_job="$(sbatch --parsable --dependency="afterok:${chain_job}" \
  --export=ALL,SR_V2_EXTENSION_EPOCH=0 \
  hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch)"

submitted_at="$(date -Is)"
record="$PROJECT_HOME/$RELATIVE_ROOT/submitted_jobs.tsv"
mkdir -p "$(dirname "$record")"
if [ ! -e "$record" ]; then
  printf 'submitted_at\tstage\tjob_id\tdependency\tscript\n' > "$record"
fi
printf '%s\tbenchmark\t%s\t\t%s\n' \
  "$submitted_at" "$benchmark_job" "hpc/wahab/slurm/65_sr_v2_spatial_sensitivity_benchmark.sbatch" >> "$record"
printf '%s\tchain_array\t%s\tafterok:%s\t%s\n' \
  "$submitted_at" "$chain_job" "$benchmark_job" "hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch" >> "$record"
printf '%s\tfinalize\t%s\tafterok:%s\t%s\n' \
  "$submitted_at" "$finalize_job" "$chain_job" "hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch" >> "$record"

echo "benchmark_job=$benchmark_job"
echo "chain_job=$chain_job"
echo "finalize_job=$finalize_job"
echo "submission_record=$record"
