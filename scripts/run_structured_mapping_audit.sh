#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

.venv/bin/python src/40_audit_structured_mappings.py \
  --nwicu-root "$HOME/datasets/external_icu/nwicu" \
  --mimic-root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output outputs/external_validation/structured_mapping_audit.json
