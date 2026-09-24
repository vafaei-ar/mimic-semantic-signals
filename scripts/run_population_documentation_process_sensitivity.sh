#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/population_landmark12_v1"
SEM="$BASE/semantic_unique_notes_v1"
OUT="outputs/multitask_benchmark/population_documentation_process_sensitivity_v1.json"

test -f "$SEM/open_jev_raw.jsonl"
test -f "$SEM/laya_raw.jsonl"
test -f "$SEM/case_to_note_mapping.jsonl"

PYTHONPATH=src .venv/bin/python src/98_evaluate_population_documentation_process_sensitivity.py   --base "$BASE"   --semantic-base "$SEM"   --output "$OUT"   --folds 5   --bootstrap-replicates 1000   --max-features 10000
