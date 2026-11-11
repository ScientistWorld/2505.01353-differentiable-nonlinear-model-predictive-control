#!/bin/bash
# Use the gym's existing runtime without changing any installed package.
export ACADOS_SOURCE_DIR=/home/user/method/acados
export PYTHONNOUSERSITE=1
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH:-}
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH:-}
for audit_dep_dir in /home/user/environment/vendor_py310/*; do
    if [ -d "$audit_dep_dir" ]; then
        export PYTHONPATH="$audit_dep_dir:${PYTHONPATH}"
    fi
done
for audit_casadi_dir in /home/user/environment/vendor_py310/casadi-*; do
    if [ -d "$audit_casadi_dir/casadi" ]; then
        export LD_LIBRARY_PATH="$audit_casadi_dir/casadi:${LD_LIBRARY_PATH}"
    fi
done
