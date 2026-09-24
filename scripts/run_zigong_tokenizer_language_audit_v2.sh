#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CASES="data/real_zigong_local/ventilation24_v1/cases.jsonl"
LAYA_DIR="$HOME/.cache/mimic-semantic-signals/laya-typed-decisions-f9ab0b2"
DG_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
OUT="outputs/zigong_external/tokenizer_language_audit_v2.json"

test -f "$CASES"
test -d "$LAYA_DIR"
test -d "$DG_DIR"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 USE_TF=0 \
PYTHONPATH=src .venv/bin/python src/84_audit_zigong_tokenizers_v2.py \
  --cases "$CASES" \
  --laya-dir "$LAYA_DIR" \
  --diffusiongemma-dir "$DG_DIR" \
  --output "$OUT"
