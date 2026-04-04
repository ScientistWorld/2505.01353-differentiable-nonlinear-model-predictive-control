#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script evaluates the acados differentiable MPC experiments by running
# the evaluation Python module and writing scores to scoring/scores.json.
#
# OUTPUT CONTRACT: This script writes scoring/scores.json containing
# a JSON dict nested by experiment, matching reference.json structure.
#
# Usage:
#   ./evaluate.sh                    # evaluate with defaults

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}

mkdir -p scoring

echo "=== Evaluating acados differentiable MPC ==="

# Run evaluation using the eval module
python3 -c "
import sys
sys.path.insert(0, '/home/user/eval')
import evaluator
results = evaluator.evaluate_all()
"

echo ''
echo '=== Evaluation complete ==='
echo 'Results written to scoring/scores.json'
