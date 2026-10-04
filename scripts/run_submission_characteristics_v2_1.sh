#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/164_build_submission_characteristics_v2_1.py \
  --base data/real_mimic_local/population_landmark12_v2_1 \
  --output outputs/manuscript/paper1_table1_characteristics_v2_1.json
