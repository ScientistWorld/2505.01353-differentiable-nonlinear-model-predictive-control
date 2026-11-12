# Research Direction

## In scope

Better ways to compute **correct, precise solution sensitivities of constrained nonlinear OCPs**, scored on hidden instances:

- **More precise exact-map sensitivities:** better convergence of the nominal solve before differentiating, better handling of nearly-active constraints and multiplier/slack clipping, iterative refinement of the KKT solve.
- **Correct derivatives of the smoothed (barrier) solution map:** the reproduced acados implementation is systematically biased there, and the error grows with `tau_min`.
- **Robust adjoints for constrained problems:** many parameters, and tight control bounds with degenerate or near-degenerate active sets.
- **Robust nominal solves from the given warm start**, so the derivative is taken at the right solution.

## Out of scope

- Changing the problem to make derivatives easier, for example answering exact instances with a smoothed solution, or ignoring constraints. The solution-correctness constraint (`frac_u0_accurate`) and per-instance gating catch this.
- Reporting anything other than the computed `u0` and derivative (self-reported errors or scores are ignored).
- Using the evaluator's ground truth or code.

## Note on finite differences

Finite differences of the solution map are a valid but expensive way to obtain a derivative (one or more extra solves per parameter). The gym scores accuracy, not cost.
- **At the paper's tolerance**, central differences rank below the reference.
- **With a 100× tighter nominal solve plus Richardson extrapolation**, they rank slightly above it. They still rank below the paper's implicit-function-theorem sensitivities computed with that same tighter solve.

The paper's contribution is to obtain exact derivatives from a single factorization. A method that wants to beat the reference should improve the derivative computation itself.
