#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/set_hgb_thread_env_v2_1.sh

bash scripts/require_osf_registration.sh

PYTHONPATH=src .venv/bin/python src/117_evaluate_rich_comparator_v2_1.py \
  --base "data/real_mimic_local/population_landmark12_v2_1" \
  --split-manifest "outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json" \
  --context-freeze "config/v2_1_context_feature_freeze.json" \
  --output "outputs/multitask_benchmark/rich_comparator_evaluation_v2_1_ventilation.json" \
  --outcome invasive_ventilation
