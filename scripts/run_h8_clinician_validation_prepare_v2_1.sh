#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

PYTHONPATH=src .venv/bin/python src/156_prepare_h8_clinician_validation_v2_1.py \
  --base data/real_mimic_local/population_landmark12_v2_1 \
  --freeze config/v2_1_h8_clinician_validation_freeze.json \
  --corpus-contract config/v2_1_fixed_note_corpus_result_contract.json \
  --output outputs/multitask_benchmark/h8_clinician_validation_preparation_v2_1.json
