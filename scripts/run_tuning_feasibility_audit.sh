#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BASE="data/real_mimic_local/multitask_benchmark_v1"
OUT="outputs/multitask_benchmark/tuning_feasibility_audit_v1.json"

for outcome in invasive_ventilation renal_replacement_therapy icu_death; do
  test -f "$BASE/$outcome/snapshot_index_local.csv"
done

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONPATH=src .venv/bin/python src/69_audit_tuning_feasibility.py   --base "$BASE"   --output "$OUT"   --seed 20260924
