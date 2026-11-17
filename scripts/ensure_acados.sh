#!/bin/bash
# Make sure the installed acados library carries the gym's sign fix
# (scripts/patch_acados.sh). Rebuilds libacados only when the installed
# library predates the fix; a no-op otherwise.

set -euo pipefail

ACADOS_DIR="${ACADOS_SOURCE_DIR:-/home/user/method/acados}"

bash /home/user/scripts/patch_acados.sh
if bash /home/user/scripts/patch_acados.sh --check; then
    echo "acados library: sign fix present"
    exit 0
fi

echo "acados library predates the sign fix: rebuilding libacados"
if [ -f "${ACADOS_DIR}/build/Makefile" ] && make -C "${ACADOS_DIR}/build" install -j"$(nproc)"; then
    echo "incremental acados rebuild done"
else
    echo "incremental rebuild unavailable or failed: full acados build"
    bash /home/user/scripts/build_acados.sh
fi
touch "${ACADOS_DIR}/lib/.gym_sign_fix"
echo "acados library: sign fix installed"
