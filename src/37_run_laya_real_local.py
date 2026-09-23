from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from runrelay_progress import update_progress


POSITIVE_CONSTRUCTS = {
    "overall_clinician_concern",
    "worsening_trajectory",
    "respiratory_concern",
    "hemodynamic_concern",
    "poor_treatment_response",
    "escalation_considered",
    "diagnostic_uncertainty",
}


def chunk_token_ids(
    token_ids: list[int],
    size: int,
    overlap: int,
    max_chunks: int,
) -> list[list[int]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk size")
    if not token_ids:
        return [[]]

    step = size - overlap
    chunks = []
    start = 0
    while start < len(token_ids):
        chunks.append(token_ids[start:start + size])
        if len(chunks) >= max_chunks:
            break
        if start + size >= len(token_ids):
            break
        start += step
    return chunks


def make_questions(case: dict) -> dict:
    questions = {}
    for q in case["questions"]:
        if q.get("type") != "noul":
            raise ValueError("Laya robustness runner currently supports noul questions only.")
        text = str(q["question"])
        criteria = q.get("criteria")
        if isinstance(criteria, dict):
            text += (
                "\nTrue criterion: " + str(criteria.get("true", "")) +
                "\nFalse criterion: " + str(criteria.get("false", ""))
            )
        questions[str(q["name"])] = {
            "type": "noul",
            "instructions": text,
        }
    return questions


def aggregate_probability(name: str, values: list[float]) -> float:
    if not values:
        return float("nan")
    if name == "reassuring_stability":
        return float(min(values))
    return float(max(values))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run a pinned local Laya checkpoint on credentialed real-note cases. "
            "Clinical text is read only after all network access is disabled."
        )
    )
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument(
        "--model-dir",
        default="~/.cache/mimic-semantic-signals/laya-typed-decisions-f9ab0b2",
    )
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--chunk-tokens", type=int, default=600)
    ap.add_argument("--chunk-overlap", type=int, default=100)
    ap.add_argument("--max-chunks", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--progress-offset", type=int, default=0)
    ap.add_argument("--progress-total", type=int, default=0)
    ap.add_argument("--progress-phase", default="semantic_inference")
    args = ap.parse_args()

    model_dir = Path(args.model_dir).expanduser().resolve()
    if not (model_dir / "model.safetensors").exists():
        raise FileNotFoundError(
            f"Pinned Laya model not cached at {model_dir}. "
            "Run src/36_cache_laya_typed_decisions.py first."
        )

    # Disable network before importing/loading model code and before opening cases.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["USE_TF"] = "0"

    import laya

    print(f"Loading pinned local Laya model offline: {model_dir}")
    agent = laya.load(str(model_dir), device=args.device)
    tok = agent.tok

    cases_path = Path(args.cases).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cases = []
    with cases_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("synthetic_only") is True:
                raise RuntimeError("This runner is for real local-only cases, not synthetic cases.")
            if rec.get("local_only") is not True:
                raise RuntimeError("Refusing a real case not explicitly marked local_only=true.")
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                continue
            cases.append(rec)

    if args.limit > 0:
        cases = cases[:args.limit]
    if not cases:
        raise RuntimeError("No usable real local-only cases found.")

    completed = 0
    failed = 0

    with out.open("w", encoding="utf-8") as f:
        for case in cases:
            try:
                note = str(case["model_state"]["clinical_note"])
                token_ids = tok(
                    note,
                    add_special_tokens=False,
                )["input_ids"]
                chunks = chunk_token_ids(
                    token_ids,
                    size=args.chunk_tokens,
                    overlap=args.chunk_overlap,
                    max_chunks=args.max_chunks,
                )
                chunk_texts = [
                    tok.decode(ids, skip_special_tokens=True)
                    for ids in chunks
                ]

                questions = make_questions(case)
                per_construct = {name: [] for name in questions}

                for chunk_text in chunk_texts:
                    result = agent.predict(chunk_text, questions)
                    answers = result.get("answers", {})
                    for name in questions:
                        answer = answers.get(name, {})
                        p = answer.get("noul")
                        if isinstance(p, (int, float)):
                            per_construct[name].append(float(p))

                aggregate = {
                    name: {
                        "noul": aggregate_probability(name, values),
                        "chunk_values": values,
                    }
                    for name, values in per_construct.items()
                }

                record = {
                    "case_id": case.get("case_id"),
                    "synthetic_only": False,
                    "local_only": True,
                    "metadata": {
                        **case.get("metadata", {}),
                        "note_tokens": len(token_ids),
                        "chunks_evaluated": len(chunk_texts),
                        "chunk_tokens": args.chunk_tokens,
                        "chunk_overlap": args.chunk_overlap,
                        "max_chunks": args.max_chunks,
                        "aggregation": (
                            "max across chunks for concern constructs; "
                            "min across chunks for reassuring_stability"
                        ),
                    },
                    "model": str(model_dir),
                    "backend": "laya_typed_decisions_real_local_chunked",
                    "response": {"answers": aggregate},
                    "status": "ok",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                completed += 1
                if completed % 25 == 0 or completed + failed == len(cases):
                    total = args.progress_total if args.progress_total > 0 else len(cases)
                    current = args.progress_offset + completed + failed
                    update_progress(
                        current=current,
                        total=total,
                        phase=args.progress_phase,
                        message=f"Laya completed {current}/{total} frozen benchmark notes",
                        unit="note",
                    )
            except Exception as exc:
                failed += 1
                f.write(
                    json.dumps(
                        {
                            "case_id": case.get("case_id"),
                            "synthetic_only": False,
                            "local_only": True,
                            "backend": "laya_typed_decisions_real_local_chunked",
                            "status": "error",
                            "error": type(exc).__name__ + ": " + str(exc),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                f.flush()
                if (completed + failed) % 25 == 0 or completed + failed == len(cases):
                    total = args.progress_total if args.progress_total > 0 else len(cases)
                    current = args.progress_offset + completed + failed
                    update_progress(
                        current=current,
                        total=total,
                        phase=args.progress_phase,
                        message=f"Laya completed {current}/{total} frozen benchmark notes",
                        unit="note",
                    )

    print(
        json.dumps(
            {
                "cases_attempted": len(cases),
                "completed": completed,
                "failed": failed,
                "forced_offline_before_case_read": True,
                "raw_note_text_written_to_predictions": False,
                "model_dir": str(model_dir),
                "output": str(out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
