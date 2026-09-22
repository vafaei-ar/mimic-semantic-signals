#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p outputs/vasopressor_incremental_v5_complete_matched/robustness
.venv/bin/python src/48_evaluate_lead_time_sensitivity.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --features data/real_mimic_local/vasopressor_incremental_v5_complete_matched/structured_features.csv \
  --cases data/real_mimic_local/vasopressor_incremental_v5_complete_matched/cases.jsonl \
  --openjev data/real_mimic_local/vasopressor_incremental_v5_complete_matched/open_jev_raw.jsonl \
  --laya data/real_mimic_local/vasopressor_incremental_v5_complete_matched/laya_raw.jsonl \
  --output outputs/vasopressor_incremental_v5_complete_matched/robustness/lead_time_sensitivity_report.json \
  --thresholds-hours 0 1 2 3 4 \
  --folds 5 \
  --repeats 20 \
  --bootstrap-replicates 2000
