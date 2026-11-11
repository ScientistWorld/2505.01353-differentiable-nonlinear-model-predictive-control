#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/single_point_shortcut/method.py
python3 redteam/test_case.py single_point_shortcut
