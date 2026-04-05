# Scientist Constraints

## Problem Formulation
The scientist must use the same optimal control problem (OCP) formulations as in the paper:
- **Pendulum**: Cart-pole system, N=20 horizon, nx=4 states (x, theta, v, omega), nu=1 control (F), parametric cost weight on Q matrix, Fmax=80, constraint on x >= -1.5. Exact formulation in `eval/evaluator.py` (run_pendulum_eval).
- **LQR**: Dense linear dynamics, N=20 horizon, nx=8 states, nu=4 controls, parametric cost matrices. Two settings: u_max=10^4 (loose) and u_max=1.0 (tight). Exact formulation in `eval/evaluator.py` (run_lqr_eval).

Do not simplify, reduce, or reformulate the problems. The scientist may not reduce N, change Q/R matrices, or alter the constraint structure.

## Solver Infrastructure
The scientist must use **acados** as the NLP solver backend. The contribution is the exact-Hessian parametric sensitivity computation in acados, not the underlying QP solver (HPIPM). Switching to a different MPC framework (e.g., MuJoCo MPC, OCS2, force, Crocoddyl) bypasses the paper's actual contribution.

## Sensitivity Computation Method
For the pendulum sensitivity accuracy experiment, the scientist must compute parametric sensitivities via the **adjoint sensitivity method** applied to the KKT conditions of the nonlinear OCP (Implicit Function Theorem). Computing sensitivities by re-solving the OCP at perturbed parameters (brute-force reoptimization) is not the method — it is a fallback that does not demonstrate the algorithmic contribution.

## Compliance Checklist
- [ ] Pendulum OCP uses N=20, nx=4, nu=1, Fmax=80, x >= -1.5 constraint, parametric Q weight
- [ ] LQR OCP uses N=20, nx=8, nu=4, parametric cost matrices, u_max=10^4 or u_max=1.0
- [ ] Uses acados NLP solver backend (not MuJoCo MPC, OCS2, force, Crocoddyl, etc.)
- [ ] Sensitivity computed via adjoint method on KKT conditions, not brute-force reoptimization
