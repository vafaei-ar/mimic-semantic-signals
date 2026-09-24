#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
CASES="data/real_zigong_local/ventilation24_v1/cases.jsonl"
RAW="data/real_zigong_local/ventilation24_v1/diffusiongemma_raw.jsonl"
REPORT="outputs/zigong_external/diffusiongemma_inference_report_v1.json"

test -x "$ENV_DIR/bin/python"
test -f "$MODEL_DIR/config.json"
test -f "$CASES"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/89_run_zigong_diffusiongemma_inference.py \
  --cases "$CASES" \
  --model-dir "$MODEL_DIR" \
  --raw-output "$RAW" \
  --report "$REPORT" \
  --expected-total 340 \
  --chunk-tokens 977 \
  --chunk-overlap 97 \
  --max-chunks 8 \
  --max-new-tokens 256 \
  --parse-retries 2 \
  --seed 20260924
