from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

from runrelay_progress import update_progress

EXPECTED_REVISION = "f7f5b7f5fa82ffc52addd066915886d497f5517b"


def load_helpers():
    path = Path(__file__).with_name("66_run_diffusiongemma_hf_native_multitask.py")
    spec = importlib.util.spec_from_file_location("dg_registered_v2_1_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen DiffusionGemma helpers")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def revision_candidates(model_dir: Path) -> set[str]:
    out: set[str] = set()
    manifest = model_dir / "local_model_manifest.json"
    if manifest.exists():
        try:
            value = json.loads(manifest.read_text(encoding="utf-8")).get("revision")
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value):
                out.add(value)
        except Exception:
            pass
    config = model_dir / "config.json"
    if config.exists():
        try:
            value = json.loads(config.read_text(encoding="utf-8")).get("_commit_hash")
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value):
                out.add(value)
        except Exception:
            pass
    meta_root = model_dir / ".cache" / "huggingface"
    if meta_root.exists():
        for path in meta_root.rglob("*.metadata"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines and re.fullmatch(r"[0-9a-f]{40}", lines[0]):
                out.add(lines[0])
    return out


def load_cases(path: Path, expected_names: list[str]) -> list[dict]:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("synthetic_only") is True or rec.get("local_only") is not True:
                raise RuntimeError("Invalid synthetic/local-only flag in registered DiffusionGemma corpus")
            case_id = str(rec.get("case_id"))
            if not case_id or case_id == "None" or case_id in seen:
                raise RuntimeError("Missing or duplicate case_id in registered DiffusionGemma corpus")
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"Blank note for case_id={case_id}")
            question_names = [str(q.get("name")) for q in rec.get("questions", [])]
            if question_names != expected_names:
                raise RuntimeError(f"Semantic question schema mismatch for case_id={case_id}")
            seen.add(case_id)
            rows.append({"case_id": case_id, "note": note})
    return rows


def existing_success_ids(path: Path) -> set[str]:
    ids = set()
    if not path.exists():
        return ids
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("status") == "ok" and rec.get("case_id") is not None:
                ids.add(str(rec["case_id"]))
    return ids


def safe_summary(values):
    vals = [float(x) for x in values]
    if not vals:
        return {"n": 0}
    vals.sort()
    def q(p):
        if len(vals) == 1:
            return vals[0]
        pos = p * (len(vals) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(vals) - 1)
        w = pos - lo
        return vals[lo] * (1 - w) + vals[hi] * w
    return {
        "n": len(vals),
        "p05": q(0.05),
        "median": q(0.5),
        "p95": q(0.95),
        "max": vals[-1],
    }


