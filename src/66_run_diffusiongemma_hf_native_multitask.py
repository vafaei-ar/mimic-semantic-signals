from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import time
from collections import Counter
from pathlib import Path

from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS


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
        parts.extend(
            [
                f"- {q['name']}: {q['question']}",
                f"  TRUE: {q['criteria']['true']}",
                f"  FALSE: {q['criteria']['false']}",
            ]
        )
    parts.extend(
        [
            "",
            "Required JSON keys in this exact order:",
            ", ".join(EXPECTED),
        ]
    )
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


def parse_structure_signature(text: str) -> str:
    candidates = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
    parseable = 0
    max_expected_keys = 0
    for raw in candidates:
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            parseable += 1
            max_expected_keys = max(
                max_expected_keys,
                sum(1 for name in EXPECTED if name in obj),
            )
    mentions = sum(1 for name in EXPECTED if name in text)
    char_bucket = (len(text) // 100) * 100
    return (
        f"json_candidates={len(candidates)}|parseable_objects={parseable}|"
        f"max_expected_keys={max_expected_keys}|expected_key_mentions={mentions}|"
        f"chars_bucket={char_bucket}"
    )


def load_cases(path: Path) -> list[dict]:
    cases: list[dict] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("synthetic_only") is True:
                raise RuntimeError(f"{path}: synthetic case found in real-note inference")
            if rec.get("local_only") is not True:
                raise RuntimeError(f"{path}: refusing case without local_only=true")
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"{path}: blank clinical note in frozen cohort")
            question_names = [str(q.get("name")) for q in rec.get("questions", [])]
            if question_names != EXPECTED:
                raise RuntimeError(
                    f"{path}: frozen semantic question schema mismatch: {question_names}"
                )
            case_id = str(rec.get("case_id"))
            if not case_id or case_id == "None":
                raise RuntimeError(f"{path}: missing case_id")
            if case_id in seen:
                raise RuntimeError(f"{path}: duplicate case_id")
            seen.add(case_id)
            cases.append(rec)
    if not cases:
        raise RuntimeError(f"{path}: no usable cases")
    return cases


def load_success_ids(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("status") == "ok" and rec.get("case_id") is not None:
                out.add(str(rec["case_id"]))
    return out


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


def chunk_token_ids(
    ids: list[int],
    size: int,
    overlap: int,
    max_chunks: int,
) -> tuple[list[list[int]], bool]:
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


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
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


def safe_summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "min": None, "median": None, "p90": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "p90": quantile(values, 0.9),
        "max": max(values),
    }


