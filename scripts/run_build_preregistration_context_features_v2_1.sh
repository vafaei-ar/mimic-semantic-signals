#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/114_build_preregistration_context_features_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --context-freeze "config/v2_1_context_feature_freeze.json" \
  --output "outputs/multitask_benchmark/preregistration_context_features_v2_1.json"
