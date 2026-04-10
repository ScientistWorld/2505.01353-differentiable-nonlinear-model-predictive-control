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
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "=== Running differentiable NMPC reproduction ==="
python3 method/run_reproduction.py
bash scripts/evaluate.sh
echo "=== Method run complete ==="
