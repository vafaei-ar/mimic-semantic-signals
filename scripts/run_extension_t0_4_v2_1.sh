#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/177_evaluate_extension_t0_4_support_timing_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output outputs/multitask_benchmark/extension_t0_4_support_timing_v2_1.json
