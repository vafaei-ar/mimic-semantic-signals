#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/vasopressor_incremental_v5_complete_matched/robustness
.venv/bin/python src/47_evaluate_treatment_language_sensitivity.py \
  --features data/real_mimic_local/vasopressor_incremental_v5_complete_matched/structured_features.csv \
  --cases data/real_mimic_local/vasopressor_incremental_v5_complete_matched/cases.jsonl \
  --openjev data/real_mimic_local/vasopressor_incremental_v5_complete_matched/open_jev_raw.jsonl \
  --laya data/real_mimic_local/vasopressor_incremental_v5_complete_matched/laya_raw.jsonl \
  --output outputs/vasopressor_incremental_v5_complete_matched/robustness/treatment_language_sensitivity_report.json \
  --folds 5 \
  --repeats 20 \
  --bootstrap-replicates 2000
