#!/bin/bash
# Install Python packages into the container overlay.
#
# Run by the system on the login node inside the container with a persistent overlay.
# Use python -m pip here instead of uv. On this cluster's root-mapped
# fakeroot overlay, uv can resolve packages successfully and then crash inside
# libfakeroot semaphore handling before installation completes.

set -e

export PIP_ROOT_USER_ACTION=ignore

# Install scientific Python packages and CasADi.
python3 -m pip install numpy scipy matplotlib pillow casadi

# Install acados_template (Python interface for acados)
# Note: acados must be built first (in download.sh / run.sh)
cd /home/user/method/acados/interfaces/acados_template
python3 -m pip install -e .
cd /home/user
