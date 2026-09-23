from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path


def command_output(cmd: list[str]) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
        return {
            "available": True,
            "returncode": int(p.returncode),
            "stdout": p.stdout.strip()[:2000],
            "stderr": p.stderr.strip()[:1000],
        }
    except FileNotFoundError:
        return {"available": False}
    except Exception as exc:
        return {"available": True, "error": type(exc).__name__}


def probe(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            body = r.read(2000).decode("utf-8", errors="replace")
            return {
                "reachable": True,
                "status": int(getattr(r, "status", 200)),
                "body_preview": body[:500],
            }
    except Exception as exc:
        return {"reachable": False, "error": type(exc).__name__}


def dir_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    files = 0
    bytes_total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                files += 1
                try:
                    bytes_total += p.stat().st_size
                except OSError:
                    pass
    except Exception as exc:
        return {"exists": True, "scan_error": type(exc).__name__}
    return {
        "exists": True,
        "files": files,
        "size_gb": round(bytes_total / (1024 ** 3), 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    home = Path.home()
    hf_model = home / ".cache" / "huggingface" / "hub" / "models--nvidia--diffusiongemma-26B-A4B-it-NVFP4"

    modules = {}
    for name in ["torch", "vllm", "djev", "djev_spark"]:
        modules[name] = importlib.util.find_spec(name) is not None

    gpu = command_output([
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.free,compute_cap",
        "--format=csv,noheader,nounits",
    ])

    report = {
        "analysis": "Local DiffusionGemma-Jev readiness audit",
        "local_only": True,
        "network_download_performed": False,
        "credentialed_note_inference_performed": False,
        "python_modules": modules,
        "executables": {
            "docker": shutil.which("docker") is not None,
            "nvidia_smi": shutil.which("nvidia-smi") is not None,
        },
        "gpu_query": gpu,
        "local_server_probes": {
            "127.0.0.1:8011": probe("http://127.0.0.1:8011/health"),
            "127.0.0.1:8080": probe("http://127.0.0.1:8080/health"),
        },
        "huggingface_diffusiongemma_cache": dir_summary(hf_model),
        "readiness_rule": (
            "A local DiffusionGemma-Jev benchmark requires a localhost-only /v1/systemone service, "
            "the compatible djev/vLLM stack, local model weights, and sufficient GPU memory. "
            "This audit does not install packages, download weights, or start a server."
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
