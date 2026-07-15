#!/bin/bash -l
set -euo pipefail

PROJECT_HOME="${PROJECT_HOME:-/home/pierpogb/EpilepsyMortalityOptionB}"
VENV_PATH="${VENV_PATH:-/home/pierpogb/.venvs/epimort_bayes}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_HOME"
mkdir -p wheelhouse
if [ -x "$VENV_PATH/bin/python" ]; then
  PYTHON_BIN="$VENV_PATH/bin/python"
fi
"$PYTHON_BIN" -m pip download -r requirements-bayes.txt -d wheelhouse
echo "wheelhouse=$(pwd)/wheelhouse"
