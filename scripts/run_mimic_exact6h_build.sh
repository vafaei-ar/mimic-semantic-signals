#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

.venv/bin/python src/41_build_mimic_exact6h_structured.py \
  --root "$HOME/datasets/MIMIC/physionet.org/files" \
  --output-dir outputs/external_validation \
  --controls-per-case 3 \
  --prediction-horizon-hours 6 \
  --vital-lookback-hours 6 \
  --lab-lookback-hours 24
