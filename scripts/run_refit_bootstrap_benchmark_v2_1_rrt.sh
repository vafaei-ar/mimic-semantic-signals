#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/set_hgb_thread_env_v2_1.sh

PYTHONPATH=src .venv/bin/python src/111_benchmark_refit_bootstrap_v2_1.py \
  --analysis-populations "config/v2_1_analysis_population_contract.json" \
  --outcome renal_replacement_therapy \
  --output "outputs/multitask_benchmark/refit_bootstrap_benchmark_v2_1_rrt.json" \
  --runtime-replicates 1 \
  --null-trials 2000 \
  --null-bootstrap-replicates 500
