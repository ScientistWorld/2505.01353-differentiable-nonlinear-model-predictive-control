#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script evaluates method output artifacts by running the evaluation
# Python module and writing scores to scoring/scores.json.
#
# OUTPUT CONTRACT: This script writes scoring/scores.json containing
# a JSON dict nested by experiment, matching reference.json structure.
#
# Usage:
#   ./evaluate.sh                    # evaluate with defaults

set -e

cd /home/user

export PYTHONNOUSERSITE=1

for dep_dir in /home/user/environment/vendor_py310/*; do
    if [ -d "${dep_dir}" ]; then
        export PYTHONPATH="${dep_dir}:${PYTHONPATH}"
    fi
done

CASADI_VENDOR_DIR="$(find /home/user/environment/vendor_py310 -maxdepth 1 -mindepth 1 -type d -name 'casadi-*' 2>/dev/null | head -n 1)"
if [ -n "${CASADI_VENDOR_DIR}" ]; then
    export LD_LIBRARY_PATH="${CASADI_VENDOR_DIR}/casadi:${LD_LIBRARY_PATH}"
fi

mkdir -p scoring

echo "=== Evaluating method output artifact ==="

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
