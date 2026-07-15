#!/bin/bash -l
set -euo pipefail

MIDAS="${MIDAS:-pierpogb}"
PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
cd "$PROJECT_HOME"

echo "## squeue"
squeue -u "$MIDAS" || true
echo
echo "## submitted jobs"
cat outputs/bayes_constrained/hpc/submitted_jobs.tsv 2>/dev/null || true
echo
echo "## convergence gate"
cat outputs/bayes_constrained/hpc/convergence_gate.md 2>/dev/null || true
echo
echo "## chain status"
python - <<'PY' || true
import json
from pathlib import Path
for path in sorted(Path("outputs/bayes_constrained/hpc/chains").glob("chain_*/chain_status.json")):
    s=json.loads(path.read_text())
    print(path.parent.name, s.get("status"), s.get("mode"), s.get("iteration"), s.get("saved_draws"))
PY
echo
echo "## recent slurm logs"
find logs/slurm -type f \( -name '*.out' -o -name '*.err' \) -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -20 | cut -d' ' -f2- | xargs -r tail -n 20 || true
echo
echo "## disk usage"
du -sh "$PROJECT_HOME" "$PROJECT_SCRATCH" 2>/dev/null || true
echo
echo "## next recommended action"
python scripts/hpc_wahab/print_manual_next_steps.py
