#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/146_prepare_h6_lab_lag_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --expected-counts "config/corrected_landmark12_v2_1_expected_counts.json" \
  --output "outputs/multitask_benchmark/h6_lab_lag_preparation_v2_1.json"
