#!/usr/bin/env bash
set -euo pipefail

REGISTRATION_RECORD="docs/registration/osf_registration.json"
if [[ ! -f "$REGISTRATION_RECORD" ]]; then
  echo "CONFIRMATORY ANALYSIS LOCKED: $REGISTRATION_RECORD does not exist." >&2
  echo "Submit the post-review OSF registration before running real-label predictive evaluation." >&2
  exit 23
fi

PYTHONPATH=src .venv/bin/python -c 'from registration_gate import require_osf_registration; require_osf_registration()'
