#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
BASE="data/real_mimic_local/multitask_benchmark_v1"
REPORT="outputs/multitask_benchmark/diffusiongemma_hf_native_inference_report.json"

test -x "$ENV_DIR/bin/python"
test -f "$MODEL_DIR/config.json"
test -f "$MODEL_DIR/model.safetensors.index.json"
for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  test -f "$BASE/$outcome/cases.jsonl"
done

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/66_run_diffusiongemma_hf_native_multitask.py \
  --base "$BASE" \
  --model-dir "$MODEL_DIR" \
  --report "$REPORT" \
  --expected-total 12032 \
  --max-chunks 8 \
  --max-new-tokens 256 \
  --parse-retries 2 \
  --seed 20260923
