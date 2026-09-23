from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> dict:
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=30,check=False)
        return {
            "available": True,
            "returncode": int(p.returncode),
            "stdout": p.stdout.strip()[:4000],
            "stderr": p.stderr.strip()[:2000],
        }
    except FileNotFoundError:
        return {"available": False}
    except Exception as exc:
        return {"available": True, "error": type(exc).__name__}


def summarize_dir(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    files=[]
    total=0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
            files.append(p)
    safe=[p for p in files if p.suffix==".safetensors"]
    required=["config.json","tokenizer.json","model.safetensors.index.json"]
    return {
        "exists": True,
        "file_count": len(files),
        "size_gb": round(total/(1024**3),3),
        "safetensors_files": len(safe),
        "required_files_present": {x:(path/x).exists() for x in required},
        "partial_or_incomplete_files": sorted([
            p.name for p in files if ".incomplete" in p.name or p.suffix in {".tmp",".part"}
        ])[:100],
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    a=ap.parse_args()

    root=Path.cwd()
    model=root/"data/local_models/diffusiongemma-26B-A4B-it-NVFP4"
    setup_artifact=root/"outputs/multitask_benchmark/local_djev_setup_report.json"

    disk=shutil.disk_usage(root)
    report={
        "analysis":"Offline diagnosis of failed local DiffusionGemma-Jev setup",
        "local_only":True,
        "network_access_used":False,
        "credentialed_note_inference_performed":False,
        "docker_executable":shutil.which("docker") is not None,
        "podman_executable":shutil.which("podman") is not None,
        "apptainer_executable":shutil.which("apptainer") is not None,
        "singularity_executable":shutil.which("singularity") is not None,
        "identity":run(["id"]),
        "docker_group":run(["getent","group","docker"]),
        "sudo_noninteractive_docker_info":run(["sudo","-n","docker","info","--format","{{json .ServerVersion}}"]),
        "sg_docker_info":run(["sg","docker","-c","docker info --format '{{json .ServerVersion}}'"]),
        "docker_image_inspect":run(["docker","image","inspect","ghcr.io/taeold/djev-run:latest","--format","{{.Id}}"]),
        "docker_ps_named":run(["docker","ps","-a","--filter","name=mimic-djev-local","--format","{{.ID}} {{.Status}} {{.Image}}"]),
        "gpu":run(["nvidia-smi","--query-gpu=index,name,driver_version,memory.total,memory.free","--format=csv,noheader,nounits"]),
        "nvidia_smi_header":run(["nvidia-smi"]),
        "model_directory":summarize_dir(model),
        "setup_artifact_exists":setup_artifact.exists(),
        "disk_free_gb":round(disk.free/(1024**3),3),
        "disk_total_gb":round(disk.total/(1024**3),3),
        "huggingface_hub_import":run([str(root/".venv/bin/python"),"-c","import huggingface_hub; print(huggingface_hub.__version__)"]),
        "interpretation":"If the image is absent, failure occurred at docker pull or earlier. If the image exists but the model directory is absent/partial, failure occurred during Hugging Face download. If both are complete and no setup artifact exists, failure occurred during post-download verification/report creation."
    }

    out=Path(a.output).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
