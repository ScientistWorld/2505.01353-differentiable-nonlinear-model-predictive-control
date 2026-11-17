#!/bin/bash
# Clean and rebuild acados from the current source tree.

set -e

ACADOS_DIR="${ACADOS_SOURCE_DIR:-/home/user/method/acados}"

if [ ! -f "${ACADOS_DIR}/CMakeLists.txt" ]; then
    echo "ERROR: missing acados source tree at ${ACADOS_DIR}"
    exit 1
fi

SOURCE_COMMIT="$(git -C "${ACADOS_DIR}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
INSTALLED_COMMIT=""
if [ -f "${ACADOS_DIR}/lib/git_commit_hash" ]; then
    INSTALLED_COMMIT="$(cat "${ACADOS_DIR}/lib/git_commit_hash")"
fi

echo "acados_source_commit=${SOURCE_COMMIT}"
echo "acados_installed_commit=${INSTALLED_COMMIT:-missing}"

# The acados install prefix is the source tree itself, so stale build products
# can survive source updates. Remove the old build/install artifacts before
# reconfiguring to avoid mixed-version shared libraries.
rm -rf "${ACADOS_DIR}/build"
rm -f "${ACADOS_DIR}/lib/libacados.so"
rm -f "${ACADOS_DIR}/lib/libhpipm.so"
rm -f "${ACADOS_DIR}/lib/libqpOASES_e.so"
rm -f "${ACADOS_DIR}/lib/libblasfeo.so" \
      "${ACADOS_DIR}/lib/libblasfeo.so.0" \
      "${ACADOS_DIR}/lib/libblasfeo.so.0.1.4.2"
rm -f "${ACADOS_DIR}/lib/git_commit_hash" "${ACADOS_DIR}/lib/link_libs.json" "${ACADOS_DIR}/lib/.gym_sign_fix"

# The gym's one-line sign fix of the parametric constraint Hessian (see the script).
bash /home/user/scripts/patch_acados.sh

mkdir -p "${ACADOS_DIR}/build"
cd "${ACADOS_DIR}/build"
cmake -DACADOS_WITH_QPOASES=ON \
      -DACADOS_WITH_OSQP=OFF \
      -DACADOS_WITH_HPIPM=ON \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_BUILD_TYPE=Release \
      -DACADOS_EXTERNAL_HPMPC=OFF \
      ..
make install -j"$(nproc)"
touch "${ACADOS_DIR}/lib/.gym_sign_fix"
