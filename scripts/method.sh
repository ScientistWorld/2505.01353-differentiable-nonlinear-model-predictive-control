#!/bin/bash
# Run the paper's method using the packaged reproduction path.
#
# The authoritative implementation for this workspace lives in `eval/evaluator.py`,
# which reproduces the paper's core Section 5.1 claim and a reduced-scale
# Section 5.2 timing benchmark with the acados sensitivity workflow.

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "=== Running differentiable NMPC reproduction ==="
bash scripts/evaluate.sh
echo "=== Method run complete ==="
