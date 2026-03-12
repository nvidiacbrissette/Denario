#!/usr/bin/env bash

set -euo pipefail

# Creates/uses a virtual environment and installs Denario + dependencies
# from this repository so "import denario" works locally.

VENV_DIR="${1:-.venv}"
PY_BIN="${DENARIO_PYTHON_BIN:-python3}"
PYPI_EXTRA_INDEX_URL="${PYPI_EXTRA_INDEX_URL:-https://pypi.org/simple}"

if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "Error: ${PY_BIN} is not installed or not on PATH."
  exit 1
fi

if command -v python3.12 >/dev/null 2>&1; then
  PY_BIN="${DENARIO_PYTHON_BIN:-python3.12}"
fi

PY_VERSION="$("${PY_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! "${PY_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Error: Denario setup requires Python >= 3.11. Found ${PY_VERSION}."
  exit 1
fi

if ! "${PY_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "Warning: Python ${PY_VERSION} detected. Python 3.12 is recommended for best dependency compatibility."
fi

echo "Using virtual environment: ${VENV_DIR}"
"${PY_BIN}" -m venv "${VENV_DIR}"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip setuptools wheel

if ! python -m pip install -r requirements.txt; then
  echo ""
  echo "Primary requirements install failed. Retrying with PyPI as extra index:"
  echo "  ${PYPI_EXTRA_INDEX_URL}"
  if ! python -m pip install --extra-index-url "${PYPI_EXTRA_INDEX_URL}" -r requirements.txt; then
    echo ""
    echo "Requirements install failed after retry."
    echo "Common causes:"
    echo "  1) Python version too old for one or more dependencies."
    echo "  2) Your package index mirror is missing required packages."
    echo ""
    echo "Try again with Python 3.12:"
    echo "  DENARIO_PYTHON_BIN=python3.12 bash setup_env.sh"
    echo ""
    echo "Or specify an alternate extra index:"
    echo "  PYPI_EXTRA_INDEX_URL=https://pypi.org/simple bash setup_env.sh"
    exit 1
  fi
fi

python -m pip install -e . --no-deps

# Optional FutureHouse features (non-fatal if unavailable on mirror/index)
if [ -f requirements-optional.txt ]; then
  if ! python -m pip install -r requirements-optional.txt; then
    echo ""
    echo "Optional dependencies were not installed."
    echo "FutureHouse features may be unavailable in this environment."
  fi
fi

echo ""
echo "Running sanity checks..."
python -c "import denario; print('denario import OK')"
python -m pip show denario >/dev/null && echo "denario package installed in this venv"

echo ""
echo "Setup complete."
echo "Activate later with:"
echo "  source ${VENV_DIR}/bin/activate"
