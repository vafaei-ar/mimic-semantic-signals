#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
BASE="data/real_mimic_local/population_landmark12_v2_1"
PYTHONPATH=src .venv/bin/python src/159_audit_semantic_alignment_v2_1.py \
  --base "$BASE" \
  --analysis-populations config/v2_1_analysis_population_contract.json \
  --output outputs/multitask_benchmark/submission_semantic_alignment_audit_v2_1.json
