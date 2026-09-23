#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
REPORT="outputs/multitask_benchmark/diffusiongemma_hf_native_graded_calibration.json"

test -x "$ENV_DIR/bin/python"
test -f "$MODEL_DIR/config.json"
test -f "$MODEL_DIR/model.safetensors.index.json"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/64_calibrate_diffusiongemma_hf_native.py \
  --model-dir "$MODEL_DIR" \
  --report "$REPORT" \
  --seed 20260923 \
  --max-new-tokens 256
