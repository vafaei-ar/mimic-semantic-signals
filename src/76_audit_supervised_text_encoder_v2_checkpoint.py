from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit and freeze the selected supervised encoder v2 checkpoint without reading test data.")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    ckpt_path = Path(args.checkpoint).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    if not ckpt_path.exists():
        raise FileNotFoundError(ckpt_path)

    obj = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    required = {
        "protocol",
        "base_checkpoint",
        "epoch",
        "outcomes",
        "chunk_tokens",
        "chunk_overlap",
        "max_chunks",
        "model_state_dict",
    }
    missing = sorted(required - set(obj))
    if missing:
        raise RuntimeError(f"Checkpoint missing required fields: {missing}")

    epoch = int(obj["epoch"])
    if epoch != 4:
        raise RuntimeError(f"Expected selected epoch 4, found {epoch}")

    state = obj["model_state_dict"]
    float_tensors = 0
    parameter_elements = 0
    for value in state.values():
        if torch.is_tensor(value) and torch.is_floating_point(value):
            float_tensors += 1
            parameter_elements += int(value.numel())

    report = {
        "analysis": "Selected supervised Open-Jev DeBERTa v2 checkpoint freeze audit",
        "development_job": "Y8R4K2M7",
        "development_artifact_sha256": "755dcdd4cfbb695cb6f2d52101e0256c3ee30d4b70cd04fd2cb2e9765ebfa99f",
        "local_only": True,
        "network_enabled": False,
        "test_split_read": False,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "checkpoint_path_shared": False,
        "checkpoint_sha256": sha256_file(ckpt_path),
        "checkpoint_size_bytes": int(ckpt_path.stat().st_size),
        "protocol": obj["protocol"],
        "base_checkpoint": obj["base_checkpoint"],
        "selected_epoch": epoch,
        "outcomes": list(obj["outcomes"]),
        "chunk_tokens": int(obj["chunk_tokens"]),
        "chunk_overlap": int(obj["chunk_overlap"]),
        "max_chunks": int(obj["max_chunks"]),
        "positive_class_weight": float(obj.get("positive_class_weight", 3.0)),
        "encoder_learning_rate": float(obj.get("encoder_learning_rate", 5e-6)),
        "head_learning_rate": float(obj.get("head_learning_rate", 1e-4)),
        "state_float_tensors": int(float_tensors),
        "state_parameter_elements": int(parameter_elements),
        "guardrail": "This task hashes and verifies the selected local checkpoint only. It does not enumerate or open the locked test split.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
