#!/bin/bash
# Run the paper's simplest baseline comparison.
#
# The paper's most important baseline for the core claim is the Gauss-Newton
# Hessian approximation on the pendulum sensitivity task. This script runs the
# pendulum evaluation and stores the resulting baseline/proposed metrics in a
# baseline artifact for inspection.

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

mkdir -p baseline

python3 - <<'PY'
import json
import sys
sys.path.insert(0, "/home/user/eval")
import evaluator

results = evaluator.run_pendulum_eval()
with open("/home/user/baseline/pendulum_gn_baseline.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
PY
