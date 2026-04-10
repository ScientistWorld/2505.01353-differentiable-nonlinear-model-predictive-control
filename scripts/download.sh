#!/bin/bash
# Download and build acados from source on the login node (internet available).
#
# Estimated total download size: ~200 MB
#   - acados checkout + renderer: ~50 MB
#   - vendored CPython 3.10 wheels (casadi/numpy/scipy/etc.): ~130 MB
# Estimated disk usage after build/unpack: ~2.3 GB
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
echo "Preparing vendored Python 3.10 runtime dependencies..."

mkdir -p /home/user/environment/vendor_wheels /home/user/environment/vendor_py310 /home/user/tmp/pip-tmp
TMPDIR=/home/user/tmp/pip-tmp python3 -m pip download \
    --only-binary=:all: \
    --platform manylinux2014_x86_64 \
    --python-version 310 \
    --implementation cp \
    --abi cp310 \
    --dest /home/user/environment/vendor_wheels \
    "casadi==3.7.2" \
    "numpy<2.3" \
    "scipy<1.16" \
    "deprecated<2"

python3 - <<'PY'
import glob
import os
import shutil
import zipfile

wheel_dir = "/home/user/environment/vendor_wheels"
out_dir = "/home/user/environment/vendor_py310"
os.makedirs(out_dir, exist_ok=True)

for wheel_path in sorted(glob.glob(os.path.join(wheel_dir, "*.whl"))):
    target = os.path.join(out_dir, os.path.basename(wheel_path)[:-4])
    if os.path.isdir(target):
        shutil.rmtree(target)
    os.makedirs(target, exist_ok=True)
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(target)
    print(f"Extracted {os.path.basename(wheel_path)} -> {target}")
PY

echo ""
echo "=== Download + Build Complete ==="
echo "LD_LIBRARY_PATH should include: ${ACADOS_DIR}/lib"
