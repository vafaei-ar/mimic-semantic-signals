#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec .venv/bin/python scripts/check_extension_runtime_readiness_v2_1.py \
  --output outputs/integrity/extension_runtime_readiness_v2_1.json
