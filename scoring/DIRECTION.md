# Research Direction

## Research Problem
This paper addresses the problem of computing accurate parametric sensitivities (gradients of optimal solutions with respect to problem parameters) for nonlinear Model Predictive Control (NMPC). The key challenge: when an MPC problem depends on parameters (e.g., cost weights, physical constants, reference trajectories), we need du*/dtheta to train policies via gradient-based methods, embed MPC in larger differentiable pipelines, or adapt MPC to changing conditions. Computing these sensitivities via the Implicit Function Theorem applied to the KKT conditions requires the exact second-order derivatives of the NLP — Gauss-Newton approximations give wrong sensitivities.

## Core Contribution
The paper's contribution is demonstrating that using the **exact (full) Hessian** in the SQP solver, combined with Riccati-based parametric sensitivity computation, gives accurate parametric sensitivities for nonlinear OCPs. The scientist must work on improving this approach: how to compute or approximate second-order sensitivity information more accurately or more efficiently for parametric nonlinear MPC.

## Approach Scope
The scientist may work on:
- Improving the accuracy of parametric sensitivities (lower sensitivity_max_error)
- Reducing solve + sensitivity time for bounded LQR problems
- Making exact-Hessian sensitivity computation more robust (handle ill-conditioned QP subproblems better)
- Warm-starting strategies for exact Hessian SQP
- Exploring partial exact-Hessian approaches (exact cost Hessian + GN dynamics Hessian)
- Regularization strategies that preserve sensitivity accuracy
- Scaling to larger N or nx/nu dimensions

The scientist may NOT switch to a fundamentally different paradigm (e.g., reinforcement learning policy for MPC, purely data-driven approaches) — the contribution is about algorithmic sensitivity computation for nonlinear OCP.

## Out of Bounds
- Replacing acados with MuJoCo MPC, OCS2, Crocoddyl, or another MPC framework. The contribution is the exact-Hessian sensitivity computation in acados.
- Using brute-force reoptimization (re-solve OCP at perturbed parameters, no adjoint) as the sensitivity method. This does not demonstrate the algorithmic contribution.
- Training a neural network to approximate MPC solutions. This is a different research area (learning-based MPC), not an improvement on the sensitivity computation method.
- Switching from SQP/NLP to a fundamentally different approach (e.g., direct collocation with different optimization).
