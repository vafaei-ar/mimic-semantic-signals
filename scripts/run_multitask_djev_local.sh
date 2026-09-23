#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MODEL_DIR="$(pwd)/data/local_models/diffusiongemma-26B-A4B-it-NVFP4"
NAME="mimic-djev-local"
NET="mimic-djev-internal"
TOTAL=12032

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

docker network create --internal "$NET" >/dev/null

docker run -d --rm \
  --name "$NAME" \
  --gpus "device=0" \
  --shm-size=32g \
  --network "$NET" \
  -p 127.0.0.1:8011:8080 \
  -v "$MODEL_DIR:/mnt/gcs/dgemma:ro" \
  -e CANVAS=128 \
  -e MAX_SEQS=16 \
  -e MAX_MODEL_LEN=4096 \
  -e GPU_UTIL=0.40 \
  -e KV_CACHE_GB=2 \
  -e DISABLE_MM=1 \
  -e TORCH_COMPILE_DISABLE=1 \
  -e VLLM_NO_USAGE_STATS=1 \
  ghcr.io/taeold/djev-run:latest >/dev/null

echo "[djev] Waiting for local-only server health"
.venv/bin/python - <<'PY'
import json,time,urllib.request
url="http://127.0.0.1:8011/health"
last=None
for _ in range(180):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:
            data=json.loads(r.read().decode())
            if r.status==200 and data.get("status")=="ok":
                print(json.dumps(data))
                break
    except Exception as e:
        last=repr(e)
    time.sleep(2)
else:
    raise SystemExit(f"Local djev server failed health check: {last}")
PY

echo "[djev] Synthetic smoke test"
.venv/bin/python - <<'PY'
import json,urllib.request
payload={
  "model":"dgemma",
  "state":{"clinical_note":"Patient is stable and comfortable with no new acute concern."},
  "questions":{"stable":{"type":"noul","instructions":"Does clinical_note indicate reassuring stability?","criteria":{"true":"stable or reassuring","false":"not stable"}}},
}
req=urllib.request.Request("http://127.0.0.1:8011/v1/systemone",data=json.dumps(payload).encode(),headers={"content-type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=120) as r:
    data=json.loads(r.read().decode())
if "stable" not in data and "answers" not in data:
    raise SystemExit(f"Unexpected Jev response shape: {type(data)}")
print("synthetic smoke ok")
PY

BASE=data/real_mimic_local/multitask_benchmark_v1
.venv/bin/python src/16_run_jev_compatible_local.py \
  --cases "$BASE/invasive_ventilation/cases.jsonl" \
  --output "$BASE/invasive_ventilation/djev_raw.jsonl" \
  --endpoint http://127.0.0.1:8011/v1/systemone \
  --model dgemma \
  --progress-offset 0 --progress-total "$TOTAL" --progress-phase djev_multitask

.venv/bin/python src/16_run_jev_compatible_local.py \
  --cases "$BASE/renal_replacement_therapy/cases.jsonl" \
  --output "$BASE/renal_replacement_therapy/djev_raw.jsonl" \
  --endpoint http://127.0.0.1:8011/v1/systemone \
  --model dgemma \
  --progress-offset 1460 --progress-total "$TOTAL" --progress-phase djev_multitask

.venv/bin/python src/16_run_jev_compatible_local.py \
  --cases "$BASE/icu_death/cases.jsonl" \
  --output "$BASE/icu_death/djev_raw.jsonl" \
  --endpoint http://127.0.0.1:8011/v1/systemone \
  --model dgemma \
  --progress-offset 3792 --progress-total "$TOTAL" --progress-phase djev_multitask
