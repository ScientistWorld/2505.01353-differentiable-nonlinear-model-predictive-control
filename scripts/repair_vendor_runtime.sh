#!/bin/bash
# Repair locally vendored Python wheels before running in offline compute jobs.
#
# The repository's broad ignore rules can omit files named core.* from extracted
# wheels. Compute nodes have no internet, so repair any missing critical files
# from the already-downloaded wheels in environment/vendor_wheels.

set -euo pipefail

cd /home/user

python3 - <<'PY'
from pathlib import Path
import sys
import zipfile

wheel_dir = Path("/home/user/environment/vendor_wheels")
vendor_dir = Path("/home/user/environment/vendor_py310")

repairs = [
    (
        "numpy-*.whl",
        "numpy-*/numpy/ma/core.py",
        "numpy/ma/core.py",
    ),
    (
        "numpy-*.whl",
        "numpy-*/numpy/ma/core.pyi",
        "numpy/ma/core.pyi",
    ),
]

for wheel_pattern, extracted_pattern, member_name in repairs:
    if any(vendor_dir.glob(extracted_pattern)):
        continue

    wheels = sorted(wheel_dir.glob(wheel_pattern))
    if not wheels:
        raise SystemExit(
            f"Missing {member_name} and no local {wheel_pattern} in {wheel_dir}. "
            "Run scripts/download.sh on an internet-enabled node before submitting."
        )

    wheel_path = wheels[-1]
    targets = sorted(vendor_dir.glob(wheel_path.name[:-4]))
    if not targets:
        raise SystemExit(
            f"Missing extracted vendor directory for {wheel_path.name}. "
            "Run scripts/download.sh on an internet-enabled node before submitting."
        )

    with zipfile.ZipFile(wheel_path) as zf:
        if member_name not in zf.namelist():
            raise SystemExit(f"{member_name} not found in {wheel_path}")
        zf.extract(member_name, targets[0])
        print(f"repaired_vendor_file={targets[0] / member_name}")

print("vendor_runtime_ok=true")
PY
