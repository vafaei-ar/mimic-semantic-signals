from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_REPO = "google/diffusiongemma-26B-A4B-it"
EXPECTED_REVISION = "f7f5b7f5fa82ffc52addd066915886d497f5517b"
EXPECTED_SCHEMA_SHA256 = "72763082c314a4542817ccfcd42d2b10d9446fc8e84c3391a2140790b2483623"
EXPECTED_TORCH_PREFIX = "2.5.1"
EXPECTED_CUDA_PREFIX = "12.4"
EXPECTED_TRANSFORMERS = "5.17.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_revision_candidates(model_dir: Path) -> list[str]:
    found: set[str] = set()
    manifest = model_dir / "local_model_manifest.json"
    if manifest.exists():
        try:
            obj = json.loads(manifest.read_text(encoding="utf-8"))
            value = obj.get("revision")
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value):
                found.add(value)
        except Exception:
            pass

    config = model_dir / "config.json"
    if config.exists():
        try:
            obj = json.loads(config.read_text(encoding="utf-8"))
            value = obj.get("_commit_hash")
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value):
                found.add(value)
        except Exception:
            pass

    meta_root = model_dir / ".cache" / "huggingface"
    if meta_root.exists():
        for path in meta_root.rglob("*.metadata"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for value in re.findall(r"\b[0-9a-f]{40}\b", text):
                found.add(value)

    for path in model_dir.rglob("*"):
        try:
            if path.is_symlink():
                resolved = str(path.resolve())
                for value in re.findall(r"\b[0-9a-f]{40}\b", resolved):
                    found.add(value)
        except Exception:
            continue
    return sorted(found)


def infer_context_limit(config, tokenizer) -> tuple[int, str]:
    candidates: list[tuple[int, str]] = []
    for label, obj in [
        ("config", config),
        ("config.text_config", getattr(config, "text_config", None)),
    ]:
        if obj is None:
            continue
        for attr in ("max_position_embeddings", "max_sequence_length", "seq_length"):
            value = getattr(obj, attr, None)
            if isinstance(value, int) and 512 <= value <= 131072:
                candidates.append((value, f"{label}.{attr}"))
    tok_max = getattr(tokenizer, "model_max_length", None)
    if isinstance(tok_max, int) and 512 <= tok_max <= 131072:
        candidates.append((tok_max, "tokenizer.model_max_length"))
    if not candidates:
        return 2048, "conservative_fallback"
    return min(candidates, key=lambda x: x[0])


def main() -> None:
    ap = argparse.ArgumentParser(description="No-data registered DiffusionGemma v2.1 environment preflight.")
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--schema", default="src/semantic_schema.py")
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    args = ap.parse_args()

    import torch
    import transformers
    from transformers import AutoConfig, AutoProcessor

    model_dir = Path(args.model_dir).expanduser().resolve()
    schema = Path(args.schema).resolve()
    output = Path(args.output).resolve()

    required = ["config.json", "model.safetensors.index.json"]
    missing = [name for name in required if not (model_dir / name).exists()]
    shards = sorted(model_dir.glob("model-*.safetensors"))
    if missing or not shards:
        raise RuntimeError(f"DiffusionGemma local model incomplete: missing={missing}, shards={len(shards)}")

    if not torch.__version__.startswith(EXPECTED_TORCH_PREFIX):
        raise RuntimeError(f"torch version mismatch: {torch.__version__}")
    if not str(torch.version.cuda).startswith(EXPECTED_CUDA_PREFIX):
        raise RuntimeError(f"CUDA runtime mismatch: {torch.version.cuda}")
    if transformers.__version__ != EXPECTED_TRANSFORMERS:
        raise RuntimeError(f"transformers version mismatch: {transformers.__version__}")
    if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
        raise RuntimeError("Registered DiffusionGemma path requires two visible CUDA GPUs")

    revisions = local_revision_candidates(model_dir)
    if EXPECTED_REVISION not in revisions:
        raise RuntimeError(
            "Could not verify the registered DiffusionGemma revision from local checkpoint metadata; "
            f"expected={EXPECTED_REVISION}, observed={revisions}"
        )
    unexpected = [x for x in revisions if x != EXPECTED_REVISION]
    if unexpected:
        raise RuntimeError(f"Mixed DiffusionGemma revision metadata found: {revisions}")

    schema_sha = sha256_file(schema)
    if schema_sha != EXPECTED_SCHEMA_SHA256:
        raise RuntimeError(f"Semantic schema mismatch: {schema_sha} != {EXPECTED_SCHEMA_SHA256}")

    config = AutoConfig.from_pretrained(str(model_dir), local_files_only=True)
    processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True)
    tokenizer = processor.tokenizer

    helper_path = Path(__file__).with_name("66_run_diffusiongemma_hf_native_multitask.py")
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("dg_helpers_preflight", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load DiffusionGemma helper module")
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper
    spec.loader.exec_module(helper)

    context_limit, context_source = infer_context_limit(config, tokenizer)
    empty_inputs = processor.apply_chat_template(
        [{"role": "user", "content": helper.build_prompt("")}],
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
        enable_thinking=False,
    )
    empty_prompt_tokens = int(empty_inputs["input_ids"].shape[-1])
    reserve = int(args.max_new_tokens) + 96
    chunk_tokens = context_limit - empty_prompt_tokens - reserve
    if chunk_tokens < 256:
        raise RuntimeError(
            f"Insufficient context after prompt/generation reserve: context={context_limit}, "
            f"prompt={empty_prompt_tokens}, reserve={reserve}"
        )
    overlap = min(128, max(32, chunk_tokens // 10))

    report = {
        "analysis": "Registered v2.1 DiffusionGemma environment preflight",
        "status": "passed",
        "clinical_data_read": False,
        "outcome_labels_read": False,
        "model_repo": EXPECTED_REPO,
        "model_revision": EXPECTED_REVISION,
        "revision_verified_from_local_metadata": True,
        "local_revision_candidates": revisions,
        "semantic_schema_sha256": schema_sha,
        "torch_version": torch.__version__,
        "torch_cuda_version": str(torch.version.cuda),
        "transformers_version": transformers.__version__,
        "visible_gpu_count": int(torch.cuda.device_count()),
        "model_shard_count": len(shards),
        "context_limit_tokens": int(context_limit),
        "context_limit_source": context_source,
        "empty_prompt_tokens": empty_prompt_tokens,
        "max_new_tokens": int(args.max_new_tokens),
        "generation_reserve_tokens": reserve,
        "derived_note_chunk_tokens": int(chunk_tokens),
        "derived_chunk_overlap_tokens": int(overlap),
        "registered_max_chunks": 8,
        "score_definition": "Prompted zero-shot 0-1 support scores for the frozen eight constructs; not Jev noul probabilities.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