def main():
    ap = argparse.ArgumentParser(description="Registered v2.1 local DiffusionGemma inference on one frozen stripped-note corpus.")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--raw-output", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--expected", type=int, required=True)
    ap.add_argument("--max-chunks", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--parse-retries", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--progress-phase", default="v2_1_h6_diffusiongemma")
    args = ap.parse_args()

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import torch
    import transformers
    from transformers import AutoProcessor, DiffusionGemmaForBlockDiffusion

    helper = load_helpers()
    model_dir = Path(args.model_dir).expanduser().resolve()
    cases_path = Path(args.cases).expanduser().resolve()
    raw_path = Path(args.raw_output).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()

    revisions = revision_candidates(model_dir)
    if EXPECTED_REVISION not in revisions or any(x != EXPECTED_REVISION for x in revisions):
        raise RuntimeError(f"Registered DiffusionGemma revision not verified: {sorted(revisions)}")

    if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
        raise RuntimeError("Registered DiffusionGemma inference requires two visible CUDA GPUs")

    cases = load_cases(cases_path, list(helper.EXPECTED))
    if len(cases) != args.expected:
        raise RuntimeError(f"Expected {args.expected} frozen notes, found {len(cases)}")

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    existing = existing_success_ids(raw_path)
    valid_ids = {x["case_id"] for x in cases}
    if not existing.issubset(valid_ids):
        raise RuntimeError("Existing DiffusionGemma raw output contains case IDs outside frozen corpus")

    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True)
    model = DiffusionGemmaForBlockDiffusion.from_pretrained(
        str(model_dir),
        dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
        local_files_only=True,
        attn_implementation="sdpa",
    )
    model.eval()
    model_load_seconds = time.perf_counter() - load_started
    tokenizer = processor.tokenizer
    context_limit, context_source = helper.infer_context_limit(model, tokenizer)

    empty_inputs = processor.apply_chat_template(
        [{"role": "user", "content": helper.build_prompt("")}],
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
        enable_thinking=False,
    )
    empty_prompt_tokens = int(empty_inputs["input_ids"].shape[-1])
    reserve = args.max_new_tokens + 96
    chunk_tokens = context_limit - empty_prompt_tokens - reserve
    if chunk_tokens < 256:
        raise RuntimeError("Insufficient context for registered DiffusionGemma chunking")
    overlap = min(128, max(32, chunk_tokens // 10))
    first_device = next(model.parameters()).device

    note_tokens = []
    chunk_counts = []
    attempt_seconds = []
    all_scores = {name: [] for name in helper.EXPECTED}
    new_success = 0
    new_failures = 0
    retries_total = 0
    chunks_using_retry = 0
    truncated = 0
    error_types = Counter()
    failure_stages = Counter()
    started = time.perf_counter()

    def build_report(status: str):
        per_construct = {}
        for name, vals in all_scores.items():
            per_construct[name] = {
                "n_new": len(vals),
                "mean_new": statistics.fmean(vals) if vals else None,
                "median_new": statistics.median(vals) if vals else None,
                "intermediate_fraction_new": (
                    sum(1 for v in vals if 0.0 < v < 1.0) / len(vals) if vals else None
                ),
            }
        return {
            "analysis": "Registered v2.1 H6 DiffusionGemma semantic inference aggregate report",
            "status": status,
            "registration_id": "ahxn9",
            "local_only": True,
            "labels_read_or_used": False,
            "contains_note_text": False,
            "contains_case_ids": False,
            "contains_patient_level_scores": False,
            "model": "google/diffusiongemma-26B-A4B-it",
            "model_revision": EXPECTED_REVISION,
            "backend": "transformers_native_bf16_prompted_semantic_scores",
            "score_definition": "Prompted zero-shot 0-1 support scores for the frozen eight constructs; not Jev noul probabilities.",
            "aggregation_across_chunks": "maximum for seven concern constructs; minimum for reassuring_stability",
            "torch_version": torch.__version__,
            "torch_cuda_version": str(torch.version.cuda),
            "transformers_version": transformers.__version__,
            "expected_unique_notes": args.expected,
            "resumed_successes": len(existing),
            "new_successes": new_success,
            "new_failures": new_failures,
            "successful_rows_available": len(existing) + new_success,
            "truncated_by_max_chunks_new": truncated,
            "note_token_count_new": safe_summary(note_tokens),
            "chunks_evaluated_new": safe_summary(chunk_counts),
            "seconds_per_new_attempt": safe_summary(attempt_seconds),
            "parse_retries_used_total": retries_total,
            "chunks_using_parse_retry": chunks_using_retry,
            "error_type_counts": dict(error_types),
            "failure_stage_counts": dict(failure_stages),
            "context_policy": {
                "context_limit_tokens": context_limit,
                "context_limit_source": context_source,
                "empty_prompt_tokens": empty_prompt_tokens,
                "max_new_tokens": args.max_new_tokens,
                "note_chunk_tokens": chunk_tokens,
                "chunk_overlap_tokens": overlap,
                "max_chunks": args.max_chunks,
            },
            "per_construct_new_score_summary": per_construct,
            "model_load_seconds": model_load_seconds,
            "run_elapsed_seconds": time.perf_counter() - started,
            "guardrail": "Aggregate diagnostics only; outcome labels were not read or used during semantic inference.",
        }

    mode = "a" if raw_path.exists() else "w"
    with raw_path.open(mode, encoding="utf-8") as out:
        for ordinal, case in enumerate(cases):
            if case["case_id"] in existing:
                continue
            t0 = time.perf_counter()
            stage = "tokenize"
            try:
                ids = tokenizer(case["note"], add_special_tokens=False)["input_ids"]
                stage = "chunk"
                chunks, was_truncated = helper.chunk_token_ids(
                    ids, size=chunk_tokens, overlap=overlap, max_chunks=args.max_chunks
                )
                truncated += int(was_truncated)
                chunk_scores = []
                retry_counts = []
                for chunk_index, chunk_ids in enumerate(chunks):
                    chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
                    stage = "template"
                    inputs = processor.apply_chat_template(
                        [{"role": "user", "content": helper.build_prompt(chunk_text)}],
                        tokenize=True,
                        add_generation_prompt=True,
                        return_dict=True,
                        return_tensors="pt",
                        enable_thinking=False,
                    )
                    input_len = int(inputs["input_ids"].shape[-1])
                    if input_len + args.max_new_tokens > context_limit:
                        raise RuntimeError("DiffusionGemma context overflow")
                    inputs = {k: v.to(first_device) if hasattr(v, "to") else v for k, v in inputs.items()}
                    parsed = None
                    used = 0
                    for attempt in range(args.parse_retries + 1):
                        local_seed = args.seed + ordinal * 1000 + chunk_index * 10 + attempt
                        torch.manual_seed(local_seed)
                        torch.cuda.manual_seed_all(local_seed)
                        stage = "generate"
                        with torch.inference_mode():
                            generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens)
                        sequences = getattr(generated, "sequences", generated)
                        if sequences.ndim != 2 or sequences.shape[0] != 1:
                            raise RuntimeError(f"Unexpected generated shape {tuple(sequences.shape)}")
                        completion = sequences[0, input_len:].detach().cpu().tolist()
                        decoded = tokenizer.decode(completion, skip_special_tokens=True)
                        stage = "parse"
                        try:
                            parsed = helper.extract_scores(decoded)
                            used = attempt
                            break
                        except ValueError:
                            if attempt >= args.parse_retries:
                                raise
                    if parsed is None:
                        raise RuntimeError("DiffusionGemma parse retry exhausted")
                    chunk_scores.append(parsed)
                    retry_counts.append(used)

                aggregated = helper.aggregate_scores(chunk_scores)
                record = {
                    "case_id": case["case_id"],
                    "local_only": True,
                    "status": "ok",
                    "model": "google/diffusiongemma-26B-A4B-it",
                    "model_revision": EXPECTED_REVISION,
                    "backend": "transformers_native_bf16_prompted_semantic_scores",
                    "metadata": {
                        "note_tokens": len(ids),
                        "chunks_evaluated": len(chunks),
                        "truncated_by_max_chunks": bool(was_truncated),
                        "chunk_tokens": chunk_tokens,
                        "chunk_overlap": overlap,
                        "max_chunks": args.max_chunks,
                        "parse_retries_by_chunk": retry_counts,
                        "aggregation": "max concern constructs; min reassuring_stability",
                    },
                    "response": {
                        "answers": {
                            name: {
                                "score": float(aggregated[name]),
                                "chunk_values": [float(row[name]) for row in chunk_scores],
                            }
                            for name in helper.EXPECTED
                        }
                    },
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                new_success += 1
                note_tokens.append(len(ids))
                chunk_counts.append(len(chunks))
                retries_total += sum(retry_counts)
                chunks_using_retry += sum(x > 0 for x in retry_counts)
                for name, value in aggregated.items():
                    all_scores[name].append(float(value))
            except Exception as exc:
                new_failures += 1
                error_types[type(exc).__name__] += 1
                failure_stages[stage] += 1
                out.write(json.dumps({
                    "case_id": case["case_id"],
                    "local_only": True,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "failure_stage": stage,
                }) + "\n")
                out.flush()
            finally:
                attempt_seconds.append(time.perf_counter() - t0)

            processed = len(existing) + new_success + new_failures
            if processed % 10 == 0 or processed == args.expected:
                update_progress(
                    current=processed,
                    total=args.expected,
                    phase=args.progress_phase,
                    message=f"DiffusionGemma processed {processed}/{args.expected} frozen notes",
                    unit="note",
                )
            if processed % 50 == 0:
                report_path.write_text(json.dumps(build_report("running"), indent=2) + "\n", encoding="utf-8")

    final_status = "completed" if len(existing) + new_success == args.expected and new_failures == 0 else "failed"
    report_path.write_text(json.dumps(build_report(final_status), indent=2) + "\n", encoding="utf-8")
    if final_status != "completed":
        raise RuntimeError("Registered DiffusionGemma inference did not complete without failures")


if __name__ == "__main__":
    main()
