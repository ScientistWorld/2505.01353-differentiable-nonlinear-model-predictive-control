#!/bin/bash
# Run the paper's method using the packaged reproduction path.
#
# The authoritative method implementation lives in `method/run_reproduction.py`.
# It writes raw method metrics to checkpoints/reproduction_results.json, then
# the method-agnostic evaluator scores that artifact.

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

echo "=== Running differentiable NMPC reproduction ==="
python3 method/run_reproduction.py
bash scripts/evaluate.sh
echo "=== Method run complete ==="
