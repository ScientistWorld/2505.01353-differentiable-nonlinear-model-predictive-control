#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 -u redteam/run_suite.py
