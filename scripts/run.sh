#!/bin/bash
# Job script for acados differentiable MPC reproduction.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available (if requested)
#   - No internet access on compute node
#
# Steps:
# 1. Build acados from source (with submodule fetch on login/build node)
# 2. Install Python packages
# 3. Run the pendulum OCP sensitivity experiment (core claim)

set -e

cd /home/user

export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH}

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - BUILD + RUN"
echo "========================================"
echo "ACADOS_SOURCE_DIR=${ACADOS_SOURCE_DIR}"
echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"

# Step 1: Build acados
echo ""
echo ">>> Step 1: Building acados..."
if [ -f "${ACADOS_SOURCE_DIR}/lib/libacados.so" ]; then
    echo "acados already built (libacados.so found)"
else
    echo "Building acados from source..."

    if [ ! -d "${ACADOS_SOURCE_DIR}" ]; then
        echo "ERROR: acados not found at ${ACADOS_SOURCE_DIR}"
        ls /home/user/method/
        exit 1
    fi

    cd "${ACADOS_SOURCE_DIR}"

    # Fetch submodules (blasfeo, hpipm, qpoases, etc.)
    echo "Fetching git submodules..."
    git submodule update --recursive --init || {
        echo "WARNING: git submodule update failed, trying individual clones..."
        # Try to clone required submodules individually
        if [ ! -d "external/blasfeo" ] || [ ! -f "external/blasfeo/CMakeLists.txt" ]; then
            echo "Cloning blasfeo..."
            rm -rf external/blasfeo
            git clone --depth 1 https://github.com/giaf/blasfeo.git external/blasfeo || true
        fi
        if [ ! -d "external/hpipm" ] || [ ! -f "external/hpipm/CMakeLists.txt" ]; then
            echo "Cloning hpipm..."
            rm -rf external/hpipm
            git clone --depth 1 --branch stable https://github.com/giaf/hpipm.git external/hpipm || true
        fi
        if [ ! -d "external/qpoases" ] || [ ! -f "external/qpoases/src/qpOASES.cpp" ]; then
            echo "Cloning qpoases..."
            rm -rf external/qpoases
            git clone --depth 1 https://github.com/acados/qpOASES.git external/qpoases || true
        fi
        # Initialize submodules recursively
        git submodule update --recursive --init || true
    }

    # Download t_renderer binaries
    TERA_DIR="${ACADOS_SOURCE_DIR}/bin/t_renderer"
    mkdir -p "${TERA_DIR}"
    ARCH=$(uname -m)
    case "${ARCH}" in
        x86_64) TERA_ARCH="linux64" ;;
        aarch64) TERA_ARCH="linux-arm64" ;;
        *) echo "Unknown arch: ${ARCH}"; exit 1 ;;
    esac
    TERA_URL="https://github.com/acados/tera_renderer/releases/download/v0.0.41/t_renderer_${TERA_ARCH}"
    if [ ! -f "${TERA_DIR}/t_renderer" ]; then
        echo "Downloading t_renderer..."
        curl -sSL "${TERA_URL}" -o "${TERA_DIR}/t_renderer" || {
            echo "WARNING: t_renderer download failed"
        }
        chmod +x "${TERA_DIR}/t_renderer" 2>/dev/null || true
    fi

    # Build acados
    echo "Running cmake..."
    mkdir -p build
    cd build
    cmake -DACADOS_WITH_QPOASES=ON \
          -DACADOS_WITH_OSQP=OFF \
          -DACADOS_WITH_HPIPM=ON \
          -DBUILD_SHARED_LIBS=ON \
          -DACADOS_EXTERNAL_HPMPC=OFF \
          ..
    echo "Building acados..."
    make install -j4
    cd /home/user
fi

echo "acados build complete."
ls -la ${ACADOS_SOURCE_DIR}/lib/ 2>/dev/null || echo "lib dir not found"

# Step 2: Install Python packages
echo ""
echo ">>> Step 2: Installing Python packages..."
pip3 install numpy scipy matplotlib casadi 2>/dev/null || \
pip install numpy scipy matplotlib casadi 2>/dev/null || \
echo "WARNING: pip install failed, trying uv..."
uv pip install --system numpy scipy matplotlib casadi 2>/dev/null || true

# Install acados_template
if [ -d "${ACADOS_SOURCE_DIR}/interfaces/acados_template" ]; then
    echo "Installing acados_template..."
    cd "${ACADOS_SOURCE_DIR}/interfaces/acados_template"
    pip3 install -e . 2>/dev/null || pip install -e . 2>/dev/null || \
    uv pip install --system -e . 2>/dev/null || true
    cd /home/user
fi

# Verify key imports
echo ""
echo ">>> Verifying installations..."
python3 -c "import casadi; print(f'casadi {casadi.__version__} OK')" 2>/dev/null || \
python3 -c "import casadi; print('casadi OK')" 2>/dev/null || \
echo "WARNING: casadi import failed"

# Step 3: Run pendulum experiment (core claim - Section 5.1)
echo ""
echo ">>> Step 3: Running Pendulum OCP Sensitivity (Section 5.1 - Core Claim)..."
if [ -f method/pendulum_sensitivity.py ]; then
    python3 method/pendulum_sensitivity.py 2>&1
else
    echo "pendulum_sensitivity.py not found, using evaluator..."
fi

# Step 4: Evaluate
echo ""
echo ">>> Step 4: Evaluating results..."
python3 -c "
import sys
sys.path.insert(0, '/home/user/eval')
import evaluator
evaluator.evaluate_all()
" 2>&1

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "Results in scoring/scores.json"
echo "========================================"
