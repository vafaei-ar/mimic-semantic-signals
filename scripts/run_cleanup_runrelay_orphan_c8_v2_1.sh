#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec .venv/bin/python scripts/cleanup_runrelay_orphan_c8_v2_1.py \
  --output outputs/integrity/runrelay_orphan_cleanup_c8_v2_1.json
