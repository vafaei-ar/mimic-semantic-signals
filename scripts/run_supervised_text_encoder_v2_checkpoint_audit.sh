#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CKPT="data/local_models/postfreeze_tuned/openjev_deberta_multitask_v2/best_model.pt"
OUT="outputs/multitask_benchmark/supervised_text_encoder_v2_checkpoint_audit.json"

PYTHONPATH=src .venv/bin/python src/76_audit_supervised_text_encoder_v2_checkpoint.py \
  --checkpoint "$CKPT" \
  --output "$OUT"
