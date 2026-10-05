#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
test -f docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md
PYTHONPATH=src .venv/bin/python src/171_evaluate_extension_t0_v2_1.py \
  --output outputs/multitask_benchmark/extension_t0_v2_1.json
