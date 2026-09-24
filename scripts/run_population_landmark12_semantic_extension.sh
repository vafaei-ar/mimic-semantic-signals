#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/population_landmark12_v1"
SEM="$BASE/semantic_unique_notes_v1"
STRUCT_REF="outputs/multitask_benchmark/population_landmark12_structured_calibration_v1.json"
OUT="outputs/multitask_benchmark/population_landmark12_semantic_extension_v1.json"

test -f "$SEM/open_jev_raw.jsonl"
test -f "$SEM/laya_raw.jsonl"
test -f "$SEM/case_to_note_mapping.jsonl"
test -f "$STRUCT_REF"

PYTHONPATH=src .venv/bin/python src/97_evaluate_population_landmark12_semantic_extension.py \
  --base "$BASE" \
  --semantic-base "$SEM" \
  --structured-reference "$STRUCT_REF" \
  --output "$OUT" \
  --folds 5 \
  --bootstrap-replicates 1000 \
  --max-features 10000
