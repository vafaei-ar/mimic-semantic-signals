#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/178_evaluate_extension_t1_decomposition_v2_1.py \
  --outcome renal_replacement_therapy --mode timing \
  --output outputs/multitask_benchmark/extension_t1_decomposition_timing_v2_1_rrt.json
