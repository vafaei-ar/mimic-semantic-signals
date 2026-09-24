#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ -d "$HOME/datasets/external_icu/zigong" ]; then
  ROOT="$HOME/datasets/external_icu/zigong"
elif [ -d "$HOME/datasets/zigong" ]; then
  ROOT="$HOME/datasets/zigong"
else
  echo "Zigong dataset root not found under documented local paths." >&2
  exit 2
fi

OUT="outputs/zigong_external/time_origin_audit.json"

PYTHONPATH=src .venv/bin/python src/33_audit_zigong_time_origins.py \
  --root "$ROOT" \
  --output "$OUT"
