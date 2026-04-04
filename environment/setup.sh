#!/bin/bash
# Install Python packages into the container overlay.
#
# Run by the system on the login node inside the container with a persistent overlay.

set -e

# Install Python packages needed for acados Python interface
uv pip install --system numpy scipy matplotlib

# Install casadi (required for acados OCP formulation)
uv pip install --system casadi

# Install acados_template (Python interface)
cd /home/user/method/acados/interfaces/acados_template
uv pip install --system -e .
cd /home/user
