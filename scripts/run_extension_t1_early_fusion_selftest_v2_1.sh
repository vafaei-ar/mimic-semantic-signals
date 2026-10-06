#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src .venv/bin/python src/176_evaluate_extension_t1_early_fusion_v2_1.py \
  --outcome invasive_ventilation --mode timing \
  --output /tmp/extension_t1_early_fusion_selftest_unused.json --self-test
