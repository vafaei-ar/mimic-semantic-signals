#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOTAL=12032

.venv/bin/python src/37_run_laya_real_local.py \
  --cases data/real_mimic_local/multitask_benchmark_v1/invasive_ventilation/cases.jsonl \
  --output data/real_mimic_local/multitask_benchmark_v1/invasive_ventilation/laya_raw.jsonl \
  --device cuda \
  --progress-offset 0 \
  --progress-total "$TOTAL" \
  --progress-phase laya_multitask

.venv/bin/python src/37_run_laya_real_local.py \
  --cases data/real_mimic_local/multitask_benchmark_v1/renal_replacement_therapy/cases.jsonl \
  --output data/real_mimic_local/multitask_benchmark_v1/renal_replacement_therapy/laya_raw.jsonl \
  --device cuda \
  --progress-offset 1460 \
  --progress-total "$TOTAL" \
  --progress-phase laya_multitask

.venv/bin/python src/37_run_laya_real_local.py \
  --cases data/real_mimic_local/multitask_benchmark_v1/icu_death/cases.jsonl \
  --output data/real_mimic_local/multitask_benchmark_v1/icu_death/laya_raw.jsonl \
  --device cuda \
  --progress-offset 3792 \
  --progress-total "$TOTAL" \
  --progress-phase laya_multitask
