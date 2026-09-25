#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/105_build_enhanced_structured_baseline_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --expected-counts "config/corrected_landmark12_v2_1_expected_counts.json" \
  --manifest "outputs/multitask_benchmark/enhanced_structured_baseline_features_v2_1.json"
