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

LOCAL_OUT="data/real_zigong_local/ventilation24_v1"
MANIFEST="outputs/zigong_external/ventilation24_cohort_manifest.json"

PYTHONPATH=src .venv/bin/python src/82_build_zigong_ventilation24_cohort.py \
  --root "$ROOT" \
  --local-output-dir "$LOCAL_OUT" \
  --manifest "$MANIFEST" \
  --washout-hours 6 \
  --horizon-hours 24 \
  --controls-per-case 3 \
  --matching-seed 20260924 \
  --preferred-match-hours 6 \
  --max-match-hours 12
