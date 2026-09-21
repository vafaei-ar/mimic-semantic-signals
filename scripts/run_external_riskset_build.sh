#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

.venv/bin/python src/39_build_external_structured_risksets.py \
  --eicu-root "$HOME/datasets/external_icu/eicu" \
  --nwicu-root "$HOME/datasets/external_icu/nwicu" \
  --output-dir outputs/external_validation \
  --controls-per-case 3 \
  --prediction-horizon-hours 6 \
  --vital-lookback-hours 6 \
  --lab-lookback-hours 24
