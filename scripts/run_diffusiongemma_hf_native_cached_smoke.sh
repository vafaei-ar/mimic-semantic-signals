#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
REPORT="outputs/multitask_benchmark/diffusiongemma_hf_native_smoke_report.json"
PHASE="initializing"
mkdir -p "$(dirname "$REPORT")"

write_status() {
  local status="$1"
  local exit_code="${2:-0}"
  STATUS="$status" EXIT_CODE="$exit_code" PHASE="$PHASE" REPORT="$REPORT" MODEL_DIR="$MODEL_DIR" \
  .venv/bin/python - <<'PY'
import json, os
from pathlib import Path
model=Path(os.environ["MODEL_DIR"])
files=[p for p in model.rglob("*") if p.is_file()] if model.exists() else []
size=sum(p.stat().st_size for p in files)
payload={
  "analysis":"Native Hugging Face DiffusionGemma cached synthetic semantic-score smoke test",
  "status":os.environ["STATUS"],
  "phase":os.environ["PHASE"],
  "exit_code":int(os.environ["EXIT_CODE"]),
  "synthetic_only":True,
  "clinical_note_inference_performed":False,
  "network_required":False,
  "model":"google/diffusiongemma-26B-A4B-it",
  "backend":"transformers_native_bf16",
  "model_directory_exists":model.exists(),
  "model_file_count":len(files),
  "model_directory_size_gb":round(size/(1024**3),3),
}
Path(os.environ["REPORT"]).write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
PY
}
write_status "running" 0

on_exit() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    write_status "failed" "$rc" || true
  fi
  exit "$rc"
}
trap on_exit EXIT

PHASE="verify_cached_environment"
write_status "running" 0
test -x "$ENV_DIR/bin/python"
"$ENV_DIR/bin/python" - <<'PY'
import torch, transformers
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("transformers", transformers.__version__)
assert torch.__version__.startswith("2.5.1")
assert str(torch.version.cuda).startswith("12.4")
assert transformers.__version__ == "5.17.0"
assert torch.cuda.is_available()
assert torch.cuda.device_count() >= 2
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), torch.cuda.get_device_capability(i))
PY

PHASE="verify_cached_model"
write_status "running" 0
"$ENV_DIR/bin/python" - "$MODEL_DIR" <<'PY'
import sys
from pathlib import Path
model=Path(sys.argv[1]).resolve()
required=["config.json","model.safetensors.index.json"]
missing=[x for x in required if not (model/x).exists()]
if missing:
    raise SystemExit(f"Cached model incomplete; missing {missing}")
shards=list(model.glob("model-*.safetensors"))
if not shards:
    raise SystemExit("Cached model has no safetensor shards")
size=sum(p.stat().st_size for p in model.rglob("*") if p.is_file())
if size < 40 * 1024**3:
    raise SystemExit(f"Cached model unexpectedly small: {size/(1024**3):.2f} GiB")
print(model)
print(f"{len(shards)} shards, {size/(1024**3):.3f} GiB")
PY

PHASE="native_hf_synthetic_smoke"
write_status "running" 0
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
PYTHONPATH=src "$ENV_DIR/bin/python" src/63_smoke_diffusiongemma_hf_native.py \
  --model-dir "$MODEL_DIR" \
  --report "$REPORT" \
  --seed 20260923 \
  --max-new-tokens 256

PHASE="complete"
trap - EXIT
