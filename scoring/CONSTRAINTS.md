# Scientist Constraints

## Problem Formulation
The scientist must use the packaged workspace formulations below, which preserve the paper's method while matching the runnable environment:
- **Pendulum**: Use the packaged formulation in `method/run_reproduction.py`: cart-pole system with `N=20`, `T=1.0`, `nx=4`, `nu=1`, `Fmax=80`, parametric state weighting, parametric cart-mass dynamics, and parametric inequality `-1.5 <= -p * theta^2 <= 1.5`. This is a reduced-scale but method-faithful version of the paper's Appendix A.10 setup.
- **LQR**: Dense linear dynamics, `N=20`, `nx=8`, `nu=4`, parametric cost matrices. Two settings: `u_max=10^4` and `u_max=1.0`. The packaged benchmark uses `n_batch=128`.

Do not simplify, reduce, or reformulate the problems. The scientist may not reduce N, change Q/R matrices, or alter the constraint structure.

## Solver Infrastructure
The scientist must use **acados** as the NLP solver backend. The contribution is the exact-Hessian parametric sensitivity computation in acados, not the underlying QP solver (HPIPM). Switching to a different MPC framework (e.g., MuJoCo MPC, OCS2, force, Crocoddyl) bypasses the paper's actual contribution.

## Sensitivity Computation Method
For the pendulum sensitivity accuracy experiment, the scientist must compute parametric sensitivities via the **adjoint sensitivity method** applied to the KKT conditions of the nonlinear OCP (Implicit Function Theorem). Computing sensitivities by re-solving the OCP at perturbed parameters (brute-force reoptimization) is not the method — it is a fallback that does not demonstrate the algorithmic contribution.

## Compliance Checklist
- [ ] Pendulum OCP uses the packaged reduced-scale formulation in `method/run_reproduction.py` with `N=20`, `T=1.0`, `nx=4`, `nu=1`, `Fmax=80`, parametric cost, dynamics, and inequality
- [ ] LQR OCP uses `N=20`, `nx=8`, `nu=4`, parametric cost matrices, `u_max=10^4` or `u_max=1.0`, and `n_batch=128`
- [ ] Uses acados NLP solver backend (not MuJoCo MPC, OCS2, force, Crocoddyl, etc.)
- [ ] Sensitivity computed via adjoint method on KKT conditions, not brute-force reoptimization
