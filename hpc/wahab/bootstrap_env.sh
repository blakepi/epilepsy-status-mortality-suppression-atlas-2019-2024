#!/bin/bash -l
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
PROJECT_SCRATCH="${PROJECT_SCRATCH:-/scratch/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "bootstrap_env.sh is for login-node setup only; it does not run heavy modeling."
mkdir -p "$PROJECT_HOME" "$PROJECT_SCRATCH" "$PROJECT_HOME/logs/slurm" "$PROJECT_HOME/outputs/bayes_constrained/hpc" "$(dirname "$VENV_PATH")"
cd "$PROJECT_HOME"

if command -v enable_lmod >/dev/null 2>&1; then
  enable_lmod || true
fi

if type module >/dev/null 2>&1; then
  for module_name in python/3.11 python/3.10 python; do
    if module load "$module_name" >/dev/null 2>&1; then
      echo "Loaded module: $module_name"
      break
    fi
  done
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip setuptools wheel
if [ -d "$PROJECT_HOME/wheelhouse" ] && compgen -G "$PROJECT_HOME/wheelhouse/*.whl" >/dev/null; then
  python -m pip install --no-index --find-links "$PROJECT_HOME/wheelhouse" -r "$PROJECT_HOME/requirements-bayes.txt"
else
  python -m pip install -r "$PROJECT_HOME/requirements-bayes.txt"
fi

export PROJECT_HOME PROJECT_SCRATCH MPLBACKEND=Agg PYTHONPATH="$PROJECT_HOME"
python "$PROJECT_HOME/scripts/hpc_wahab/validate_wahab_env.py"
python - <<'PY'
import numpy, pandas, scipy, yaml
print("import_smoke=passed")
PY

echo "Environment ready at $VENV_PATH"
