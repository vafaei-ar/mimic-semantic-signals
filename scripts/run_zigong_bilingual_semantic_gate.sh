#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CFG="configs/zigong_bilingual_semantic_gate_v1.json"
LAYA_DIR="$HOME/.cache/mimic-semantic-signals/laya-typed-decisions-f9ab0b2"
DG_ENV="data/local_envs/diffusiongemma_hf_cu124"
DG_MODEL="data/local_models/diffusiongemma-26B-A4B-it-hf"
JL_RAW="outputs/zigong_external/bilingual_gate_jev_laya_raw.json"
DG_RAW="outputs/zigong_external/bilingual_gate_diffusiongemma_raw.json"
OUT="outputs/zigong_external/bilingual_semantic_gate_v1.json"

test -f "$CFG"
test -d "$LAYA_DIR"
test -x "$DG_ENV/bin/python"
test -f "$DG_MODEL/config.json"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 USE_TF=0 \
PYTHONPATH=src .venv/bin/python src/86_run_zigong_bilingual_gate_jev_laya.py \
  --config "$CFG" \
  --laya-dir "$LAYA_DIR" \
  --output "$JL_RAW"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$DG_ENV/bin/python" src/87_run_zigong_bilingual_gate_diffusiongemma.py \
  --config "$CFG" \
  --model-dir "$DG_MODEL" \
  --output "$DG_RAW" \
  --seed 20260924 \
  --max-new-tokens 256 \
  --parse-retries 2

PYTHONPATH=src .venv/bin/python src/88_summarize_zigong_bilingual_gate.py \
  --config "$CFG" \
  --jev-laya "$JL_RAW" \
  --diffusiongemma "$DG_RAW" \
  --output "$OUT"
