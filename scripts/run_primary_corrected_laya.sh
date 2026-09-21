#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python src/37_run_laya_real_local.py \
  --cases data/real_mimic_local/vasopressor_incremental_v3_corrected/cases.jsonl \
  --output data/real_mimic_local/vasopressor_incremental_v3_corrected/laya_raw.jsonl \
  --device cuda
