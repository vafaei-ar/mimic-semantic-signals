#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/population_landmark12_v1"
LOCAL="data/real_mimic_local/population_landmark12_v1/semantic_unique_notes_v1"
OUT="outputs/multitask_benchmark/population_landmark12_note_workload_v1.json"

PYTHONPATH=src .venv/bin/python src/95_build_population_landmark12_note_corpus.py \
  --base "$BASE" \
  --local-output "$LOCAL" \
  --manifest "$OUT"
