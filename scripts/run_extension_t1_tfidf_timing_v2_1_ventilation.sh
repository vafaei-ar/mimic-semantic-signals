#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
test -f docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md
PYTHONPATH=src .venv/bin/python src/172_evaluate_extension_t1_tfidf_v2_1.py \
  --outcome invasive_ventilation \
  --mode timing \
  --output outputs/multitask_benchmark/extension_t1_tfidf_timing_v2_1_ventilation.json
