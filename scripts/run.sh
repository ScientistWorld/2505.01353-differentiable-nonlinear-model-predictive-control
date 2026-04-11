#!/bin/bash
# Job script for acados differentiable MPC reproduction.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available (if requested)
#   - No internet access on compute node
#
# All required source trees, generated assets, and Python packages must be
# prepared before submission. This script only runs the evaluation payload.

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONNOUSERSITE=1
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

for dep_dir in /home/user/environment/vendor_py310/*; do
    if [ -d "${dep_dir}" ]; then
        export PYTHONPATH="${dep_dir}:${PYTHONPATH}"
    fi
done

CASADI_VENDOR_DIR="$(find /home/user/environment/vendor_py310 -maxdepth 1 -mindepth 1 -type d -name 'casadi-*' 2>/dev/null | head -n 1)"
if [ -n "${CASADI_VENDOR_DIR}" ]; then
    export LD_LIBRARY_PATH="${CASADI_VENDOR_DIR}/casadi:${LD_LIBRARY_PATH}"
fi

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - EVALUATE"
echo "========================================"
echo "ACADOS_SOURCE_DIR=${ACADOS_SOURCE_DIR}"
echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
echo "PYTHONNOUSERSITE=${PYTHONNOUSERSITE}"
echo "CASADI_VENDOR_DIR=${CASADI_VENDOR_DIR:-}"

if [ ! -f "${ACADOS_SOURCE_DIR}/lib/libacados.so" ]; then
    echo "ERROR: missing ${ACADOS_SOURCE_DIR}/lib/libacados.so"
    exit 1
fi

if [ ! -x "${ACADOS_SOURCE_DIR}/bin/t_renderer" ]; then
    echo "ERROR: missing executable ${ACADOS_SOURCE_DIR}/bin/t_renderer"
    exit 1
fi

echo ""
echo ">>> Verifying runtime Python imports..."
python3 - <<'PY'
import sys
import traceback

sys.path.insert(0, "/home/user/method")
from bootstrap_runtime import ensure_casadi_importable

print(f"python={sys.executable}")
print(f"version={sys.version}")
print(f"sys.path[:12]={sys.path[:12]}")
try:
    casadi = ensure_casadi_importable()
except Exception as exc:
    print(f"casadi_bootstrap_failed={exc.__class__.__name__}: {exc}")
    traceback.print_exc()
    raise
print(f"casadi_file={getattr(casadi, '__file__', None)}")
print(
    "casadi_symbols="
    f"{all(hasattr(casadi, name) for name in ('MX', 'SX', 'Function'))}"
)
PY

echo ""
echo ">>> Rebuilding acados in Release mode..."
bash /home/user/scripts/build_acados.sh

echo ""
echo ">>> Verifying acados shared-library linkage..."
python3 - <<'PY'
import ctypes

lib_path = "/home/user/method/acados/lib/libacados.so"
ctypes.CDLL(lib_path)
print(f"ctypes_loaded={lib_path}")
PY

echo ""
echo ">>> Running reproduction and evaluation..."
bash /home/user/scripts/reproduce.sh

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "Results in scoring/scores.json"
echo "========================================"
