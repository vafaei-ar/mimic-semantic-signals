#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/112_audit_death_source_strategy_v2_1.py \
  --local-root "data/real_mimic_local/population_landmark12_v2_1" \
  --output "outputs/multitask_benchmark/death_source_strategy_audit_v2_1.json"
