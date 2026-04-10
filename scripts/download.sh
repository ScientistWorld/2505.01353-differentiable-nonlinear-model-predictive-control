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

# Check if acados is already available. Some benchmark workspaces contain a
# pre-populated source tree without a nested .git directory, so only run git
# update commands when the directory is an actual checkout/submodule.
if [ -d "${ACADOS_DIR}/.git" ] || [ -f "${ACADOS_DIR}/.git" ]; then
    echo "acados checkout already present, updating submodules..."
    cd "${ACADOS_DIR}"
    git submodule update --recursive --init
elif [ -f "${ACADOS_DIR}/CMakeLists.txt" ]; then
    echo "Using existing acados source tree at ${ACADOS_DIR}"
    cd "${ACADOS_DIR}"
else
    echo "Initializing acados submodule..."
    git submodule sync -- method/acados || true
    git submodule update --init --recursive method/acados || {
        echo "Submodule init failed; cloning acados repository directly..."
        rm -rf "${ACADOS_DIR}"
        git clone --recursive https://github.com/acados/acados.git "${ACADOS_DIR}"
    }
    cd "${ACADOS_DIR}"
fi

# Download t_renderer binary
mkdir -p "${ACADOS_DIR}/bin"
ARCH=$(uname -m)
case "${ARCH}" in
    x86_64) TERA_ARCH="linux64" ;;
    aarch64) TERA_ARCH="linux-arm64" ;;
    *) echo "Unknown architecture: ${ARCH}"; exit 1 ;;
esac
TERA_URL="https://github.com/acados/tera_renderer/releases/download/v0.0.41/t_renderer_${TERA_ARCH}"
if [ ! -f "${ACADOS_DIR}/bin/t_renderer" ]; then
    echo "Downloading t_renderer..."
    curl -sSL "${TERA_URL}" -o "${ACADOS_DIR}/bin/t_renderer"
    chmod +x "${ACADOS_DIR}/bin/t_renderer"
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
      -DCMAKE_BUILD_TYPE=Release \
      -DACADOS_EXTERNAL_HPMPC=OFF \
      ..
make install -j$(nproc)

echo "acados build complete."
echo "Library: ${ACADOS_DIR}/lib/"
ls -la ${ACADOS_DIR}/lib/
echo "Python dependencies are installed separately via environment/setup.sh."

echo ""
echo "=== Download + Build Complete ==="
echo "LD_LIBRARY_PATH should include: ${ACADOS_DIR}/lib"
