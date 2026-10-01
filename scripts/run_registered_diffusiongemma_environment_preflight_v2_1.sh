#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
REPORT="outputs/integrity/v2_1_registered_diffusiongemma_environment_preflight.json"
test -x "$ENV_DIR/bin/python"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/134_audit_registered_diffusiongemma_environment_v2_1.py \
  --model-dir "$MODEL_DIR" \
  --schema "src/semantic_schema.py" \
  --output "$REPORT" \
  --max-new-tokens 256
