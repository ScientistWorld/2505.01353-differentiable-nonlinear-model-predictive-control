# Research Direction

## In scope

Better ways to compute **correct, precise solution sensitivities of constrained nonlinear OCPs, at the cost of one factorization per solution**, scored on hidden instances:

- **Sensitivities near constraint switches.** Here the reference is accurate on only about 12% of instances: an interior-point iterate at tolerance 1e-8 blurs constraints whose multiplier or slack is 1e-6 to 1e-3. Ideas include active-set identification and refinement before the factorization, better multiplier and slack handling, tighter or adaptive barrier targets, and iterative refinement of the KKT solve.
- **More precise exact-map sensitivities:** better convergence of the nominal solve before differentiating, and better clipping.
- **Robust adjoints for constrained problems with many parameters** (976 on the scaled LQR), including degenerate and near-degenerate active sets, within the compute budget.
- **Robust nominal solves from the given warm start**, so the derivative is taken at the right solution.

## Out of scope

- Changing the problem to make derivatives easier, for example answering exact instances with a smoothed solution, or ignoring constraints. The solution-correctness constraint (`frac_u0_accurate`) and per-instance gating catch this.
- Reporting anything other than the computed `u0` and derivative (self-reported errors or scores are ignored).
- Using the evaluator's ground truth or code.
- Escaping the compute budget, for example by doing the work in detached processes. The whole process tree is charged.

## Note on finite differences

Finite differences of the solution map need one or more extra solves per parameter.

- **976-parameter LQR:** about 1.8 CPU s per instance for central differences against 2 ms for the reference's adjoint. A brute-force submission exceeds the budget there and fails the run.
- **One-parameter pendulum:** finite differences fit the budget but do not pay. Replacing the IFT by tight-tolerance Richardson differences there lowers the aggregate rank. Steps cross constraint switches in the near-switch experiment, and the smoothed map is less accurate than the IFT.

Gains so far come from the derivative computation and the nominal solve, e.g. a 100× tighter solve with lower clipping.
