#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src .venv/bin/python src/161_validate_submission_minimal_analyses_v2_1.py \
  --output outputs/integrity/submission_minimal_analysis_validation_v2_1.json
