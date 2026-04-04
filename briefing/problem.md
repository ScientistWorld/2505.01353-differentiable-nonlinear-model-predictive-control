# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself. Think about if a future scientist agent try to solve this problem from scratch without knowing what approach the paper took. If you leak the solution, you compromise the benchmark.

## Research Question

The paper addresses the problem of computing **parametric solution sensitivities** — that is, the gradients (derivatives) of the optimal solution of an optimization problem with respect to its parameters. This is critical for combining learning-based methods (neural networks, RL) with model predictive control (MPC), where one needs to backpropagate through an optimization solver.

The challenge is: given an optimal control problem (OCP) of the form:
```
minimize cost(x, u; θ)
subject to dynamics(x, u; θ) = 0
          inequality constraints(x, u; θ) ≤ 0
```
where θ are parameters, compute ∂solution/∂θ efficiently.

This is hard because:
1. The solution involves solving an NLP with inequality constraints
2. At constraint boundaries, the solution map can be nondifferentiable (kinks)
3. Computing exact sensitivities requires the exact Hessian, not just an approximation
4. Existing methods (mpc.pytorch, cvxpygen) are either slow, limited to simple problem forms, or give wrong sensitivities

## Why It Matters

Parametric solution sensitivities are a key building block for:
- Differentiable MPC layers in neural networks
- Learning-enhanced MPC (learning system models, costs, or policies)
- Imitation learning from MPC demonstrations
- Real-time MPC with online adaptation

Without efficient and accurate sensitivity computation, learning-enhanced control cannot achieve the necessary real-time performance, especially on embedded platforms.

## Success Criteria

A successful solution must:
1. **Solve general NLPs**: Support nonlinear cost, nonlinear dynamics, and nonlinear inequality constraints — not just quadratic costs with simple bounds
2. **Compute accurate sensitivities**: Solution sensitivities should match finite-difference baselines
3. **Handle nondifferentiability gracefully**: At active-set changes, provide correct smoothed sensitivities
4. **Be computationally efficient**: Meet or exceed the speed of specialized solvers (3x+ speedup over prior art)
5. **Support both forward and adjoint modes**: Forward for few parameters, adjoint for backpropagation through networks
