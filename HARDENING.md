# Hardening Report (final iteration)

This iteration started from the hardened gym of the previous iteration (its report is kept in git history and its evidence in `hardening/prev_iteration_results/`). `REVIEW.md` listed two weaknesses:
1. Brute-force finite differences (FD) with a tighter solve ranked above the reference because compute was not scored.
2. The reproduction's smoothed (`tau_min > 0`) sensitivities were biased.

Both are fixed. Two experiments were added: one where the paper's method falls short, and one at a scale where FD no longer fits.

All numbers are outputs of the real evaluators. They come from job `d9863617-dbd` (final code, evidence in `hardening/results/`) and, for the before-fix acados run, job `7cc70131-186` (`hardening/results_job1/`). Metrics are `frac_sens_accurate / mean_log10_sens_rel_err / frac_u0_accurate`. Δ values are paired over identical instances, with ± one standard error.

## What changed

1. **acados sign fix (REVIEW item 2: a reproduction bug).** The cause is in acados itself, both the vendored commit and upstream `main`.
   - **The bug:** `ocp_nlp_constraints_bgh.c` adds the parametric part of the constraint Hessian, `d/dp [dh/dux^T (lam_u - lam_l)]`, to the parameter Jacobian of the Lagrangian gradient with sign **-1**. The QP Hessian (`+1.0`) and the stationarity residual (`grad f - DCt (lam_l - lam_u)`) both use `+(lam_u - lam_l)^T h`.
   - **Why only `tau_min > 0`:** at `tau_min = 0` the wrong term only shifts the multiplier of an *active* constraint, whose gradient is the same unit direction. The 30 hidden exact-map instances with an active path constraint were accurate before and after. With `tau_min > 0`, both sides of `|theta p| <= 1.5` carry multipliers `tau/slack`, and the complementarity row passes the error into `du0/dtheta`.
   - **Consistency with the observations:** this explains every observation in `REVIEW.md` — the error grows with `tau_min`, it is identical for the forward and adjoint paths, and it is insensitive to tolerance and clipping, while FD of the same solutions are exact.
   - **The fix:** one token, via `scripts/patch_acados.sh`. It is applied by `build_acados.sh` and checked/rebuilt by `scripts/ensure_acados.sh`. The paper's algorithm is unchanged.

   | | before (unpatched acados) | after |
   |---|---|---|
   | smoothed, `tau_min = 1e-4 / 1e-3 / 1e-2`, mean log10 error | -6.52 / -5.38 / -4.39 | -9.60 / -9.71 / -9.70 |
   | smoothed, all 180 hidden instances | 0.811 / -5.41 / 0.989 | **0.989 / -9.67 / 0.989** (Δlog -4.25 ± 0.13) |
   | exact pendulum (193) | 1.000 / -7.77 / 1.000 | 1.000 / -7.76 / 1.000 (Δlog +0.009 ± 0.006) |
   | LQR-248 (140) | 0.971 / -8.79 / 1.000 | identical |

2. **Compute budget (REVIEW item 1).** Counting solver calls cannot bind a method that runs its own solver. The evaluators (train and test, independent code) therefore charge CPU instead.
   - **Calls:** the predictor is called **once per experiment**. Each call may use `150 + n_instances * c` CPU seconds, with `c` = 1.0 for the pendulum experiments, 0.3 for the 248-parameter LQR and 0.15 for the 976-parameter LQR.
   - **What is counted:** the whole process tree, measured from `/proc` while running and from `RUSAGE_CHILDREN` at the end.
   - **Detached work:** the evaluator is a child subreaper, so double-forked or `setsid` workers stay in the accounted tree. All descendants are killed and reaped after each call.
   - **Failure:** an over-budget, crashed or timed-out call fails the run, with the worst value everywhere.
   - **No wall-clock dependence:** wall-clock time is never scored. The only wall-clock rule is a safety stop at 4× the budget + 10 min, which no CPU-bound predictor reaches.
