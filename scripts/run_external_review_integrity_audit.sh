#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ -d "$HOME/datasets/external_icu/zigong" ]; then
  ZIGONG_ROOT="$HOME/datasets/external_icu/zigong"
elif [ -d "$HOME/datasets/zigong" ]; then
  ZIGONG_ROOT="$HOME/datasets/zigong"
else
  echo "Zigong dataset root not found." >&2
  exit 2
fi

PYTHONPATH=src .venv/bin/python src/99_audit_external_review_integrity.py   --mimic-root "$HOME/datasets/MIMIC/physionet.org/files"   --local-mimic-base "data/real_mimic_local"   --eicu-root "$HOME/datasets/external_icu/eicu"   --zigong-root "$ZIGONG_ROOT"   --output "outputs/integrity/external_review_integrity_audit_v1.json"
