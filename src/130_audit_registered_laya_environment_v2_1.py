from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path

EXPECTED_PACKAGE_VERSION = "0.3.4"
EXPECTED_REPO = "convaiinnovations/laya-typed-decisions"
EXPECTED_REVISION = "f9ab0b228f0fc0f14d873dbc99038f135c2da1b2"
EXPECTED_SCHEMA_SHA256 = "72763082c314a4542817ccfcd42d2b10d9446fc8e84c3391a2140790b2483623"
DEFAULT_MODEL_DIR = "~/.cache/mimic-semantic-signals/laya-typed-decisions-f9ab0b2"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="No-data preregistered Laya v2.1 environment preflight.")
    ap.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    ap.add_argument("--schema", default="src/semantic_schema.py")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    model_dir = Path(args.model_dir).expanduser().resolve()
    schema = Path(args.schema).resolve()
    manifest_path = model_dir / "local_model_manifest.json"
    model_path = model_dir / "model.safetensors"

    package_version = importlib.metadata.version("laya")
    if package_version != EXPECTED_PACKAGE_VERSION:
        raise RuntimeError(f"Laya version mismatch: {package_version} != {EXPECTED_PACKAGE_VERSION}")
    if importlib.util.find_spec("laya") is None:
        raise RuntimeError("Laya import unavailable")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing Laya local model manifest: {manifest_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing Laya model weights: {model_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("repo") != EXPECTED_REPO:
        raise RuntimeError(f"Laya repo mismatch: {manifest.get('repo')} != {EXPECTED_REPO}")
    if manifest.get("revision") != EXPECTED_REVISION:
        raise RuntimeError(f"Laya revision mismatch: {manifest.get('revision')} != {EXPECTED_REVISION}")

    schema_sha = sha256_file(schema)
    if schema_sha != EXPECTED_SCHEMA_SHA256:
        raise RuntimeError(f"Semantic schema mismatch: {schema_sha} != {EXPECTED_SCHEMA_SHA256}")

    report = {
        "analysis": "Registered v2.1 Laya environment preflight",
        "status": "passed",
        "clinical_data_read": False,
        "outcome_labels_read": False,
        "package": "laya",
        "package_version": package_version,
        "model_repo": EXPECTED_REPO,
        "model_revision": EXPECTED_REVISION,
        "model_weights_present": True,
        "semantic_schema_sha256": schema_sha,
        "registered_chunk_tokens": 600,
        "registered_chunk_overlap": 100,
        "registered_max_chunks": 8,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
