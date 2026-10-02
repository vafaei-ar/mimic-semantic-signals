#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/set_hgb_thread_env_v2_1.sh
bash scripts/require_osf_registration.sh
BASE="data/real_mimic_local/population_landmark12_v2_1"
PYTHONPATH=src .venv/bin/python src/141_evaluate_h6_broad_ventilation_v2_1.py \
  --base "$BASE" \
  --broad-contract "config/v2_1_h6_broad_ventilation_contract.json" \
  --preparation-manifest "outputs/multitask_benchmark/h6_broad_ventilation_preparation_v2_1.json" \
  --context-freeze "config/v2_1_context_feature_freeze.json" \
  --preanalysis-clarifications "config/v2_1_preanalysis_clarifications_2026-09-25.json" \
  --semantics "$BASE/invasive_ventilation_any_support_sensitivity/openjev_registered_v2_1_broad_raw_local.jsonl" \
  --output "outputs/multitask_benchmark/h6_broad_openjev_v2_1_ventilation.json"
