Audit complete. The inherited reproduction milestone remains `core_claim` for
the local exact-Hessian versus Gauss-Newton sensitivity comparison. No broader
reproduction milestone is claimed by this audit.

- Three numerical reference reruns completed; scored seed spread is zero.
- Real tighter-solver variants and the weaker Gauss-Newton variant were scored.
- An independent finite-difference step sweep confirms a scientific ordering
  reversal for the lower sensitivity-clipping variant.
- Fourteen shortcut cases were run: seven pay (including two ties), one scores
  below the reference, and six are rejected without worst-value score records.
- All 23 candidate artifacts were rescored with the original no-argument
  train/test scripts and no inherited method-only Python/library settings.
- Results, diagnostics, scripts, and the report are in redteam/ and REDTEAM.md.
