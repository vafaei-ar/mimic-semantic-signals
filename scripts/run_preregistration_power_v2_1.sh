#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/110_simulate_preregistration_power_v2_1.py \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --output "outputs/multitask_benchmark/preregistration_power_v2_1.json"
