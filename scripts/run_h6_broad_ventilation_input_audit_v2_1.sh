#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

BASE="data/real_mimic_local/population_landmark12_v2_1"
PYTHONPATH=src .venv/bin/python src/139_audit_h6_broad_ventilation_inputs_v2_1.py \
  --base "$BASE" \
  --output "outputs/multitask_benchmark/h6_broad_ventilation_input_audit_v2_1.json"
