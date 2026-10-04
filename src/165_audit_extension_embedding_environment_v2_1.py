from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path

OUT = Path("outputs/integrity/extension_embedding_environment_v2_1.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

home = Path.home()
roots = [
    home / ".cache" / "huggingface" / "hub",
    home / ".cache" / "torch" / "sentence_transformers",
]

def pkg_version(name: str):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None

models = []
hf = roots[0]
if hf.exists():
    for model_dir in sorted(hf.glob("models--*")):
        if not model_dir.is_dir():
            continue
        model_id = model_dir.name[len("models--"):].replace("--", "/")
        snapshots_dir = model_dir / "snapshots"
        snapshots = []
        if snapshots_dir.exists():
            for snap in sorted(snapshots_dir.iterdir()):
                if not snap.is_dir():
                    continue
                entry = {"revision": snap.name}
                cfg = snap / "config.json"
                if cfg.exists():
                    try:
                        data = json.loads(cfg.read_text(encoding="utf-8"))
                        entry["model_type"] = data.get("model_type")
                        entry["hidden_size"] = data.get("hidden_size")
                        entry["max_position_embeddings"] = data.get("max_position_embeddings")
                        entry["architectures"] = data.get("architectures")
                    except Exception as exc:
                        entry["config_error"] = type(exc).__name__
                modules = snap / "modules.json"
                entry["sentence_transformers_modules"] = modules.exists()
                snapshots.append(entry)
        models.append({"model_id": model_id, "snapshots": snapshots})

torch_st = []
root = roots[1]
if root.exists():
    for p in sorted(root.iterdir()):
        if p.is_dir():
            torch_st.append(p.name)

report = {
    "analysis": "label-free extension embedding environment audit",
    "status": "completed",
    "reads_outcome_labels": False,
    "reads_clinical_notes": False,
    "network_used": False,
    "packages": {
        "transformers": pkg_version("transformers"),
        "sentence-transformers": pkg_version("sentence-transformers"),
        "torch": pkg_version("torch"),
        "scikit-learn": pkg_version("scikit-learn"),
    },
    "huggingface_cached_models": models,
    "legacy_sentence_transformer_cache_dirs": torch_st,
    "selection_guardrail": (
        "Choose exactly one open-weight embedding model using label-free criteria only: "
        "local availability, documented sentence-embedding suitability, adequate context/chunking support, "
        "and feasible compute. Do not inspect outcome-dependent performance before freezing the choice."
    ),
}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
