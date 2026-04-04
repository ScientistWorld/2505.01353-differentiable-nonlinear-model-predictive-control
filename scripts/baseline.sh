#!/bin/bash
# Run baseline method from the paper.
#
# The paper compares against Gauss-Newton Hessian approximation (a common
# baseline in differentiable optimization). This baseline gives WRONG
# sensitivities - the paper shows this as a key pitfall (Remark 3).
#
# This baseline script runs the pendulum OCP with GAUSS_NEWTON Hessian
# to reproduce the paper's demonstration that this approach fails.
#
# Usage:
#   bash scripts/baseline.sh

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "=== Running Baseline (Gauss-Newton Hessian) ==="

python3 -c "
import sys
sys.path.insert(0, '/home/user/method')
import pendulum_sensitivity
# Just run the GN part
import numpy as np
pendulum_sensitivity.run_pendulum_experiment()
"

echo "Baseline run complete."
