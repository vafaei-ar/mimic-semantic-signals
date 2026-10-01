#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
BASE="data/real_mimic_local/population_landmark12_v2_1/renal_replacement_therapy"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/135_run_registered_diffusiongemma_v2_1.py \
  --cases "$BASE/fixed_notes_stripped_v2_1_local.jsonl" \
  --model-dir "$MODEL_DIR" \
  --raw-output "$BASE/diffusiongemma_registered_v2_1_raw_local.jsonl" \
  --report "outputs/multitask_benchmark/diffusiongemma_registered_v2_1_rrt.json" \
  --expected 7709 --max-chunks 8 --max-new-tokens 256 --parse-retries 2 --seed 20260924 \
  --progress-phase v2_1_h6_diffusiongemma_rrt
