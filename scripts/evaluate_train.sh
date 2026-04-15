#!/bin/bash
# Train-slice evaluation entry point.
#
# Mirrors scripts/evaluate.sh: read the pre-generated method results artifact
# and write a scoring JSON, without importing method code.

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
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

echo "=== Evaluating train slice ==="

python3 -c "
import sys
sys.path.insert(0, '/home/user/eval/train')
import evaluator
evaluator.evaluate_all()
"

echo ''
echo '=== Train evaluation complete ==='
echo 'Results written to scoring/scores_train.json'
