#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

REPORT="outputs/multitask_benchmark/djev_cuda12_fp8_smoke_report.json"
BUILD_ROOT="data/local_build/djev_cuda12_fp8"
MODEL_DIR="data/local_models/diffusiongemma-26B-A4B-it-FP8-dynamic"
VLLM_SRC="$BUILD_ROOT/vllm"
DJEV_SRC="$BUILD_ROOT/djev-spark"
DERIVE_CTX="$BUILD_ROOT/server-image"
VLLM_REF="6591b093b29536dd070c6af3628b734025c53e23"
DJEV_REF="1444f3e927f83ba508e5b28a4fd4fdd9ecd0976b"
MODEL_REPO="RedHatAI/diffusiongemma-26B-A4B-it-FP8-dynamic"
VLLM_IMAGE="local/djev-vllm-cu128-sm89:${VLLM_REF:0:12}"
SERVER_IMAGE="local/djev-cu128-fp8:${VLLM_REF:0:12}"
CUDA_IMAGE="nvidia/cuda:12.8.2-base-ubuntu24.04"
NAME="mimic-djev-fp8-smoke"
NET="mimic-djev-fp8-smoke-net"
PHASE="initializing"
mkdir -p "$(dirname "$REPORT")" "$BUILD_ROOT" "$MODEL_DIR"

GPU_DEVICE="${NVIDIA_VISIBLE_DEVICES:-${CUDA_VISIBLE_DEVICES:-0}}"
GPU_DEVICE="${GPU_DEVICE%%,*}"
if [[ -z "$GPU_DEVICE" || "$GPU_DEVICE" == "all" ]]; then
  GPU_DEVICE="0"
fi

docker_sg() {
  local cmd
  printf -v cmd '%q ' docker "$@"
  sg docker -c "$cmd"
}

write_report() {
  local status="$1"
  local exit_code="${2:-0}"
  STATUS="$status" EXIT_CODE="$exit_code" PHASE="$PHASE" REPORT="$REPORT" \
  MODEL_DIR="$MODEL_DIR" MODEL_REPO="$MODEL_REPO" VLLM_REF="$VLLM_REF" DJEV_REF="$DJEV_REF" \
  VLLM_IMAGE="$VLLM_IMAGE" SERVER_IMAGE="$SERVER_IMAGE" CUDA_IMAGE="$CUDA_IMAGE" \
  .venv/bin/python - <<'PY'
import json, os
from pathlib import Path
model=Path(os.environ["MODEL_DIR"])
files=[p for p in model.rglob("*") if p.is_file()] if model.exists() else []
size=sum(p.stat().st_size for p in files)
report={
    "analysis":"CUDA-12.8 / Ada FP8 DiffusionGemma-Jev synthetic smoke test",
    "status":os.environ["STATUS"],
    "phase":os.environ["PHASE"],
    "exit_code":int(os.environ["EXIT_CODE"]),
    "clinical_note_inference_performed":False,
    "synthetic_only":True,
    "host_driver_expected":"555.42.02",
    "target_cuda_runtime":"12.8.2",
    "target_gpu_arch":"sm89 (RTX 6000 Ada)",
    "vllm_fork_commit":os.environ["VLLM_REF"],
    "djev_spark_commit":os.environ["DJEV_REF"],
    "model_repo":os.environ["MODEL_REPO"],
    "model_directory_exists":model.exists(),
    "model_file_count":len(files),
    "model_size_gb":round(size/(1024**3),3),
    "cuda_preflight_image":os.environ["CUDA_IMAGE"],
    "vllm_image":os.environ["VLLM_IMAGE"],
    "server_image":os.environ["SERVER_IMAGE"],
}
Path(os.environ["REPORT"]).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
PY
}
write_report "running" 0

cleanup() {
  docker_sg rm -f "$NAME" >/dev/null 2>&1 || true
  docker_sg network rm "$NET" >/dev/null 2>&1 || true
}
on_exit() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    write_report "failed" "$rc" || true
  fi
  cleanup
  exit "$rc"
}
trap on_exit EXIT