3. **New experiment `bounded_lqr_large_adjoint` (weight 0.20).** It scales the paper's Sec. 5.2 LQR to `nx = 16, nu = 8`, i.e. 976 parameters, 460 hidden / 198 train instances, and `u_max = 1` on two thirds of them.
   - **Why:** at the paper's 248 parameters, central FD cost only about 0.3 CPU s per instance (0.67 s with Richardson extrapolation), too close to the reference's fixed setup cost for any budget to separate them.
   - **At 976 parameters:** the reference's adjoint costs 2 ms per instance, while central FD costs 1.76 CPU s and Richardson 3.69 CPU s.
4. **New experiment `pendulum_near_active_set_change` (weight 0.15)**, where the paper's method falls short.
   - **Construction:** the ground truth follows the fixed-active-set branch of a solved instance towards the nearest constraint switch, until the smallest strict-complementarity margin is a log-uniform target in [1e-6, 1e-3]. Assumption 1 still holds, the derivative is cross-checked by FD on the fixed-active-set system, and the warm start lies on the side away from the switch.
   - **Initial states:** they are always perturbed. With the paper's fixed initial state the switches sit at a few `theta` values, and the first build let a nearest-train-answer lookup score 0.353 here, above the reference. Rebuilding with perturbed initial states closed this (lookup: 0.000).
5. **Reference predictor.** Only the LQR Gauss–Newton baseline changed: it now reuses the exact solver, because GN equals the exact Hessian for this convex QP and the outputs are identical. This halves code generation on the 976-parameter LQR. The paper's method, its settings and all pendulum code paths are unchanged.

## Do better results score higher?

Hidden test (`hardening/results/variants/`). Experiments in order: exact | smoothed | near-switch | LQR-248 | LQR-976.

| method | exact | smoothed | near-switch | LQR-248 | LQR-976 |
|---|---|---|---|---|---|
| **reference** | **1.000/-7.76/1.000** | **0.989/-9.67/0.989** | **0.120/-1.77/0.967** | **0.971/-8.79/1.000** | **0.952/-7.92/0.989** |
| better: tight solve 1e-10 + clipping 1e-12 | 0.995/-9.19/1.000 | 0.989/-9.88/0.989 | 0.500/-4.41/0.973 | 1.000/-9.97/1.000 | 1.000/-9.93/1.000 |
| better: clipping 1e-12 | 0.995/-8.80/1.000 | 0.989/-9.67/0.989 | 0.120/-1.75/0.967 | 0.971/-9.18/1.000 | 0.952/-8.33/0.989 |
| weaker: loose tolerance 1e-5 (LQR 1e-4) | 0.974/-7.10/1.000 | 0.978/-7.97/0.989 | 0.020/-0.75/0.540 | 0.936/-8.38/0.971 | 0.885/-7.28/0.972 |
| baseline: Gauss–Newton Hessian | 0.005/-0.16/1.000 | 0.000/-0.54/0.989 | 0.000/-0.24/0.967 | 0.971/-8.79/1.000 | 0.952/-7.92/0.989 |
| baseline: constraints dropped | 0.000/0.00/0.000 | 0.000/0.00/0.000 | 0.000/0.00/0.000 | 0.586/-5.86/0.586 | 0.348/-3.48/0.348 |

- **Tight solve:** Δlog -1.44 ± 0.13 (exact), -0.21 ± 0.04 (smoothed), -2.64 ± 0.20 with Δfrac +0.38 ± 0.04 (near-switch), -1.18 ± 0.14 (LQR-248) and -2.01 ± 0.09 with Δfrac +0.048 ± 0.010 (LQR-976). Every gain is many standard errors.
- **Weaker variant:** worse in every experiment.
- **Train:** the same ordering (`hardening/results/variants/scores_train.json`). Reference train: 1.000/-7.91, 0.989/-9.73, 0.067/-1.33, 0.971/-8.88, 0.960/-8.06.
- **Determinism:** the reference is deterministic. Two runs (official `scripts/evaluate_test.sh` and the audit) produced identical scores on train and test, so seed noise is 0.

