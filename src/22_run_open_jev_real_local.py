from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


POSITIVE_CONSTRUCTS = {
    "overall_clinician_concern",
    "worsening_trajectory",
    "respiratory_concern",
    "hemodynamic_concern",
    "poor_treatment_response",
    "escalation_considered",
    "diagnostic_uncertainty",
}


def chunk_token_ids(token_ids: list[int], size: int, overlap: int, max_chunks: int) -> list[list[int]]:
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


def make_questions(case: dict) -> tuple[list[str], list[dict]]:
    names = []
    questions = []
    for q in case["questions"]:
        if q.get("type") != "noul":
            raise ValueError("Real pilot currently supports noul questions only.")
        text = str(q["question"])
        criteria = q.get("criteria")
        if isinstance(criteria, dict):
            text += (
                "\nTrue criterion: " + str(criteria.get("true", "")) +
                "\nFalse criterion: " + str(criteria.get("false", ""))
            )
        names.append(str(q["name"]))
        questions.append({"type": "noul", "instructions": text})
    return names, questions


def aggregate_probabilities(name: str, values: list[float]) -> float:
    if not values:
        return float("nan")
    if name == "reassuring_stability":
        return float(min(values))
    return float(max(values))


def context_safe_question_packs(
    model,
    state: str,
    names: list[str],
    questions: list[dict],
    max_questions_per_pack: int,
) -> list[tuple[list[str], list[dict]]]:
    """Greedily form the largest question packs that fit the model context."""
    packs: list[tuple[list[str], list[dict]]] = []
    current_names: list[str] = []
    current_questions: list[dict] = []

    def fits(qs: list[dict]) -> bool:
        typed = [model._question(i, q) for i, q in enumerate(qs)]
        try:
            model.collator.encode_one(state, typed)
            return True
        except ValueError as exc:
            if "max_len" in str(exc):
                return False
            raise

    for name, question in zip(names, questions):
        trial_names = current_names + [name]
        trial_questions = current_questions + [question]

        if (
            len(trial_questions) <= max_questions_per_pack
            and fits(trial_questions)
        ):
            current_names = trial_names
            current_questions = trial_questions
            continue

        if current_questions:
            packs.append((current_names, current_questions))
            current_names = [name]
            current_questions = [question]
        else:
            current_names = [name]
            current_questions = [question]

        if not fits(current_questions):
            raise RuntimeError(
                "A single semantic question does not fit the Open-Jev context "
                "with the current note chunk. Reduce --chunk-tokens."
            )

    if current_questions:
        packs.append((current_names, current_questions))

    return packs


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run Open-Jev on credentialed real-note cases strictly offline, using "
            "token chunks so long notes are not silently reduced to the first 256 tokens."
        )
    )
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", default="com-kotobalabs/open-jev-deberta-v3-large")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--questions-per-pack", type=int, default=4)
    ap.add_argument("--chunk-tokens", type=int, default=220)
    ap.add_argument("--chunk-overlap", type=int, default=40)
    ap.add_argument("--max-chunks", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    # Force offline mode before importing Hugging Face-backed code.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from typed_decisions.open_jev import OpenJev

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

    print(f"Loading cached model offline: {args.model}")
    model = OpenJev.from_pretrained(args.model, device=args.device)
    print(f"Device: {model.device}")

    completed = 0
    with out.open("w", encoding="utf-8") as f:
        for case in cases:
            note = str(case["model_state"]["clinical_note"])
            token_ids = model.tok(
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
                model.tok.decode(ids, skip_special_tokens=True)
                for ids in chunks
            ]

            names, questions = make_questions(case)
            per_construct = {name: [] for name in names}

            pack_sizes_used = []
            for chunk_text in chunk_texts:
                packs = context_safe_question_packs(
                    model,
                    chunk_text,
                    names,
                    questions,
                    max_questions_per_pack=args.questions_per_pack,
                )
                pack_sizes_used.extend(len(q_pack) for _, q_pack in packs)
                for n_pack, q_pack in packs:
                    answers = model.decide(chunk_text, q_pack)
                    for name, answer in zip(n_pack, answers):
                        p = answer.get("noul")
                        if isinstance(p, (int, float)):
                            per_construct[name].append(float(p))

            aggregate = {
                name: {
                    "noul": aggregate_probabilities(name, values),
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
                    "question_pack_max_requested": args.questions_per_pack,
                    "question_pack_sizes_used": sorted(set(pack_sizes_used)),
                    "aggregation": (
                        "max across chunks for concern constructs; "
                        "min across chunks for reassuring_stability"
                    ),
                },
                "model": args.model,
                "backend": "open_jev_real_local_chunked",
                "response": {"answers": aggregate},
                "status": "ok",
            }
            # Credentialed note text is intentionally never written to the prediction output.
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            completed += 1

    print(
        json.dumps(
            {
                "cases_attempted": len(cases),
                "completed": completed,
                "failed": 0,
                "forced_offline": True,
                "raw_note_text_written_to_predictions": False,
                "question_packing": "automatic context-safe greedy packing",
                "output": str(out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
