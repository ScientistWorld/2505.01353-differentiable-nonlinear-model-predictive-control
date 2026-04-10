#!/usr/bin/env python3
"""
Pendulum OCP sensitivity experiment from Section 5.1 / Appendix A.10.

This script implements the paper's two-solver workflow:
1. solve the nominal NLP with a Gauss-Newton SQP solver,
2. transfer the primal-dual iterate to an exact-Hessian solver,
3. compute adjoint sensitivities with the exact-Hessian KKT factorization,
4. compare exact and Gauss-Newton sensitivities against finite differences.
"""

from __future__ import annotations

import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(THIS_DIR)
sys.path.insert(0, THIS_DIR)

from run_reproduction import run_pendulum_eval


def main():
    results = run_pendulum_eval()
    out_path = os.path.join(ROOT_DIR, "checkpoints", "pendulum_sensitivity_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print(f"Wrote pendulum results to {out_path}")


if __name__ == "__main__":
    main()
