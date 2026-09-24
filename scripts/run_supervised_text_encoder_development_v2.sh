#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_tuning_v1"
OUT="outputs/multitask_benchmark/supervised_text_encoder_development_v2.json"
CKPT="data/local_models/postfreeze_tuned/openjev_deberta_multitask_v2"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONPATH=src .venv/bin/python src/71_train_supervised_text_encoder.py   --base "$BASE" --protocol "docs/multitask_supervised_text_encoder_protocol_v2.md" --analysis-name "Post-freeze supervised Open-Jev DeBERTa multitask upper-bound development v2"   --report "$OUT"   --checkpoint-dir "$CKPT"   --epochs 5   --note-batch-size 2   --grad-accum 8   --encoder-learning-rate 5e-6   --head-learning-rate 1e-4   --positive-class-weight 3.0   --weight-decay 0.01   --warmup-fraction 0.10   --chunk-tokens 384   --chunk-overlap 64   --max-chunks 5   --seed 20260924
