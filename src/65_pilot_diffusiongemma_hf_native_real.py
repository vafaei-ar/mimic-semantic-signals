from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path

from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS
import re


EXPECTED = [q["name"] for q in SEMANTIC_CONSTRUCTS]
OUTCOMES = [
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
]
POSITIVE_CONSTRUCTS = set(EXPECTED) - {"reassuring_stability"}


def build_prompt(note: str) -> str:
    parts = [
        "You are a clinical semantic scoring system.",
        "Score ONLY the information explicitly supported by the clinical note below.",
        "For each construct, return a number from 0.0 to 1.0 representing how strongly the TRUE criterion is supported.",
        "0.0 means the TRUE criterion is not supported; 1.0 means it is strongly supported.",
        "Return exactly one JSON object with the eight keys shown below and numeric values only.",
        "Do not add markdown, explanations, units, or extra keys.",
        "",
        "Clinical note:",
        note,
        "",
        "Constructs:",
    ]
    for q in SEMANTIC_CONSTRUCTS:
        parts.extend([
            f"- {q['name']}: {q['question']}",
            f"  TRUE: {q['criteria']['true']}",
            f"  FALSE: {q['criteria']['false']}",
        ])
    parts.extend([
        "",
        "Required JSON keys in this exact order:",
        ", ".join(EXPECTED),
    ])
    return "\n".join(parts)


def extract_scores(text: str) -> dict[str, float]:
    candidates = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict) or not all(name in obj for name in EXPECTED):
            continue
        scores: dict[str, float] = {}
        try:
            for name in EXPECTED:
                value = float(obj[name])
                if not 0.0 <= value <= 1.0:
                    raise ValueError
                scores[name] = value
        except Exception:
            continue
        return scores
    raise ValueError("No valid eight-score JSON object found.")


def load_cases(path: Path, limit: int) -> list[dict]:
    cases: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("synthetic_only") is True:
                raise RuntimeError(f"{path}: synthetic case found in real-note pilot")
            if rec.get("local_only") is not True:
                raise RuntimeError(f"{path}: refusing case without local_only=true")
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                continue
            question_names = [str(q.get("name")) for q in rec.get("questions", [])]
            if question_names != EXPECTED:
                raise RuntimeError(
                    f"{path}: frozen semantic question schema mismatch: {question_names}"
                )
            cases.append(rec)
            if len(cases) >= limit:
                break
    if len(cases) < limit:
        raise RuntimeError(f"{path}: requested {limit} usable cases but found {len(cases)}")
    return cases


