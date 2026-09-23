#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ENV_DIR="data/local_envs/diffusiongemma_hf_cu124"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-hf"
REPORT="outputs/multitask_benchmark/diffusiongemma_hf_native_smoke_report.json"
MODEL_REPO="google/diffusiongemma-26B-A4B-it"
PHASE="initializing"
mkdir -p "$(dirname "$REPORT")" "data/local_envs" "data/local_models"

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
  "analysis":"Native Hugging Face DiffusionGemma synthetic semantic-score smoke test",
  "status":os.environ["STATUS"],
  "phase":os.environ["PHASE"],
  "exit_code":int(os.environ["EXIT_CODE"]),
  "synthetic_only":True,
  "clinical_note_inference_performed":False,
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

PHASE="create_isolated_environment"
write_status "running" 0
if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  python3 -m venv --without-pip "$ENV_DIR"
fi
if ! "$ENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
  GET_PIP="data/local_envs/get-pip.py"
  .venv/bin/python - "$GET_PIP" <<'PY'
import sys
import urllib.request
from pathlib import Path
target=Path(sys.argv[1]).resolve()
target.parent.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen("https://bootstrap.pypa.io/get-pip.py", timeout=120) as r:
    target.write_bytes(r.read())
print(target)
PY
  "$ENV_DIR/bin/python" "$GET_PIP" "pip>=24,<26"
fi
"$ENV_DIR/bin/python" -m pip install --upgrade "pip>=24,<26"

PHASE="install_pytorch_cu124"
write_status "running" 0
"$ENV_DIR/bin/python" -m pip install \
  torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cu124

PHASE="install_transformers_stack"
write_status "running" 0
"$ENV_DIR/bin/python" -m pip install \
  transformers==5.17.0 \
  accelerate==1.15.0 \
  "huggingface_hub>=0.35" \
  safetensors \
  sentencepiece

PHASE="verify_cuda_environment"
write_status "running" 0
"$ENV_DIR/bin/python" - <<'PY'
import torch, transformers
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("transformers", transformers.__version__)
assert torch.cuda.is_available()
assert torch.cuda.device_count() >= 2
assert str(torch.version.cuda).startswith("12.4")
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), torch.cuda.get_device_capability(i))
PY

PHASE="download_official_diffusiongemma"
write_status "running" 0
HF_HUB_DISABLE_TELEMETRY=1 "$ENV_DIR/bin/python" - "$MODEL_REPO" "$MODEL_DIR" <<'PY'
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
repo=sys.argv[1]
target=Path(sys.argv[2]).resolve()
snapshot_download(repo_id=repo, local_dir=str(target))
required=["config.json","model.safetensors.index.json"]
missing=[x for x in required if not (target/x).exists()]
if missing:
    raise SystemExit(f"Downloaded model is incomplete; missing {missing}")
shards=list(target.glob("model-*.safetensors"))
if not shards:
    raise SystemExit("Downloaded model has no safetensor shards")
print(target)
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