**Illustrative aggregate rank.** Weights × |coefficients| × improvement / spread over 11 methods: reference, its 2 baselines, 6 variants, 2 FD variants. Real spreads come from future attempts. The same scale is used for both splits.

| method | test | train |
|---|---|---|
| better: tight solve + clipping | **+0.84** | **+0.89** |
| tight IFT on the LQRs only, reference on the pendulum | +0.21 | +0.22 |
| better: clipping 1e-12 | +0.09 | +0.09 |
| reference | 0 | 0 |
| weaker: loose tolerance | -0.49 | -0.47 |
| Gauss–Newton baseline | -1.91 | -1.84 |

**Before** (previous report, same idea of scale): tight + clipping +0.35, clipping +0.12. The main new source of headroom is algorithmic: the near-switch experiment.

## Shortcuts: fix and score before → after (hidden test)

| shortcut | before | fix | after |
|---|---|---|---|
| Brute-force FD: tight solve + Richardson, every parameter, every experiment (REVIEW) | +0.06, **above** the reference | per-call CPU budget; 976-parameter LQR | run **fails**: `bounded_lqr_large_adjoint: compute budget exceeded (219 > 219 CPU s)` after the four other calls fit. Worst everywhere (`shortcut_fd_brute_force`) |
| Central FD at the paper's settings | -0.07 | same | would also exceed the budget (est. 1.76 CPU s × 460 ≈ 810 s vs 219); even ignoring the budget it is below the reference in all four experiments where it ran fully, and on 15 of the 16 LQR-976 instances where it was measured |
| Budget evasion: detached (double-fork + `setsid`) worker does the work while the predictor sleeps | n/a | subreaper + process-tree accounting | run **fails**: `compute budget exceeded (344 > 343 CPU s)` |
| Nearest train answer | 0/0/0; then **0.353** on near-switch in this iteration's first build | perturbed initial states for near-switch instances | 0.000 on near-switch; ≤ 0.05 anywhere |
| Fabricated zeros, garbage types, ±1e308, empty methods, crash, 10% subset, self-reported scores, omitted experiments, injected bad baseline | 0 / failed / reference unchanged | unchanged (strict parsing, raw-value scoring, every method in every experiment) | same as before: 0 / failed / reference unchanged (`hardening/results/shortcut_*`) |

## Shortcuts and issues left open

1. **FD on the one-parameter pendulum fits the budget.** With `n_theta = 1`, FD costs about as much as the IFT, so no budget separates them. It does not pay, though:
   - FD-tight on the pendulum + reference IFT on the LQRs ranks **-0.14** (test) / -0.09 (train).
   - The hybrid "FD-tight on the pendulum + tight IFT on the LQRs" ranks +0.08 / +0.12. That is *below* the same tight IFT without the FD half (+0.21 / +0.22). Its gain is the tight-tolerance IFT, an honest improvement.
   - FD crosses switches (near-switch 0.020) and is less accurate than the IFT on the smoothed map.
   - I treat this as an honest alternative that the one-parameter experiments cannot tell apart from the IFT on cost, not as a loophole.
2. **Forward (one-sided) FD on the 976-parameter LQR** costs about 0.9 CPU s per instance. It exceeds the hidden-test budget by only about 2× (about 1.2× on train). Its accuracy (about 1e-5 at best) is far below the reference's, so it cannot outrank it.
3. **Budget margins.** Reference CPU (3 methods per call) against budget:

   | split | pendulum | LQR-248 | LQR-976 |
   |---|---|---|---|
   | test | 17–21 / 300–343 s (≥ 14×) | 6.9 / 192 s (28×) | 50.7 / 219 s (4.3×) |
   | train | | | 45.9 / 180 s (3.9×) |

   - The LQR-976 margin is limited by acados code generation (about 45 CPU s per solver for 976 parameters); the per-instance adjoint is 2 ms.
   - CPU time does not depend on machine load, but it does depend on CPU speed. A node more than about 4× slower than the cluster's would fail the reference.
