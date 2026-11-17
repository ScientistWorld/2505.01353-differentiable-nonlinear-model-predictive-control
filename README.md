# Differentiable Nonlinear Model Predictive Control

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

<!-- hardening-note -->
> [!NOTE]
> **Red-teamed and hardened.** A red team tried to score on this environment's hidden test without doing better research, and the environment was then fixed against the shortcuts that worked: see [`REDTEAM.md`](REDTEAM.md) and [`HARDENING.md`](HARDENING.md). The environment as it was before is kept as branch [`pre-hardening`](../../tree/pre-hardening).

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2505.01353"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2505.01353-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2505.01353](https://arxiv.org/abs/2505.01353) |
|:---|:---|
| **Domain** | Optimization / Control Theory / Differentiable Programming |
| **TL;DR** | Efficient computation of parametric solution sensitivities for nonlinear MPC using implicit function theorem with interior-point SQP, achieving 3x+ speedups over state-of-the-art differentiable MPC solvers. |

## Summary

This paper addresses the key challenge of computing parametric solution sensitivities (gradients of optimal solutions with respect to parameters) for general nonlinear programs in model predictive control. The approach combines the implicit function theorem applied to the KKT conditions solved by an interior-point SQP method, with a two-solver strategy: a fast nominal solver for convergence and an exact-Hessian sensitivity solver for accuracy. The implementation in the acados framework exploits the OCP structure via Riccati factorization, achieving significant speedups over prior differentiable MPC implementations like mpc.pytorch and cvxpygen.

## Problem

The benchmark studies how to compute **solution sensitivities** for parameterized optimal control problems. In this setting, the cost, dynamics, or constraints depend on a parameter vector `theta`, and the goal is to determine how the optimal trajectory or first control action changes when `theta` changes.

This matters because many control-and-learning systems need gradients through an optimizer. If those gradients are inaccurate, unstable near constraint changes, or too slow to compute, the surrounding learning system becomes unreliable or unusable in practice.

The benchmark therefore asks for methods that can handle nonlinear optimal control problems with constraints while still producing useful derivatives of the optimizer output with respect to problem parameters.

## The paper's method

The paper proposes an **efficient implementation of parametric solution sensitivity computation** for general nonlinear programs (NLPs) arising in optimal control, using:
1. Implicit function theorem (IFT) applied to the KKT conditions of an interior-point SQP method
2. Exact Hessian computation (not just Gauss-Newton approximation) for correct sensitivities
3. A **two-solver approach**: nominal solver (with approximations for speed) + sensitivity solver (with exact Hessian)
4. Structure-exploiting Riccati factorization via HPIPM/BLASFEO

## Key results of the paper

- **Pendulum OCP**: Solution sensitivities match finite-difference baselines across parameter range including active-set change boundaries; Gauss-Newton Hessian gives completely wrong results (Remark 3)
- **Bounded LQR**: acados is 3.6x–520x faster than mpc.pytorch and 19x–160x faster than cvxpygen for solving 128 problems with adjoint sensitivities
- **Chain of masses**: Single adjoint sensitivity is ~2.5x faster than full forward Jacobian evaluation

## Run it

```bash
pip install sciworld
sw research 2505.01353 --mode innovate --agent claude-code
sw evaluate 2505.01353
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

