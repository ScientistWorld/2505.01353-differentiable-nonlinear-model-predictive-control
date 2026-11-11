#!/usr/bin/env python3
"""Score genuine tighter-solver runs with their original FD error procedure.

Reuses actual solver outputs from the preceding job. Unlike better_tol10/12,
these variants do not freeze the lower-precision nominal solver's FD value.
Both retain its comparison-baseline error, so the anchors do not buy any gain.
"""
import sys
from common import AUDIT, PENDULUM, EXACT, load, reference, publish

name = sys.argv[1]
source = name.replace('better_native_', 'better_')
diagnostics = load(AUDIT / source / 'diagnostics.json')
artifact = reference()
artifact['experiments'][PENDULUM]['results'][EXACT] = diagnostics['native_errors'][EXACT]
publish(name, artifact)
