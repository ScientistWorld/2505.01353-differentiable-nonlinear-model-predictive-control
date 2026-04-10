#!/bin/bash
# Python dependencies are vendored into the workspace under
# `environment/vendor_py310` and loaded via `PYTHONPATH` at runtime.
#
# Keep setup as a no-op to avoid cluster-specific overlay/package-manager
# failures. The authoritative dependency acquisition path is `scripts/download.sh`.

set -e

echo "setup.sh: no-op; runtime uses vendored workspace wheels from environment/vendor_py310."
