#!/bin/bash
# Job script for acados differentiable MPC reproduction.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available (if requested)
#   - No internet access on compute node
#
# All required source trees, generated assets, and Python packages must be
# prepared before submission. This script only runs the evaluation payload.

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - EVALUATE"
echo "========================================"
echo "ACADOS_SOURCE_DIR=${ACADOS_SOURCE_DIR}"
echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"

if [ ! -f "${ACADOS_SOURCE_DIR}/lib/libacados.so" ]; then
    echo "ERROR: missing ${ACADOS_SOURCE_DIR}/lib/libacados.so"
    exit 1
fi

if [ ! -x "${ACADOS_SOURCE_DIR}/bin/t_renderer" ]; then
    echo "ERROR: missing executable ${ACADOS_SOURCE_DIR}/bin/t_renderer"
    exit 1
fi

echo ""
echo ">>> Rebuilding acados in Release mode..."
mkdir -p "${ACADOS_SOURCE_DIR}/build"
cd "${ACADOS_SOURCE_DIR}/build"
cmake -DACADOS_WITH_QPOASES=ON \
      -DACADOS_WITH_OSQP=OFF \
      -DACADOS_WITH_HPIPM=ON \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_BUILD_TYPE=Release \
      -DACADOS_EXTERNAL_HPMPC=OFF \
      ..
make install -j"$(nproc)"

cd /home/user

echo ""
echo ">>> Running evaluation..."
bash /home/user/scripts/evaluate.sh

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "Results in scoring/scores.json"
echo "========================================"
