#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/140_prepare_h6_broad_ventilation_v2_1.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --base "data/real_mimic_local/population_landmark12_v2_1" \
  --contract "config/v2_1_h6_broad_ventilation_contract.json" \
  --context-freeze "config/v2_1_context_feature_freeze.json" \
  --strip-freeze "config/v2_1_language_stripping_freeze.json" \
  --output "outputs/multitask_benchmark/h6_broad_ventilation_preparation_v2_1.json"
