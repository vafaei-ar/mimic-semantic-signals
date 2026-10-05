#!/usr/bin/env bash
set -euo pipefail

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1

exec /home/asadr/miniconda3/envs/lc/bin/python \
  src/173_cache_extension_embeddings_v2_1.py \
  --output outputs/multitask_benchmark/extension_embedding_cache_v2_1.json \
  --device cuda \
  --note-batch-size 32 \
  --chunk-batch-size 64
