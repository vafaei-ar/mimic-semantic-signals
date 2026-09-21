#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python src/29_evaluate_vasopressor_incremental.py \
  --features data/real_mimic_local/vasopressor_incremental_v3_corrected/structured_features.csv \
  --semantics data/real_mimic_local/vasopressor_incremental_v3_corrected/laya_raw.jsonl \
  --output-dir outputs/vasopressor_incremental_v3_corrected/laya \
  --bootstrap-replicates 2000
