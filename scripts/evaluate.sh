#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script evaluates the acados differentiable MPC experiments by:
# 1. Running the method scripts
# 2. Reading the output JSON files
# 3. Writing scores to scoring/scores.json
#
# OUTPUT CONTRACT: This script writes scoring/scores.json containing
# a JSON dict nested by experiment.
#
# Usage:
#   ./evaluate.sh                    # evaluate with defaults
#   ./evaluate.sh pendulum           # evaluate specific experiment

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

mkdir -p scoring

echo "=== Evaluating acados differentiable MPC ==="

# Run evaluation using the eval module
python3 -c "
import sys
sys.path.insert(0, '/home/user/eval')
import evaluator
results = evaluator.evaluate_all()
print('Evaluation results:')
for k, v in results.items():
    print(f'  {k}: {v}')
"

echo ''
echo '=== Scores written to scoring/scores.json ==='
