#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src .venv/bin/python src/162_summarize_submission_exploratory_v2_1.py \
  --input outputs/multitask_benchmark/submission_exploratory_explanatory_v2_1.json \
  --output outputs/multitask_benchmark/submission_exploratory_explanatory_summary_v2_1.json
