#!/bin/bash
# Download and build acados from source on the login node (internet available).
#
# Estimated total download size: ~50 MB (git clone + submodules)
# Estimated disk usage after build: ~2 GB
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs. MUST be run here (login node) because
# the compute node has no internet access.

set -e

cd /home/user

ACADOS_DIR="/home/user/method/acados"

# Check if acados is already cloned
if [ -d "${ACADOS_DIR}" ]; then
    echo "acados already cloned, updating submodules..."
    cd "${ACADOS_DIR}"
    git submodule update --recursive --init
else
    echo "Cloning acados repository with submodules..."
    git clone --recursive https://github.com/acados/acados.git "${ACADOS_DIR}"
    cd "${ACADOS_DIR}"
fi

# Download t_renderer binaries
TERA_DIR="${ACADOS_DIR}/bin/t_renderer"
mkdir -p "${TERA_DIR}"
ARCH=$(uname -m)
case "${ARCH}" in
    x86_64) TERA_ARCH="linux64" ;;
    aarch64) TERA_ARCH="linux-arm64" ;;
    *) echo "Unknown architecture: ${ARCH}"; exit 1 ;;
esac
TERA_URL="https://github.com/acados/tera_renderer/releases/download/v0.0.41/t_renderer_${TERA_ARCH}"
if [ ! -f "${TERA_DIR}/t_renderer" ]; then
    echo "Downloading t_renderer..."
    curl -sSL "${TERA_URL}" -o "${TERA_DIR}/t_renderer"
    chmod +x "${TERA_DIR}/t_renderer"
    echo "t_renderer installed"
else
    echo "t_renderer already present"
fi

# Build acados as shared library
echo "Building acados..."
mkdir -p "${ACADOS_DIR}/build"
cd "${ACADOS_DIR}/build"
cmake -DACADOS_WITH_QPOASES=ON \
      -DACADOS_WITH_OSQP=OFF \
      -DACADOS_WITH_HPIPM=ON \
      -DBUILD_SHARED_LIBS=ON \
      -DACADOS_EXTERNAL_HPMPC=OFF \
      ..
make install -j$(nproc)

echo "acados build complete."
echo "Library: ${ACADOS_DIR}/lib/"
ls -la ${ACADOS_DIR}/lib/

# Install Python packages
echo "Installing Python packages..."
pip3 install numpy scipy matplotlib casadi || pip install numpy scipy matplotlib casadi

# Install acados_template
echo "Installing acados_template..."
cd "${ACADOS_DIR}/interfaces/acados_template"
pip3 install -e . || pip install -e .
cd /home/user

echo ""
echo "=== Download + Build Complete ==="
echo "LD_LIBRARY_PATH should include: ${ACADOS_DIR}/lib"