PHASE="cuda12_runtime_preflight"
write_report "running" 0
docker_sg pull "$CUDA_IMAGE"
docker_sg run --rm --gpus "device=$GPU_DEVICE" "$CUDA_IMAGE" nvidia-smi >/tmp/djev_cuda12_nvidia_smi.txt

PHASE="clone_pinned_sources"
write_report "running" 0
rm -rf "$VLLM_SRC" "$DJEV_SRC" "$DERIVE_CTX"
git clone --filter=blob:none https://github.com/mmastrac/vllm.git "$VLLM_SRC"
git -C "$VLLM_SRC" checkout --detach "$VLLM_REF"
git clone --filter=blob:none https://github.com/mmastrac/djev-spark.git "$DJEV_SRC"
git -C "$DJEV_SRC" checkout --detach "$DJEV_REF"

PHASE="build_cuda12_vllm"
write_report "running" 0
(
  cd "$VLLM_SRC"
  export DOCKER_BUILDKIT=1
  docker_sg build \
    --target vllm-openai \
    -t "$VLLM_IMAGE" \
    --build-arg CUDA_VERSION=12.8.2 \
    --build-arg BUILD_BASE_IMAGE=pytorch/manylinux2_28-builder:cuda12.8 \
    --build-arg FINAL_BASE_IMAGE=nvidia/cuda:12.8.2-base-ubuntu24.04 \
    --build-arg torch_cuda_arch_list=8.9 \
    --build-arg max_jobs=4 \
    --build-arg nvcc_threads=2 \
    --build-arg RUN_WHEEL_CHECK=false \
    -f docker/Dockerfile .
)

PHASE="build_structured_server_image"
write_report "running" 0
mkdir -p "$DERIVE_CTX"
cp "$DJEV_SRC/server/structured_server.py" "$DERIVE_CTX/structured_server.py"
cp "$DJEV_SRC/entrypoint.sh" "$DERIVE_CTX/entrypoint.sh"
cat > "$DERIVE_CTX/Dockerfile" <<EOF
FROM $VLLM_IMAGE
COPY structured_server.py /opt/dgemma/structured_server.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && python3 -m py_compile /opt/dgemma/structured_server.py
ENTRYPOINT ["/entrypoint.sh"]
EOF
(
  cd "$DERIVE_CTX"
  docker_sg build -t "$SERVER_IMAGE" .
)

PHASE="download_fp8_checkpoint"
write_report "running" 0
.venv/bin/python - "$MODEL_DIR" "$MODEL_REPO" <<'PY'
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
model_dir=Path(sys.argv[1]).resolve()
repo=sys.argv[2]
snapshot_download(repo_id=repo, local_dir=str(model_dir))
if not (model_dir/"config.json").exists():
    raise SystemExit("FP8 checkpoint missing config.json")
safe=list(model_dir.glob("*.safetensors"))
if not safe:
    raise SystemExit("FP8 checkpoint contains no safetensors")
print(model_dir)
PY

PHASE="container_cuda_python_preflight"
write_report "running" 0
docker_sg run --rm --gpus "device=$GPU_DEVICE" --entrypoint python3 "$SERVER_IMAGE" -c \
  "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0)); assert torch.cuda.get_device_capability(0)==(8,9)"

PHASE="synthetic_server_start"
write_report "running" 0
cleanup
docker_sg network create --internal "$NET" >/dev/null
docker_sg run -d --rm \
  --name "$NAME" \
  --gpus "device=$GPU_DEVICE" \
  --network "$NET" \
  --shm-size=16g \
  -p 127.0.0.1:8011:8011 \
  -v "$(pwd)/$MODEL_DIR:/models/dgemma:ro" \
  -e MODEL=/models/dgemma \
  -e SERVED_NAME=dgemma-fp8 \
  -e CANVAS=128 \
  -e MAX_SEQS=2 \
  -e MAX_MODEL_LEN=4096 \
  -e GPU_UTIL=0.85 \
  -e KV_CACHE_GB=1 \
  -e HEADROOM_GB=8 \
  -e PORT=8010 \
  -e STRUCTURED_PORT=8011 \
  -e VLLM_USE_V2_MODEL_RUNNER=1 \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  -e VLLM_NO_USAGE_STATS=1 \
  "$SERVER_IMAGE" >/dev/null

