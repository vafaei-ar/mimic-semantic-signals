#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/vasopressor_incremental_v5_complete_matched/robustness
.venv/bin/python src/46_evaluate_nonlinear_rf_robustness.py \
  --features data/real_mimic_local/vasopressor_incremental_v5_complete_matched/structured_features.csv \
  --openjev data/real_mimic_local/vasopressor_incremental_v5_complete_matched/open_jev_raw.jsonl \
  --laya data/real_mimic_local/vasopressor_incremental_v5_complete_matched/laya_raw.jsonl \
  --output outputs/vasopressor_incremental_v5_complete_matched/robustness/nonlinear_rf_structured_report.json \
  --folds 5 \
  --repeats 10 \
  --bootstrap-replicates 2000 \
  --n-estimators 500
