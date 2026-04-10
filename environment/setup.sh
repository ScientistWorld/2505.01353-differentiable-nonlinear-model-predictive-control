#!/bin/bash
# Install Python packages into the container overlay.
#
# Run by the system on the login node inside the container with a persistent overlay.
# Use python -m pip here instead of uv. On this cluster's root-mapped
# fakeroot overlay, uv can resolve packages successfully and then crash inside
# libfakeroot semaphore handling before installation completes.

set -e

export PIP_ROOT_USER_ACTION=ignore

# Install only PyPI dependencies here. The setup phase can run before the
# workspace submodule tree is available, so acados_template is imported from
# source at runtime via PYTHONPATH in scripts/run.sh and scripts/method.sh.
#
# The scheduler wraps python -m pip with uv. A previous setup left a broken
# namespace-only casadi import in the overlay, so force a reinstall and check
# that the compiled CasADi symbols used by acados_template are importable.
python3 -m pip install --force-reinstall --upgrade \
    "numpy<2.3" \
    "scipy<1.16" \
    "casadi==3.7.2" \
    "deprecated<2"

python3 - <<'PY'
import casadi

missing = [name for name in ("MX", "SX", "Function") if not hasattr(casadi, name)]
if missing:
    raise SystemExit(
        f"CasADi import is incomplete at {getattr(casadi, '__file__', None)}; "
        f"missing {missing}"
    )
print(f"CasADi {casadi.__version__} OK from {casadi.__file__}")
PY
