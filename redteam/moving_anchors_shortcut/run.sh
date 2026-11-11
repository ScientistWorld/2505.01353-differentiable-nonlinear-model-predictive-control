#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/moving_anchors_shortcut/method.py
python3 redteam/test_case.py moving_anchors_shortcut
