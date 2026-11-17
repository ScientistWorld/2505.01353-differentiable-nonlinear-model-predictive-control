# Problem Definition

## Research Question

How do we compute accurate **parametric solution sensitivities** of constrained, nonlinear optimal control problems (OCPs)? An OCP depends on a parameter vector `theta` (entering costs, dynamics and constraints); its optimal first control `u0*(theta)` is the output of an MPC policy. Learning-based MPC needs derivatives of that output with respect to `theta` (forward sensitivities, or adjoint sensitivities `seed . d u0*/d theta` for back-propagation).

## Why It Is Difficult

1. The problems are nonconvex and constrained; the solution map is only piecewise smooth (it has kinks where constraints switch between active and inactive) and can have several local branches.
2. The parameter enters cost, dynamics and inequality constraints at once.
3. Derivatives are only as good as the solution they are taken at, and approximations that are harmless for solving (for example a Gauss-Newton Hessian) can make derivatives badly wrong.
4. Near constraint switches the exact map is non-differentiable; a smoothed (interior-point / barrier) version of the optimality conditions gives a differentiable approximation whose derivative must itself be computed correctly.

## The Benchmark Problems

All problems are fully specified in each instance file (`problem` block); a method must solve exactly the stated problem.

**Parametric pendulum on a cart** (`pendulum_sensitivity_accuracy`, `pendulum_smoothed_sensitivity`, `pendulum_near_active_set_change`). States `x = (p, phi, v, omega)`, force `u`, scalar parameter `theta` = cart mass. `N = 50` intervals, `T = 2 s`, `dt = T/N`; dynamics: one RK4 step per interval of

```
p' = v,  phi' = omega
v' = (-m l sin(phi) omega^2 + m g cos(phi) sin(phi) + u) / (theta + m - m cos(phi)^2)
omega' = (-m l cos(phi) sin(phi) omega^2 + u cos(phi) + (theta + m) g sin(phi)) / (l (theta + m - m cos(phi)^2))
```

with `m = 0.1, g = 9.81, l = 0.8`.

```
min   sum_{n<N} dt * (theta * x_n' Q x_n + R u_n^2) + theta * x_N' Q x_N,   Q = 2 diag(1e3, 1e3, 1e-2, 1e-2), R = 0.2
s.t.  x_0 = x0,  x_{n+1} = RK4(x_n, u_n; theta),
      -80 <= u_n <= 80            (n = 0..N-1)
      -1.5 <= theta * p_n <= 1.5  (n = 1..N-1)
```

- With `tau_min = 0` the target is the exact solution map.
- With `tau_min > 0` it is the smoothed map. Here every one-sided inequality `h_i <= 0` satisfies `mu_i * h_i = -tau_min` instead of complementarity, and the equalities stay exact.

The problem is multimodal. Each pendulum instance therefore ships `initial_guess`: the primal solution on the same branch at a neighbouring parameter `theta -/+ 1e-3`, i.e. the warm start of a parameter sweep. The target is the locally optimal solution on that branch (for the first two experiments it is also the best local minimum the evaluator found).

`pendulum_near_active_set_change` uses the exact map (`tau_min = 0`) at parameters close to a constraint switch: some inequality is within `1e-6` to `1e-3` of becoming active or inactive (its multiplier, or its slack, is that small), while strict complementarity, LICQ and second-order sufficiency still hold, so `d u0/d theta` is well defined. The warm start lies on the side away from the switch, and the initial state is always perturbed.

**Bounded LQR** (`bounded_lqr_adjoint_accuracy`, and the scaled-up `bounded_lqr_large_adjoint`).
- **Size and parameters:** `N = 20`, `nx = 8`, `nu = 4`. The 248 parameters are `theta = [vec(A) (64), vec(B) (32), b (8), vec(H) (144)]`, each `vec` column-major. The scaled-up experiment has `nx = 16`, `nu = 8` and 976 parameters in the same layout (`vec(A)` 256, `vec(B)` 128, `b` 16, `vec(H)` 576).
- **Problem:**

```
min  sum_{n<N} [x_n; u_n]' H [x_n; u_n] + x_N' H[:nx,:nx] x_N
s.t. x_0 = x0,  x_{n+1} = A x_n + B u_n + b,  |u_n| <= u_max (elementwise)
```

- **Data:** `A = I + 0.2 M` (`I + 0.2 sqrt(8/nx) M` at `nx = 16`, the same open-loop spread), and `M`, `B`, `b`, `x0` are standard normal; `H = I`; `u_max` is `1` or `1e4`.
- **Required output:** `u0` and the adjoint `d(seed . u0)/d theta` (248 or 976 numbers) for the instance's `seed_u0`.

## Success Criteria

1. **Correct solution:** the reported `u0` is the optimal first control of the stated problem (on the warm-start branch for the pendulum).
2. **Accurate sensitivities:** the reported derivative matches the exact derivative of that solution map. The smoothed problem is differentiated as smoothed, not replaced by something easier.
3. **Robustness across instances:** this covers many parameter values, initial states, smoothing levels and constraint activity patterns, including near-degenerate ones.
4. **Efficiency:** each experiment's instances are solved and differentiated within a CPU budget that fits one solution, one factorization and one backsolve per instance with a wide margin, but not one or more extra solves per parameter (see `briefing/evaluation.md`).
