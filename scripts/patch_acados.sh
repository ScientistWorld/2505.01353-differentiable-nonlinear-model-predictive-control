#!/bin/bash
# Apply (idempotently) the gym's one-line sign fix to the acados source tree.
#
#   bash scripts/patch_acados.sh            # patch the source if needed
#   bash scripts/patch_acados.sh --check    # exit 0 iff the INSTALLED library carries the fix
#
# acados adds the parametric part of the constraint Hessian, d/dp [dh/dux^T (lam_u - lam_l)],
# to the parameter Jacobian of the Lagrangian gradient with sign -1, while the Lagrangian
# (QP Hessian, stationarity residual) uses +(lam_u - lam_l)^T h. The error only reaches the
# primal sensitivities when the multipliers of both sides are nonzero, i.e. for
# tau_min > 0 (smoothed solution maps), and only for constraints h(x, u; p) whose
# gradient depends on p (the paper's pendulum path constraint |theta * p| <= 1.5).
# See HARDENING.md ("smoothed sensitivities").

set -euo pipefail

ACADOS_DIR="${ACADOS_SOURCE_DIR:-/home/user/method/acados}"
SRC="${ACADOS_DIR}/acados/ocp_nlp/ocp_nlp_constraints_bgh.c"
MARKER="${ACADOS_DIR}/lib/.gym_sign_fix"
BAD='blasfeo_dgead(nx+nu, np_global, -1.0, &work->jac_lag_p_global, 0, 0, memory->jac_lag_stat_p_global, 0, 0);'
GOOD='blasfeo_dgead(nx+nu, np_global, 1.0, &work->jac_lag_p_global, 0, 0, memory->jac_lag_stat_p_global, 0, 0);'

if [ "${1:-}" = "--check" ]; then
    [ -f "${MARKER}" ] && [ -f "${ACADOS_DIR}/lib/libacados.so" ] && [ "${MARKER}" -nt "${SRC}" ]
    exit $?
fi

if grep -qF -- "${GOOD}" "${SRC}"; then
    echo "acados sign fix: source already patched"
elif grep -qF -- "${BAD}" "${SRC}"; then
    python3 - "${SRC}" "${BAD}" "${GOOD}" <<'PY'
import sys
path, bad, good = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
assert text.count(bad) == 1, "unexpected acados source: sign-fix anchor not unique"
open(path, "w", encoding="utf-8").write(text.replace(bad, good))
PY
    echo "acados sign fix: source patched"
else
    echo "ERROR: acados sign-fix anchor not found in ${SRC}" >&2
    exit 1
fi
