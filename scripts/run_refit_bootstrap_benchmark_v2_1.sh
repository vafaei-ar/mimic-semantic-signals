#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PYTHONPATH=src .venv/bin/python src/111_benchmark_refit_bootstrap_v2_1.py \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --output "outputs/multitask_benchmark/refit_bootstrap_benchmark_v2_1.json" \
  --runtime-replicates 1 \
  --null-replicates 8
