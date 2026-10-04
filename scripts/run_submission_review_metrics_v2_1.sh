#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
PYTHONPATH=src .venv/bin/python src/163_summarize_submission_review_metrics_v2_1.py \
  --output outputs/multitask_benchmark/submission_review_metrics_v2_1.json
