#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-NVFP4"
OUT="outputs/multitask_benchmark/local_djev_setup_report.json"
mkdir -p "$MODEL_DIR" "$(dirname "$OUT")"

echo "[djev-setup] Pulling local serving image"
docker pull ghcr.io/taeold/djev-run:latest

echo "[djev-setup] Downloading public NVIDIA DiffusionGemma NVFP4 weights"
.venv/bin/python - "$MODEL_DIR" <<'PY'
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
model_dir=Path(sys.argv[1]).resolve()
snapshot_download(
    repo_id="nvidia/diffusiongemma-26B-A4B-it-NVFP4",
    local_dir=str(model_dir),
)
print(model_dir)
PY

.venv/bin/python - "$MODEL_DIR" "$OUT" <<'PY'
import json, subprocess, sys
from pathlib import Path
model=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
files=[p for p in model.rglob("*") if p.is_file()]
size=sum(p.stat().st_size for p in files)
safe=[p for p in files if p.suffix==".safetensors"]
inspect=subprocess.run(
    ["docker","image","inspect","ghcr.io/taeold/djev-run:latest","--format","{{.Id}}"],
    capture_output=True,text=True,check=False,
)
required=["config.json","tokenizer.json","model.safetensors.index.json"]
report={
    "analysis":"Local DiffusionGemma-Jev setup",
    "local_only_target":True,
    "model_repo":"nvidia/diffusiongemma-26B-A4B-it-NVFP4",
    "model_file_count":len(files),
    "model_size_gb":round(size/(1024**3),3),
    "safetensors_files":len(safe),
    "required_files_present":{x:(model/x).exists() for x in required},
    "container_image":"ghcr.io/taeold/djev-run:latest",
    "container_image_id":inspect.stdout.strip() if inspect.returncode==0 else None,
    "credentialed_note_inference_performed":False,
}
if len(safe)<2 or not all(report["required_files_present"].values()):
    raise SystemExit("Local model download incomplete")
out.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
PY
