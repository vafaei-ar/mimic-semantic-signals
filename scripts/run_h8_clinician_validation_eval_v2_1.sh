#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

LOCAL=data/real_mimic_local/h8_clinician_validation
GATE="$LOCAL/h8_governance_gate_local.json"
if [[ ! -f "$GATE" ]]; then
  echo "H8 governance gate file is missing: $GATE" >&2
  exit 2
fi

PYTHONPATH=src .venv/bin/python src/157_evaluate_h8_clinician_validation_v2_1.py \
  --base data/real_mimic_local/population_landmark12_v2_1 \
  --freeze config/v2_1_h8_clinician_validation_freeze.json \
  --governance-gate "$GATE" \
  --preparation-artifact outputs/multitask_benchmark/h8_clinician_validation_preparation_v2_1.json \
  --linkage "$LOCAL/h8_sample_linkage_v2_1_local.csv" \
  --rater-1 "$LOCAL/h8_rater_1_completed_v2_1_local.csv" \
  --rater-2 "$LOCAL/h8_rater_2_completed_v2_1_local.csv" \
  --rater-3 "$LOCAL/h8_rater_3_completed_v2_1_local.csv" \
  --semantics data/real_mimic_local/population_landmark12_v2_1/icu_death/openjev_registered_v2_1_raw_local.jsonl \
  --output outputs/multitask_benchmark/h8_clinician_validation_v2_1.json
