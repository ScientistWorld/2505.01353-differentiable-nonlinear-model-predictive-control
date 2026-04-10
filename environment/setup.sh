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
python3 -m pip install numpy scipy casadi deprecated
