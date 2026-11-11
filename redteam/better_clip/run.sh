#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/better_clip/method.py
python3 redteam/test_case.py better_clip
