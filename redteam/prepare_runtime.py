"""Restore the packaged NumPy wheel under redteam, without editing environment/.

The initial vendored tree is incomplete (numpy/ma/core.py is absent). This is
the same local wheel used by scripts/repair_vendor_runtime.sh, extracted whole
for the numerical method only. No package is installed or modified.
"""
from pathlib import Path
import zipfile

root = Path('/home/user')
target = root / 'redteam/generated/runtime_numpy'
if not (target / 'numpy/ma/core.py').exists():
    wheel = next((root / 'environment/vendor_wheels').glob('numpy-*.whl'))
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel) as zf:
        zf.extractall(target)
    print('audit_method_numpy_wheel=' + wheel.name)
