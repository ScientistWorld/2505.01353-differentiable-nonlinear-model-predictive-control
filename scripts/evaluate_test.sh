#!/bin/bash
# Held-out test-slice evaluation entry point.
#
# Mirrors scripts/evaluate.sh: read the pre-generated method results artifact
# and write a scoring JSON, without importing method code.

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

echo "=== Evaluating held-out test slice ==="

python3 -c "
import sys
sys.path.insert(0, '/home/user/eval/test')
import evaluator
evaluator.evaluate_all()
"

echo ''
echo '=== Test evaluation complete ==='
echo 'Results written to scoring/scores_test.json'
