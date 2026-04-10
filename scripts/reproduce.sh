#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and reproduces the
# packaged experiments for this workspace: the core pendulum sensitivity
# claim plus the reduced-scale bounded-LQR timing benchmark.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - acados is cloned in method/acados
#   - Working directory is /home/user
#
# This is the "gold standard" entry point for this packaged environment.

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

echo "=================================================="
echo "Reproducing: Differentiable Nonlinear MPC"
echo "Paper: 2505.01353"
echo "=================================================="

# Run all method experiments and score their raw result artifact.
echo ""
echo "=== Running Method ==="
bash scripts/method.sh

echo ""
echo "=================================================="
echo "Reproduction complete!"
echo "Results: scoring/scores.json"
echo "Compare: python3 validate.py --compare"
echo "=================================================="
