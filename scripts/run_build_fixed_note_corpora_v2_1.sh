#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/115_build_fixed_note_corpora_v2_1.py \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --strip-freeze "config/v2_1_language_stripping_freeze.json" \
  --output "outputs/multitask_benchmark/fixed_note_corpora_v2_1.json"
