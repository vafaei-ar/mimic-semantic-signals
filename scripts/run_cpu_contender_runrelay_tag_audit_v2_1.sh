#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec .venv/bin/python scripts/audit_cpu_contender_runrelay_tags_v2_1.py \
  --output outputs/integrity/cpu_contender_runrelay_tag_audit_v2_1.json