4. **Process-tree accounting** relies on Linux `/proc` and `PR_SET_CHILD_SUBREAPER`. Without them, orphaned workers would escape the budget. Both are available in the gym's container.
5. **The reproduced paper method is weak near constraint switches** (0.120). This is the IPM-based IFT at the paper's tolerance, not a reproduction bug: tightening the solve helps, lower clipping alone does not.
   - The paper reports no number in this regime. `scoring/reference.json` therefore records the reproduced value for this experiment, labelled as such (`_results_note`), and keeps the encoded paper claim under `_paper_claim_encoded`.
6. **Not scored:** the paper's wall-clock speed-ups (Table 1/2, Fig. 3) and the Sec. 5.3 chain example. Efficiency enters only through the CPU budget.

## Headroom check

| experiment | reference at a bound? | headroom shown |
|---|---|---|
| exact pendulum | `frac_sens_accurate` 1.000, `frac_u0_accurate` 1.000 | log error -7.76 → -9.19 |
| smoothed pendulum | no | -9.67 → -9.88; 2 instances with a wrong branch |
| near-switch (added) | no | 0.120 → 0.500 (`frac`), -1.77 → -4.41 (log); the exact answer is known |
| LQR-248 | `frac_u0_accurate` 1.000 | 0.971 → 1.000, -8.79 → -9.97 |
| LQR-976 (added) | no | 0.952 → 1.000, -7.92 → -9.93 |

- **Baselines:** simple baselines sit far below the reference (Gauss–Newton 0.005 on the exact map; constraint-blind 0.348 on LQR-976).
- **Brute force:** the brute force the paper avoids fails the budget.
- **Simple variants:** no simple variant reaches a bound outside the experiments already at it.

## Reference score before → after

| experiment | previous iteration | this iteration |
|---|---|---|
| exact pendulum | 1.000 / -7.77 / 1.000 | 1.000 / -7.76 / 1.000 |
| smoothed pendulum | 0.811 / -5.41 / 0.989 | **0.989 / -9.67 / 0.989** |
| LQR-248 | 0.971 / -8.79 / 1.000 | 0.971 / -8.79 / 1.000 |
| near-switch (new) | — | 0.120 / -1.77 / 0.967 |
| LQR-976 (new) | — | 0.952 / -7.92 / 0.989 |

`scoring/scores_test.json`, `scoring/scores_train.json` and `scoring/scores.json` (train copy) come from the reference predictor alone (proposed method plus its two baselines). They were produced by `scripts/evaluate_*.sh` in job `d9863617-dbd` with the final code and the patched acados.

## Weights

| experiment | before | after | why |
|---|---|---|---|
| exact pendulum | 0.5 | 0.35 | Paper's core claim (Sec. 5.1, Remark 3); the reference is at the bound of two of its metrics |
| smoothed pendulum | 0.2 | 0.15 | Stated contribution (Thm. 3, Remark 2); the reference is now close to its floor |
| near-switch | — | 0.15 | Fig. 2's switch region, where the method is weakest and real algorithmic headroom lies |
| LQR-248 | 0.3 | 0.15 | Table 1's correctness statement |
| LQR-976 | — | 0.20 | The paper's case for adjoints with many parameters (Sec. 2.2 complexity, Sec. 5.3), the only experiment where its efficiency claim binds through the budget |

Coefficients are unchanged: `frac_sens_accurate` 1.0, `mean_log10_sens_rel_err` 0.5, `frac_u0_accurate` 0.5.

## Reproducing this report

- `bash scripts/run.sh` rebuilds missing ground-truth caches, makes sure acados carries the fix, and scores the reference on train and hidden test.
- `RUN_HARDENING_CHECKS=1 bash scripts/run.sh` also runs the smoke test, the unpatched-acados reference (only while the installed library predates the fix), the variants and every shortcut (`hardening/run_checks.py`).
- `python3 hardening/rank_summary.py hardening/results test` recomputes the illustrative ranks from the saved scores and predictions; the per-instance `records_*.json` allow rescoring without solvers. Raw predictions are not committed (size).
