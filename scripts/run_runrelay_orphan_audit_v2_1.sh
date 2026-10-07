#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec .venv/bin/python scripts/audit_runrelay_orphans_v2_1.py \
  --output outputs/integrity/runrelay_orphan_audit_v2_1.json
