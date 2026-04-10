#!/usr/bin/env python3
"""Runtime import helpers for the packaged acados reproduction."""

from __future__ import annotations

import glob
import importlib
import os
import traceback
import sys
from typing import Iterable


def _candidate_roots() -> list[str]:
    roots: list[str] = []
    py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"

    env_roots = [
        os.environ.get("PYTHONUSERBASE"),
        os.path.expanduser("~/.local/lib"),
        "/usr/local/lib",
        "/usr/lib",
    ]
    for root in env_roots:
        if not root:
            continue
        if root.endswith("/lib"):
            patterns = [
                os.path.join(root, py_version, "site-packages"),
                os.path.join(root, py_version, "dist-packages"),
            ]
        else:
            patterns = [root]
        for pattern in patterns:
            for match in sorted(glob.glob(pattern)):
                roots.append(match)

    # Respect the currently configured runtime path order first, especially
    # when the job injects vendored wheel roots through PYTHONPATH.
    for path in sys.path:
        if path:
            roots.append(path)

    # Preserve order while removing duplicates.
    seen: set[str] = set()
    unique_roots: list[str] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique_roots.append(root)
    return unique_roots


def _iter_casadi_package_roots() -> Iterable[str]:
    for root in _candidate_roots():
        init_py = os.path.join(root, "casadi", "__init__.py")
        if os.path.isfile(init_py):
            yield root


def ensure_casadi_importable():
    """
    Import CasADi robustly even if an earlier namespace-only package shadows it.

    Some cluster setup paths can leave a partial `casadi` namespace package
    ahead of the actual wheel. acados_template expects the real package with
    `MX`, `SX`, and `Function`.
    """
    for module_name in ("casadi", "casadi.casadi"):
        sys.modules.pop(module_name, None)

    tried_roots: list[str] = []
    failure_messages: list[str] = []
    for root in _iter_casadi_package_roots():
        tried_roots.append(root)
        if root not in sys.path:
            sys.path.insert(0, root)
        else:
            sys.path.remove(root)
            sys.path.insert(0, root)
        importlib.invalidate_caches()
        try:
            casadi = importlib.import_module("casadi")
        except Exception as exc:
            sys.modules.pop("casadi", None)
            failure_messages.append(
                f"{root}: {exc.__class__.__name__}: {exc}\n"
                f"{traceback.format_exc(limit=3)}"
            )
            continue
        required = ("MX", "SX", "Function")
        if all(hasattr(casadi, name) for name in required):
            return casadi
        sys.modules.pop("casadi", None)
        failure_messages.append(
            f"{root}: imported casadi without required symbols {required}"
        )

    raise ImportError(
        "Unable to import a functional CasADi package. "
        f"Python={sys.executable} {sys.version}; "
        f"Tried roots: {tried_roots}; "
        f"Failures: {failure_messages}; "
        f"sys.path[:12]={sys.path[:12]}"
    )
