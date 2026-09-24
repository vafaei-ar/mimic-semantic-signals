#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
CASES="data/real_zigong_local/ventilation24_v1/cases.jsonl"
OUT="outputs/zigong_external/diffusiongemma_tokenizer_audit_v1.json"

test -x "$ENV_DIR/bin/python"
test -f "$MODEL_DIR/config.json"
test -f "$CASES"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/85_audit_zigong_diffusiongemma_tokenizer.py \
  --cases "$CASES" \
  --model-dir "$MODEL_DIR" \
  --output "$OUT"
