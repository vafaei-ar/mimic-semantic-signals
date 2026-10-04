from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

MODEL_ID = "BAAI/bge-large-en-v1.5"
REVISION = "d4aa6901d3a41ba39fb536a557fa166f842b0e09"
SNAPSHOT = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-large-en-v1.5" / "snapshots" / REVISION
OUT = Path("outputs/integrity/extension_embedding_smoke_v2_1.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def version(name: str):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None

report = {
    "analysis": "label-free frozen embedding synthetic smoke test",
    "status": "started",
    "reads_outcome_labels": False,
    "reads_clinical_notes": False,
    "network_used": False,
    "model_id": MODEL_ID,
    "revision": REVISION,
    "snapshot_exists": SNAPSHOT.is_dir(),
    "packages": {
        "sentence-transformers": version("sentence-transformers"),
        "transformers": version("transformers"),
        "torch": version("torch"),
    },
}

if not SNAPSHOT.is_dir():
    raise SystemExit(f"Missing cached snapshot: {SNAPSHOT}")

try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(SNAPSHOT), device="cpu")
    vectors = model.encode(
        [
            "Synthetic clinical sentence for offline embedding verification.",
            "Second synthetic sentence with no patient information.",
        ],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    report.update({
        "status": "completed",
        "embedding_shape": list(vectors.shape),
        "embedding_dim": int(vectors.shape[1]),
        "finite": bool(__import__("numpy").isfinite(vectors).all()),
        "max_seq_length": int(getattr(model, "max_seq_length", 0) or 0),
    })
except Exception as exc:
    report.update({
        "status": "failed",
        "error_type": type(exc).__name__,
        "error": str(exc)[:1200],
    })

OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["status"] == "completed" else 1)
