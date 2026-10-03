#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/set_hgb_thread_env_v2_1.sh
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/155_evaluate_h7_patient_shuffled_openjev_v2_1.py \
  --analysis ventilation \
  --base data/real_mimic_local/population_landmark12_v2_1 \
  --split-manifest outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json \
  --context-freeze config/v2_1_context_feature_freeze.json \
  --analysis-populations config/v2_1_analysis_population_contract.json \
  --preanalysis-clarifications config/v2_1_preanalysis_clarifications_2026-09-25.json \
  --output outputs/multitask_benchmark/h7_patient_shuffled_v2_1_ventilation.json
