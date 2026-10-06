#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/176_evaluate_extension_t1_early_fusion_v2_1.py \
  --outcome icu_death --mode timing \
  --output outputs/multitask_benchmark/extension_t1_early_fusion_timing_v2_1_death.json
