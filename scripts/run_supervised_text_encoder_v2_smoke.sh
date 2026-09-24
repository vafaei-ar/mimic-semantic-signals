#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_tuning_v1"
OUT="outputs/multitask_benchmark/supervised_text_encoder_v2_smoke.json"
CKPT="data/local_models/postfreeze_tuned/openjev_deberta_multitask_v2_smoke"

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONPATH=src .venv/bin/python src/71_train_supervised_text_encoder.py   --base "$BASE"   --report "$OUT"   --checkpoint-dir "$CKPT"   --epochs 1   --note-batch-size 2   --grad-accum 2   --encoder-learning-rate 5e-6   --head-learning-rate 1e-4   --positive-class-weight 3.0   --limit-notes-per-outcome 24   --max-train-batches 6   --no-save   --seed 20260924
