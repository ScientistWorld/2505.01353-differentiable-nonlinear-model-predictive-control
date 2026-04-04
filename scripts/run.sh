#!/bin/bash
# Job script submitted via action.yaml.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available (if requested)
#   - No internet access
#
# Steps:
# 1. Build acados from source (download.sh)
# 2. Install Python packages (setup.sh)
# 3. Run the pendulum OCP sensitivity experiment (core claim)

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - BUILD + RUN"
echo "========================================"

# Step 1: Build acados
echo ""
echo ">>> Step 1: Building acados..."
if [ -f "${ACADOS_SOURCE_DIR}/lib/libacados.so" ]; then
    echo "acados already built, skipping..."
else
    bash scripts/download.sh
fi

# Step 2: Install Python packages
echo ""
echo ">>> Step 2: Installing Python packages..."
bash environment/setup.sh

# Step 3: Run pendulum experiment (core claim - Section 5.1)
echo ""
echo ">>> Step 3: Running Pendulum OCP Sensitivity (Section 5.1 - Core Claim)..."
python3 method/pendulum_sensitivity.py

# Step 4: Evaluate
echo ""
echo ">>> Step 4: Evaluating results..."
bash scripts/evaluate.sh

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "========================================"
