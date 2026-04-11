# Problem Definition

## Research Question

The benchmark studies how to compute **solution sensitivities** for parameterized optimal control problems. In this setting, the cost, dynamics, or constraints depend on a parameter vector `theta`, and the goal is to determine how the optimal trajectory or first control action changes when `theta` changes.

This matters because many control-and-learning systems need gradients through an optimizer. If those gradients are inaccurate, unstable near constraint changes, or too slow to compute, the surrounding learning system becomes unreliable or unusable in practice.

The benchmark therefore asks for methods that can handle nonlinear optimal control problems with constraints while still producing useful derivatives of the optimizer output with respect to problem parameters.

## Why It Is Difficult

The task is challenging for three reasons:

1. The optimization problems are constrained and can become nonsmooth when the active set changes.
2. The parameter can affect several parts of the problem at once, including dynamics, costs, and inequalities.
3. A usable method must balance two goals at the same time: sensitivity accuracy and runtime efficiency.

## Success Criteria

A strong solution for this benchmark should satisfy all of the following:

1. **Accurate sensitivities**: The reported local sensitivities should agree closely with finite-difference reference values on the nonlinear pendulum benchmark.
2. **Constraint-aware behavior**: The method should remain meaningful near regions where constraints switch activity.
3. **Practical efficiency**: On the batched bounded-LQR timing benchmarks, solve-plus-sensitivity time should remain low enough to support differentiable control use cases.
4. **Reusable output**: The method must produce results in the format expected by the workspace evaluator so that different approaches can be compared fairly.
