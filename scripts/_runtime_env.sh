#!/bin/bash
# Shared runtime environment for the gym's offline container: vendored CPython
# 3.10 wheels (numpy/scipy/casadi) and, for method code, the acados build.
# Source this file; it does not change directories.

export PYTHONNOUSERSITE=1
for dep_dir in /home/user/environment/vendor_py310/*; do
    if [ -d "${dep_dir}" ]; then
        export PYTHONPATH="${dep_dir}:${PYTHONPATH:-}"
    fi
done
CASADI_VENDOR_DIR="$(find /home/user/environment/vendor_py310 -maxdepth 1 -mindepth 1 -type d -name 'casadi-*' 2>/dev/null | head -n 1)"
if [ -n "${CASADI_VENDOR_DIR}" ]; then
    export LD_LIBRARY_PATH="${CASADI_VENDOR_DIR}/casadi:${LD_LIBRARY_PATH:-}"
fi
