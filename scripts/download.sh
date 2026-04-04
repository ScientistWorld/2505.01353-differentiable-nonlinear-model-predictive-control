#!/bin/bash
# Download and build acados from source.
#
# Estimated total download size: ~50 MB (git clone)
# Estimated disk usage after build: ~2 GB
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.

set -e

cd /home/user

# Check if acados is already cloned
if [ -d "method/acados" ]; then
    echo "acados already cloned, checking submodules..."
    cd method/acados
    git submodule update --recursive --init 2>/dev/null || true
    cd /home/user
else
    echo "Cloning acados repository..."
    git clone --recursive https://github.com/acados/acados.git method/acados
fi

ACADOS_DIR="/home/user/method/acados"

# Download t_renderer binaries if not present
TERA_RENDERER_DIR="${ACADOS_DIR}/bin/t_renderer"
if [ ! -f "${TERA_RENDERER_DIR}/t_renderer" ]; then
    echo "Downloading t_renderer binaries..."
    mkdir -p "${TERA_RENDERER_DIR}"
    TERA_VERSION="v0.0.41"
    ARCH=$(uname -m)
    case "${ARCH}" in
        x86_64) TERA_ARCH="linux64" ;;
        aarch64) TERA_ARCH="linux-arm64" ;;
        *) echo "Unknown architecture: ${ARCH}"; exit 1 ;;
    esac
    TERA_URL="https://github.com/acados/tera_renderer/releases/download/${TERA_VERSION}/t_renderer_${TERA_ARCH}"
    curl -sSL "${TERA_URL}" -o "${TERA_RENDERER_DIR}/t_renderer"
    chmod +x "${TERA_RENDERER_DIR}/t_renderer"
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
      -DACADOS_WITH_QORE=OFF \
      ..
make install -j$(nproc)

echo "acados build complete."
echo "LD_LIBRARY_PATH should include: ${ACADOS_DIR}/lib"