def write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run native Hugging Face DiffusionGemma fully offline on the frozen "
            "multi-outcome local MIMIC cohorts. Row-level predictions remain local."
        )
    )
    ap.add_argument("--base", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--expected-total", type=int, default=12032)
    ap.add_argument("--max-chunks", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--parse-retries", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20260923)
    args = ap.parse_args()

    import torch
    import transformers
    from transformers import AutoProcessor, DiffusionGemmaForBlockDiffusion

    base = Path(args.base).expanduser().resolve()
    model_dir = Path(args.model_dir).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()

    if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
        raise RuntimeError("Native BF16 DiffusionGemma inference requires at least two visible GPUs.")

    outcome_cases: dict[str, list[dict]] = {}
    selected: list[tuple[str, int, dict]] = []
    global_ordinal = 0
    for outcome in OUTCOMES:
        cases = load_cases(base / outcome / "cases.jsonl")
        outcome_cases[outcome] = cases
        for rec in cases:
            selected.append((outcome, global_ordinal, rec))
            global_ordinal += 1

    if len(selected) != args.expected_total:
        raise RuntimeError(
            f"Frozen cohort total mismatch: expected {args.expected_total}, found {len(selected)}"
        )

    output_paths = {
        outcome: base / outcome / "diffusiongemma_hf_raw.jsonl"
        for outcome in OUTCOMES
    }
    existing_success = {
        outcome: load_success_ids(output_paths[outcome])
        for outcome in OUTCOMES
    }
    existing_total = sum(len(x) for x in existing_success.values())

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
    first_device = next(model.parameters()).device

    outcome_stats = {
        outcome: {
            "expected": len(outcome_cases[outcome]),
            "resumed_successes": len(existing_success[outcome]),
            "new_successes": 0,
            "new_failures": 0,
            "truncated_by_max_chunks": 0,
            "parse_retries_used_total": 0,
            "chunks_using_parse_retry": 0,
            "note_tokens": [],
            "chunks": [],
            "seconds": [],
        }
        for outcome in OUTCOMES
    }
    error_types: Counter[str] = Counter()
    failure_stages: Counter[str] = Counter()
    parse_signatures: Counter[str] = Counter()
    all_scores: dict[str, list[float]] = {name: [] for name in EXPECTED}

    handles = {
        outcome: output_paths[outcome].open("a", encoding="utf-8")
        for outcome in OUTCOMES
    }

    run_started = time.perf_counter()
    last_report_at = 0

    def build_safe_report(status: str) -> dict:
        current_success = {
            outcome: len(existing_success[outcome]) + outcome_stats[outcome]["new_successes"]
            for outcome in OUTCOMES
        }
        completed_total = sum(current_success.values())
        new_failures = sum(outcome_stats[o]["new_failures"] for o in OUTCOMES)
        safe_outcomes = {}
        for outcome in OUTCOMES:
            st = outcome_stats[outcome]
            safe_outcomes[outcome] = {
                "expected": st["expected"],
                "resumed_successes": st["resumed_successes"],
                "new_successes": st["new_successes"],
                "new_failures": st["new_failures"],
                "successful_rows_available": current_success[outcome],
                "truncated_by_max_chunks": st["truncated_by_max_chunks"],
                "parse_retries_used_total": st["parse_retries_used_total"],
                "chunks_using_parse_retry": st["chunks_using_parse_retry"],
                "note_tokens_summary_new": safe_summary(st["note_tokens"]),
                "chunks_summary_new": safe_summary(st["chunks"]),
                "seconds_per_new_attempt_summary": safe_summary(st["seconds"]),
            }

        score_summary = {}
        for name, values in all_scores.items():
            score_summary[name] = {
                "n_new": len(values),
                "unique_values_new": sorted(set(values)),
                "mean_new": statistics.fmean(values) if values else None,
                "intermediate_fraction_new": (
                    sum(1 for v in values if 0.0 < v < 1.0) / len(values)
                    if values else None
                ),
            }

        elapsed = time.perf_counter() - run_started
        return {
            "analysis": "Native Hugging Face DiffusionGemma full multi-outcome semantic inference",
            "status": status,
            "local_only": True,
            "network_required": False,
            "clinical_note_inference_performed": True,
            "contains_note_text": False,
            "contains_case_ids": False,
            "contains_patient_level_scores": False,
            "row_level_predictions_shared": False,
            "model": "google/diffusiongemma-26B-A4B-it",
            "backend": "transformers_native_bf16",
            "score_definition": (
                "Prompted zero-shot 0-1 support scores for the frozen eight semantic constructs; "
                "not Jev noul probabilities."
            ),
            "aggregation_across_chunks": (
                "maximum for seven concern constructs; minimum for reassuring_stability"
            ),
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "transformers_version": transformers.__version__,
            "seed": args.seed,
            "seed_schedule": "base_seed + global_note_ordinal*1000 + chunk_index*10 + attempt",
            "parse_retry_policy": {
                "max_retries_after_initial_generation": args.parse_retries,
                "prompt_changes_on_retry": False,
                "acceptance": "first completion containing all eight numeric scores in [0,1]",
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
            "expected_total": args.expected_total,
            "resumed_successes_total": existing_total,
            "successful_rows_available_total": completed_total,
            "new_failures_total": new_failures,
            "model_load_seconds": model_load_seconds,
            "run_elapsed_seconds": elapsed,
            "error_type_counts": dict(error_types),
            "failure_stage_counts": dict(failure_stages),
            "parse_failure_structural_signatures": dict(parse_signatures),
            "per_construct_new_score_summary": score_summary,
            "outcomes": safe_outcomes,
            "next_gate": (
                "Evaluate aggregate predictive performance only after all 12,032 frozen notes "
                "have successful local DiffusionGemma scores."
            ),
        }

    try:
        update_progress(
            current=existing_total,
            total=args.expected_total,
            phase="diffusiongemma_multitask_inference",
            message=f"Native HF DiffusionGemma has {existing_total}/{args.expected_total} successful local notes available",
            unit="note",
        )
        write_report(report_path, build_safe_report("running"))

        for outcome, ordinal, case in selected:
            case_id = str(case["case_id"])
            if case_id in existing_success[outcome]:
                if (ordinal + 1) % 100 == 0:
                    update_progress(
                        current=sum(len(existing_success[o]) + outcome_stats[o]["new_successes"] for o in OUTCOMES),
                        total=args.expected_total,
                        phase="diffusiongemma_multitask_inference",
                        message="Resuming cached successful DiffusionGemma rows",
                        unit="note",
                    )
                continue

            st = outcome_stats[outcome]
            case_started = time.perf_counter()
            stage = "read_note"
            decoded: str | None = None
            note_tokens = 0
            chunk_count = 0
            truncated = False
            try:
                note = str(case["model_state"]["clinical_note"])
                stage = "tokenize_note"
                note_ids = tokenizer(note, add_special_tokens=False)["input_ids"]
                note_tokens = len(note_ids)
                stage = "chunk_note"
                chunks, truncated = chunk_token_ids(
                    note_ids,
                    size=chunk_tokens,
                    overlap=overlap,
                    max_chunks=args.max_chunks,
                )
                chunk_count = len(chunks)
                chunk_scores: list[dict[str, float]] = []
                chunk_retry_counts: list[int] = []

                for chunk_index, ids in enumerate(chunks):
                    chunk_text = tokenizer.decode(ids, skip_special_tokens=True)
                    stage = "apply_chat_template"
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

                    parsed = None
                    retries_used = 0
                    for attempt in range(args.parse_retries + 1):
                        local_seed = args.seed + ordinal * 1000 + chunk_index * 10 + attempt
                        torch.manual_seed(local_seed)
                        torch.cuda.manual_seed_all(local_seed)
                        stage = "generate"
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
                        stage = "decode_completion"
                        completion_ids = sequences[0, input_len:].detach().cpu().tolist()
                        decoded = tokenizer.decode(completion_ids, skip_special_tokens=True)
                        stage = "parse_completion"
                        try:
                            parsed = extract_scores(decoded)
                            retries_used = attempt
                            break
                        except ValueError:
                            if attempt >= args.parse_retries:
                                raise
                    if parsed is None:
                        raise RuntimeError("parse retry loop ended without scores")
                    chunk_scores.append(parsed)
                    chunk_retry_counts.append(retries_used)

                stage = "aggregate_scores"
                aggregated = aggregate_scores(chunk_scores)
                answers = {
                    name: {
                        "score": float(aggregated[name]),
                        "chunk_values": [float(row[name]) for row in chunk_scores],
                    }
                    for name in EXPECTED
                }
                record = {
                    "case_id": case_id,
                    "synthetic_only": False,
                    "local_only": True,
                    "model": "google/diffusiongemma-26B-A4B-it",
                    "backend": "transformers_native_bf16_prompted_semantic_scores",
                    "metadata": {
                        "note_tokens": note_tokens,
                        "chunks_evaluated": chunk_count,
                        "chunk_tokens": chunk_tokens,
                        "chunk_overlap": overlap,
                        "max_chunks": args.max_chunks,
                        "truncated_by_max_chunks": bool(truncated),
                        "parse_retries_by_chunk": chunk_retry_counts,
                        "seed_schedule": "base_seed + global_note_ordinal*1000 + chunk_index*10 + attempt",
                        "aggregation": (
                            "max across chunks for concern constructs; "
                            "min across chunks for reassuring_stability"
                        ),
                    },
                    "response": {"answers": answers},
                    "status": "ok",
                }
                handles[outcome].write(json.dumps(record, ensure_ascii=False) + "\n")
                handles[outcome].flush()

                st["new_successes"] += 1
                st["note_tokens"].append(note_tokens)
                st["chunks"].append(chunk_count)
                st["truncated_by_max_chunks"] += int(truncated)
                used_total = sum(chunk_retry_counts)
                st["parse_retries_used_total"] += used_total
                st["chunks_using_parse_retry"] += sum(1 for x in chunk_retry_counts if x > 0)
                for name, value in aggregated.items():
                    all_scores[name].append(float(value))
            except Exception as exc:
                st["new_failures"] += 1
                error_types[type(exc).__name__] += 1
                failure_stages[stage] += 1
                if stage == "parse_completion" and isinstance(decoded, str):
                    parse_signatures[parse_structure_signature(decoded)] += 1
                error_record = {
                    "case_id": case_id,
                    "synthetic_only": False,
                    "local_only": True,
                    "model": "google/diffusiongemma-26B-A4B-it",
                    "backend": "transformers_native_bf16_prompted_semantic_scores",
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "failure_stage": stage,
                }
                handles[outcome].write(json.dumps(error_record, ensure_ascii=False) + "\n")
                handles[outcome].flush()
            finally:
                st["seconds"].append(time.perf_counter() - case_started)

            successes_now = sum(
                len(existing_success[o]) + outcome_stats[o]["new_successes"]
                for o in OUTCOMES
            )
            attempted_new = sum(
                outcome_stats[o]["new_successes"] + outcome_stats[o]["new_failures"]
                for o in OUTCOMES
            )
            if attempted_new % 25 == 0 or successes_now == args.expected_total:
                update_progress(
                    current=successes_now,
                    total=args.expected_total,
                    phase="diffusiongemma_multitask_inference",
                    message=f"Native HF DiffusionGemma has {successes_now}/{args.expected_total} successful local notes available",
                    unit="note",
                )
            if attempted_new - last_report_at >= 100:
                write_report(report_path, build_safe_report("running"))
                last_report_at = attempted_new

        final_success = sum(
            len(existing_success[o]) + outcome_stats[o]["new_successes"]
            for o in OUTCOMES
        )
        final_failures = sum(outcome_stats[o]["new_failures"] for o in OUTCOMES)
        final_status = (
            "completed"
            if final_success == args.expected_total and final_failures == 0
            else "failed"
        )
        write_report(report_path, build_safe_report(final_status))
        if final_status != "completed":
            raise SystemExit(2)
    finally:
        for handle in handles.values():
            handle.close()


if __name__ == "__main__":
    main()
