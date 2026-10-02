#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/set_hgb_thread_env_v2_1.sh
bash scripts/require_osf_registration.sh
BASE="data/real_mimic_local/population_landmark12_v2_1"
PYTHONPATH=src .venv/bin/python src/145_evaluate_h6_chartevents_storetime_death_v2_1.py \
  --base "$BASE" \
  --split-manifest "outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json" \
  --context-freeze "config/v2_1_context_feature_freeze.json" \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --preanalysis-clarifications "config/v2_1_preanalysis_clarifications_2026-09-25.json" \
  --semantics "$BASE/icu_death/openjev_registered_v2_1_raw_local.jsonl" \
  --output "outputs/multitask_benchmark/h6_chartevents_storetime_v2_1_death.json"
