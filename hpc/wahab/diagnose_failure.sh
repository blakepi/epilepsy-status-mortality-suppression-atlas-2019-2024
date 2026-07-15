#!/bin/bash -l
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
cd "$PROJECT_HOME"
mkdir -p outputs/bayes_constrained/hpc
REPORT="outputs/bayes_constrained/hpc/failure_diagnosis.md"
{
  echo "# Wahab Failure Diagnosis"
  echo
  echo "Generated: $(date -Is)"
  echo
  echo "## Failed or Recent Slurm Error Logs"
  echo
  find logs/slurm -type f -name '*.err' -print 2>/dev/null | sort | while read -r log; do
    echo "### $log"
    tail -n 100 "$log" || true
    echo
  done
  echo "## Output Completeness"
  python scripts/hpc_wahab/check_outputs_complete.py --write-report || true
} > "$REPORT"
echo "failure_diagnosis=$REPORT"
