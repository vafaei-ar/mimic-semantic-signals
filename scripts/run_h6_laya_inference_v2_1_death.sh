#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash scripts/require_osf_registration.sh
BASE="data/real_mimic_local/population_landmark12_v2_1/icu_death"
CASES="$BASE/fixed_notes_stripped_v2_1_local.jsonl"
RAW="$BASE/laya_registered_v2_1_raw_local.jsonl"
REPORT="outputs/multitask_benchmark/laya_registered_v2_1_death.json"
PYTHONPATH=src .venv/bin/python src/37_run_laya_real_local.py   --cases "$CASES" --output "$RAW" --device cuda   --chunk-tokens 600 --chunk-overlap 100 --max-chunks 8   --progress-phase v2_1_h6_laya_death
PYTHONPATH=src .venv/bin/python src/96_summarize_population_semantic_inference.py   --raw "$RAW" --expected 7889 --model laya_registered_v2_1   --output "$REPORT"
