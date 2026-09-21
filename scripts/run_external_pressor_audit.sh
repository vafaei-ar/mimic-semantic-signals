#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

.venv/bin/python src/38_audit_external_pressor_endpoints.py \
  --eicu-root "$HOME/datasets/external_icu/eicu" \
  --nwicu-root "$HOME/datasets/external_icu/nwicu" \
  --output outputs/external_validation/external_pressor_endpoint_audit.json
