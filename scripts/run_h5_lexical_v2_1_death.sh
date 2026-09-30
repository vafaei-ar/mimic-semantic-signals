#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
BASE="data/real_mimic_local/population_landmark12_v2_1"
PYTHONPATH=src .venv/bin/python src/126_evaluate_h5_lexical_v2_1.py \
  --base "$BASE" \
  --outcome icu_death \
  --split-manifest outputs/multitask_benchmark/enhanced_structured_cv_splits_v2_1.json \
  --context-freeze config/v2_1_context_feature_freeze.json \
  --analysis-populations config/v2_1_analysis_population_contract.json \
  --preanalysis-clarifications config/v2_1_preanalysis_clarifications_2026-09-25.json \
  --notes "$BASE/icu_death/fixed_notes_stripped_v2_1_local.jsonl" \
  --semantics "$BASE/icu_death/openjev_registered_v2_1_raw_local.jsonl" \
  --output outputs/multitask_benchmark/h5_lexical_v2_1_death.json
