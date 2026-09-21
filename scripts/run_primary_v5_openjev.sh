#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python src/22_run_open_jev_real_local.py \
  --cases data/real_mimic_local/vasopressor_incremental_v5_complete_matched/cases.jsonl \
  --output data/real_mimic_local/vasopressor_incremental_v5_complete_matched/open_jev_raw.jsonl \
  --device cuda
