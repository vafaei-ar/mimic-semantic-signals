#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

bash scripts/require_osf_registration.sh

PYTHONPATH=src .venv/bin/python src/153_audit_h6_note_availability_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --strip-freeze "config/v2_1_language_stripping_freeze.json" \
  --output "outputs/multitask_benchmark/h6_note_availability_audit_v2_1.json"
