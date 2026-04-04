#!/bin/bash
# Run the paper's method using acados.
#
# This script runs the acados differentiable MPC method:
# 1. Pendulum OCP sensitivity (Section 5.1 - core claim)
# 2. LQR benchmark (Section 5.2)
# 3. Chain of masses (Section 5.3)
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "=== Running acados differentiable MPC experiments ==="

# Run pendulum experiment (Section 5.1 - core claim)
echo ""
echo "=== Section 5.1: Pendulum OCP Sensitivity ==="
python3 method/pendulum_sensitivity.py

# Run LQR benchmark (Section 5.2)
echo ""
echo "=== Section 5.2: Bounded LQR Benchmark ==="
python3 method/lqr_benchmark.py

# Run chain experiment (Section 5.3)
echo ""
echo "=== Section 5.3: Chain of Masses ==="
python3 method/chain_sensitivity.py

echo ""
echo "=== Method run complete ==="
