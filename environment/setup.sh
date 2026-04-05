#!/bin/bash
# Install Python packages into the container overlay.
#
# Run by the system on the login node inside the container with a persistent overlay.
# Uses uv for faster installation.

set -e

# Install scientific Python packages
uv pip install --system numpy scipy matplotlib pillow

# Install casadi (required for acados OCP formulation)
uv pip install --system casadi

# Install acados_template (Python interface for acados)
# Note: acados must be built first (in download.sh / run.sh)
cd /home/user/method/acados/interfaces/acados_template
uv pip install --system -e .
cd /home/user