.venv/bin/python - <<'PY'
import time, urllib.request
url="http://127.0.0.1:8011/health"
last=None
for _ in range(240):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:
            if r.status == 200:
                print(r.read().decode())
                break
    except Exception as e:
        last=repr(e)
    time.sleep(5)
else:
    raise SystemExit(f"local FP8 djev server failed health check: {last}")
PY

PHASE="synthetic_systemone_smoke"
write_report "running" 0
SYNTH="$BUILD_ROOT/synthetic_case.jsonl"
SMOKE_OUT="$BUILD_ROOT/synthetic_djev_output.jsonl"
PYTHONPATH=src .venv/bin/python - "$SYNTH" <<'PY'
import json,sys
from pathlib import Path
from semantic_schema import SEMANTIC_CONSTRUCTS
rec={
  "case_id":"synthetic_fp8_smoke",
  "synthetic_only":True,
  "model_state":{"clinical_note":"Synthetic test note: patient is stable, comfortable, and without a new acute concern."},
  "metadata":{"purpose":"local_cuda12_fp8_smoke"},
  "questions":SEMANTIC_CONSTRUCTS,
  "gold":None,
}
Path(sys.argv[1]).write_text(json.dumps(rec)+"\n",encoding="utf-8")
PY
PYTHONPATH=src .venv/bin/python src/16_run_jev_compatible_local.py \
  --cases "$SYNTH" \
  --output "$SMOKE_OUT" \
  --endpoint http://127.0.0.1:8011/v1/systemone \
  --model dgemma-fp8 \
  --limit 1 \
  --timeout 300

PHASE="verify_synthetic_response"
.venv/bin/python - "$SMOKE_OUT" "$REPORT" "$MODEL_DIR" "$VLLM_IMAGE" "$SERVER_IMAGE" <<'PY'
import json,sys
from pathlib import Path
out=Path(sys.argv[1])
report_path=Path(sys.argv[2])
model=Path(sys.argv[3])
rec=json.loads(out.read_text(encoding="utf-8").splitlines()[0])
if rec.get("status")!="ok":
    raise SystemExit(f"synthetic Jev request failed: {rec.get('error')}")
resp=rec.get("response",{})
answers=resp.get("answers",resp) if isinstance(resp,dict) else {}
expected={
 "overall_clinician_concern","worsening_trajectory","respiratory_concern",
 "hemodynamic_concern","poor_treatment_response","escalation_considered",
 "diagnostic_uncertainty","reassuring_stability"
}
if not expected.issubset(set(answers)):
    raise SystemExit(f"missing semantic answers: {sorted(expected-set(answers))}")
vals={}
for k in sorted(expected):
    a=answers[k]
    if not isinstance(a,dict) or not isinstance(a.get("noul"),(int,float)):
        raise SystemExit(f"invalid noul response for {k}: {a!r}")
    vals[k]=float(a["noul"])
files=[p for p in model.rglob("*") if p.is_file()]
size=sum(p.stat().st_size for p in files)
report={
 "analysis":"CUDA-12.8 / Ada FP8 DiffusionGemma-Jev synthetic smoke test",
 "status":"completed",
 "phase":"complete",
 "exit_code":0,
 "clinical_note_inference_performed":False,
 "synthetic_only":True,
 "host_driver":"555.42.02",
 "target_cuda_runtime":"12.8.2",
 "target_gpu_arch":"sm89 (RTX 6000 Ada)",
 "vllm_fork_commit":"6591b093b29536dd070c6af3628b734025c53e23",
 "djev_spark_commit":"1444f3e927f83ba508e5b28a4fd4fdd9ecd0976b",
 "model_repo":"RedHatAI/diffusiongemma-26B-A4B-it-FP8-dynamic",
 "model_file_count":len(files),
 "model_size_gb":round(size/(1024**3),3),
 "vllm_image":sys.argv[4],
 "server_image":sys.argv[5],
 "systemone_answer_count":len(vals),
 "systemone_probabilities_in_range":all(0.0<=v<=1.0 for v in vals.values()),
 "smoke_semantic_probabilities":vals,
 "next_gate":"Do not run MIMIC notes until this synthetic smoke result is reviewed."
}
report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
PY

PHASE="complete"
trap - EXIT
cleanup
