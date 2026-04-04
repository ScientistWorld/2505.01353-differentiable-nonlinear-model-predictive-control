#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and reproduces all
# experiments from the paper "Differentiable Nonlinear Model Predictive Control".
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is /home/user

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "=================================================="
echo "Reproducing: Differentiable Nonlinear MPC"
echo "=================================================="

# Build acados if not already built
if [ ! -f "${ACADOS_DIR}/lib/libacados.so" ]; then
    echo "Building acados..."
    bash scripts/download.sh
fi

# Run all experiments
echo ""
echo "=== Running Method ==="
bash scripts/method.sh

# Evaluate results
echo ""
echo "=== Evaluating Results ==="
bash scripts/evaluate.sh

echo ""
echo "=================================================="
echo "Reproduction complete!"
echo "Results: scoring/scores.json"
echo "=================================================="
