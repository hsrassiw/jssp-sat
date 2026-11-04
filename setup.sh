#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python_bin="${JSSP_PYTHON:-python3.12}"
"$python_bin" -c 'import sys; assert sys.version_info[:2] == (3,12), "Use Python 3.12"'
"$python_bin" -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools
.venv/bin/python -m pip install -r requirements-lam.txt
if [[ -n "${CPLEX_STUDIO_DIR:-}" ]]; then
  if [[ -z "${CPLEX_PY_VERSION:-}" ]]; then
    echo 'Set CPLEX_PY_VERSION to match your installed CPLEX Studio.' >&2
    exit 2
  fi
  .venv/bin/python -m pip install "cplex==$CPLEX_PY_VERSION"
  .venv/bin/docplex config --upgrade "$CPLEX_STUDIO_DIR"
  .venv/bin/python scripts/check_solvers.py --full --solvers cplex
fi
printf '%s\n' 'Environment ready. Activate: source .venv/bin/activate' \
  'Copy your WLS license to ~/gurobi.lic or set GRB_LICENSE_FILE.' \
  'Validate: python scripts/check_solvers.py --full' \
  'CPLEX full install is required before official experiments.'