def infer_context_limit(model, tokenizer) -> tuple[int, str]:
    candidates: list[tuple[int, str]] = []
    for label, obj in [
        ("model.config", getattr(model, "config", None)),
        ("model.config.text_config", getattr(getattr(model, "config", None), "text_config", None)),
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


def chunk_token_ids(ids: list[int], size: int, overlap: int, max_chunks: int) -> tuple[list[list[int]], bool]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk size")
    if not ids:
        return [[]], False
    chunks: list[list[int]] = []
    step = size - overlap
    start = 0
    while start < len(ids):
        chunks.append(ids[start:start + size])
        if len(chunks) >= max_chunks:
            break
        if start + size >= len(ids):
            break
        start += step
    covered_to = min(len(ids), (len(chunks) - 1) * step + len(chunks[-1]))
    return chunks, covered_to < len(ids)


def aggregate_scores(per_chunk: list[dict[str, float]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for name in EXPECTED:
        values = [row[name] for row in per_chunk]
        out[name] = min(values) if name == "reassuring_stability" else max(values)
    return out


def quantile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    pos = q * (len(xs) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(xs[lo])
    w = pos - lo
    return float(xs[lo] * (1 - w) + xs[hi] * w)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run a small fully offline real-note DiffusionGemma pilot to test parsing, "
            "score resolution, chunking behavior, and throughput. No row-level artifact is written."
        )
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--per-outcome", type=int, default=6)
    ap.add_argument("--max-chunks", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--seed", type=int, default=20260923)
    args = ap.parse_args()

    import torch
    import transformers
    from transformers import AutoProcessor, DiffusionGemmaForBlockDiffusion

    base = Path(args.base).expanduser().resolve()
    model_dir = Path(args.model_dir).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
        raise RuntimeError("Native BF16 DiffusionGemma pilot requires at least two visible GPUs.")

    selected: list[tuple[str, dict]] = []
    for outcome in OUTCOMES:
        path = base / outcome / "cases.jsonl"
        for rec in load_cases(path, args.per_outcome):
            selected.append((outcome, rec))

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

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
    context_limit, context_limit_source = infer_context_limit(model, tokenizer)

    empty_inputs = processor.apply_chat_template(
        [{"role": "user", "content": build_prompt("")}],
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
        raise RuntimeError(
            f"Insufficient context for safe chunking: context={context_limit}, "
            f"empty_prompt={empty_prompt_tokens}, reserve={reserve}"
        )
    overlap = min(128, max(32, chunk_tokens // 10))

    completed = 0
    failed = 0
    errors: Counter[str] = Counter()
    all_scores: dict[str, list[float]] = {name: [] for name in EXPECTED}
    outcome_stats = {
        o: {
            "attempted": 0,
            "completed": 0,
            "failed": 0,
            "note_tokens": [],
            "chunks": [],
            "truncated_by_max_chunks": 0,
            "inference_seconds": [],
        }
        for o in OUTCOMES
    }

    inference_started = time.perf_counter()
    first_device = next(model.parameters()).device
    total = len(selected)

    for ordinal, (outcome, case) in enumerate(selected):
        st = outcome_stats[outcome]
        st["attempted"] += 1
        case_started = time.perf_counter()
        try:
            note = str(case["model_state"]["clinical_note"])
            note_ids = tokenizer(note, add_special_tokens=False)["input_ids"]
            chunks, truncated = chunk_token_ids(
                note_ids,
                size=chunk_tokens,
                overlap=overlap,
                max_chunks=args.max_chunks,
            )
            chunk_scores: list[dict[str, float]] = []
            for chunk_index, ids in enumerate(chunks):
                chunk_text = tokenizer.decode(ids, skip_special_tokens=True)
                inputs = processor.apply_chat_template(
                    [{"role": "user", "content": build_prompt(chunk_text)}],
                    tokenize=True,
                    add_generation_prompt=True,
                    return_dict=True,
                    return_tensors="pt",
                    enable_thinking=False,
                )
                input_len = int(inputs["input_ids"].shape[-1])
                if input_len + args.max_new_tokens > context_limit:
                    raise RuntimeError(
                        f"context_overflow input={input_len} new={args.max_new_tokens} "
                        f"limit={context_limit}"
                    )
                inputs = {
                    k: v.to(first_device) if hasattr(v, "to") else v
                    for k, v in inputs.items()
                }
                local_seed = args.seed + ordinal * 100 + chunk_index
                torch.manual_seed(local_seed)
                torch.cuda.manual_seed_all(local_seed)
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=args.max_new_tokens,
                    )
                sequences = getattr(generated, "sequences", generated)
                if sequences.ndim != 2 or sequences.shape[0] != 1:
                    raise RuntimeError(
                        f"unexpected_generated_shape={tuple(sequences.shape)}"
                    )
                completion_ids = sequences[0, input_len:].detach().cpu().tolist()
                decoded = tokenizer.decode(completion_ids, skip_special_tokens=True)
                chunk_scores.append(extract_scores(decoded))

            aggregated = aggregate_scores(chunk_scores)
            for name, value in aggregated.items():
                all_scores[name].append(float(value))

            st["completed"] += 1
            st["note_tokens"].append(len(note_ids))
            st["chunks"].append(len(chunks))
            st["truncated_by_max_chunks"] += int(truncated)
            completed += 1
        except Exception as exc:
            failed += 1
            st["failed"] += 1
            errors[type(exc).__name__] += 1
        finally:
            st["inference_seconds"].append(time.perf_counter() - case_started)
            current = ordinal + 1
            update_progress(
                current=current,
                total=total,
                phase="diffusiongemma_real_note_pilot",
                message=f"Native HF DiffusionGemma pilot processed {current}/{total} local notes",
                unit="note",
            )

    inference_seconds = time.perf_counter() - inference_started
    all_values = [v for values in all_scores.values() for v in values]
    intermediate = [v for v in all_values if 0.0 < v < 1.0]

    safe_outcomes = {}
    for outcome, st in outcome_stats.items():
        note_tokens = st.pop("note_tokens")
        chunks = st.pop("chunks")
        times = st.pop("inference_seconds")
        safe_outcomes[outcome] = {
            **st,
            "note_tokens_summary": {
                "min": min(note_tokens) if note_tokens else None,
                "median": statistics.median(note_tokens) if note_tokens else None,
                "max": max(note_tokens) if note_tokens else None,
            },
            "chunks_summary": {
                "min": min(chunks) if chunks else None,
                "median": statistics.median(chunks) if chunks else None,
                "max": max(chunks) if chunks else None,
            },
            "seconds_per_attempt_summary": {
                "median": statistics.median(times) if times else None,
                "p90": quantile(times, 0.9) if times else None,
                "max": max(times) if times else None,
            },
        }

    per_construct = {}
    for name, values in all_scores.items():
        per_construct[name] = {
            "n": len(values),
            "unique_values": sorted(set(values)),
            "mean": statistics.fmean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "intermediate_fraction": (
                sum(1 for v in values if 0.0 < v < 1.0) / len(values)
                if values else None
            ),
        }

    seconds_per_attempt = inference_seconds / total if total else float("nan")
    report = {
        "analysis": "Native Hugging Face DiffusionGemma real-note operational pilot",
        "status": "completed" if failed == 0 and completed == total else "failed",
        "local_only": True,
        "network_required": False,
        "clinical_note_inference_performed": True,
        "contains_note_text": False,
        "contains_case_ids": False,
        "contains_patient_level_scores": False,
        "model": "google/diffusiongemma-26B-A4B-it",
        "backend": "transformers_native_bf16",
        "score_definition": (
            "Prompted zero-shot 0-1 support scores for the frozen eight semantic constructs; "
            "not Jev noul probabilities."
        ),
        "prompt_identical_to_synthetic_calibration": True,
        "aggregation_across_chunks": (
            "maximum for seven concern constructs; minimum for reassuring_stability"
        ),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "transformers_version": transformers.__version__,
        "seed": args.seed,
        "pilot_design": {
            "outcomes": OUTCOMES,
            "per_outcome": args.per_outcome,
            "attempted_total": total,
            "selection": "first usable frozen local-only cases in each prespecified outcome file",
        },
        "context_policy": {
            "context_limit_tokens": context_limit,
            "context_limit_source": context_limit_source,
            "empty_prompt_tokens": empty_prompt_tokens,
            "max_new_tokens": args.max_new_tokens,
            "note_chunk_tokens": chunk_tokens,
            "chunk_overlap_tokens": overlap,
            "max_chunks": args.max_chunks,
        },
        "model_load_seconds": model_load_seconds,
        "inference_seconds": inference_seconds,
        "seconds_per_attempt": seconds_per_attempt,
        "rough_full_12032_note_hours_at_pilot_rate": (
            seconds_per_attempt * 12032 / 3600.0
        ),
        "completed": completed,
        "failed": failed,
        "parse_or_inference_success_fraction": completed / total if total else 0.0,
        "error_type_counts": dict(errors),
        "global_unique_score_values": sorted(set(all_values)),
        "intermediate_value_fraction": (
            len(intermediate) / len(all_values) if all_values else 0.0
        ),
        "per_construct_score_summary": per_construct,
        "outcome_operational_summary": safe_outcomes,
        "next_gate": (
            "Review parse success, score resolution, chunk truncation, and throughput before "
            "launching full 12,032-note inference."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failed != 0 or completed != total:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
