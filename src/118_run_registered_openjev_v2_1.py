from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
from pathlib import Path

from runrelay_progress import update_progress
from semantic_schema import SEMANTIC_CONSTRUCTS
from v2_1_registered_inference_contract import assert_registered_instrument


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
        if len(chunks) >= max_chunks or start + size >= len(token_ids):
            break
        start += step
    return chunks


def registered_questions() -> tuple[list[str], list[dict]]:
    names = []
    questions = []
    for q in SEMANTIC_CONSTRUCTS:
        text = str(q["question"])
        criteria = q.get("criteria") or {}
        text += (
            "\nTrue criterion: " + str(criteria.get("true", "")) +
            "\nFalse criterion: " + str(criteria.get("false", ""))
        )
        names.append(str(q["name"]))
        questions.append({"type": "noul", "instructions": text})
    return names, questions


def aggregate_probabilities(name: str, values: list[float]) -> float:
    if not values:
        raise RuntimeError(f"No semantic values produced for {name}")
    if name == "reassuring_stability":
        return float(min(values))
    return float(max(values))


def context_safe_question_packs(model, state: str, names: list[str], questions: list[dict], max_questions_per_pack: int):
    packs = []
    current_names = []
    current_questions = []

    def fits(qs):
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
        if len(trial_questions) <= max_questions_per_pack and fits(trial_questions):
            current_names = trial_names
            current_questions = trial_questions
            continue
        if current_questions:
            packs.append((current_names, current_questions))
        current_names = [name]
        current_questions = [question]
        if not fits(current_questions):
            raise RuntimeError("A single registered semantic question does not fit the model context.")
    if current_questions:
        packs.append((current_names, current_questions))
    return packs


def resolve_typed_decisions_commit() -> str:
    # For an installed VCS package, direct_url.json is the authoritative
    # provenance record. Do not walk parent directories looking for .git:
    # the virtual environment may live inside the Medical JEV repository,
    # which would falsely return the project commit.
    for dist_name in ("typed-decisions", "typed_decisions"):
        try:
            dist = importlib.metadata.distribution(dist_name)
        except importlib.metadata.PackageNotFoundError:
            continue
        direct = dist.read_text("direct_url.json")
        if direct:
            try:
                data = json.loads(direct)
            except json.JSONDecodeError:
                data = {}
            commit = ((data.get("vcs_info") or {}).get("commit_id"))
            if commit:
                return str(commit)

    raise RuntimeError(
        "Cannot verify typed-decisions VCS commit from installed package metadata; "
        "refusing registered inference."
    )

def main() -> None:
    ap = argparse.ArgumentParser(description="Run registered v2.1 Open-Jev inference on one frozen local note corpus.")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected", type=int, required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--questions-per-pack", type=int, default=4)
    ap.add_argument("--progress-phase", default="v2_1_openjev_inference")
    args = ap.parse_args()

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    expected = assert_registered_instrument(
        "open_jev",
        model_id="com-kotobalabs/open-jev-deberta-v3-large",
        revision="19bf9a64815add579fbf6c907bef584d9277a8e4",
        chunk_tokens=220,
        chunk_overlap_tokens=40,
        max_chunks=8,
        typed_decisions_commit="10d7834d3b99041f890db4615fb38ef95ced50cc",
    )

    observed_typed_commit = resolve_typed_decisions_commit()
    if observed_typed_commit != expected["typed_decisions_commit"]:
        raise RuntimeError(
            "V2.1 INFERENCE LOCKED: installed typed-decisions commit "
            f"{observed_typed_commit} != registered {expected['typed_decisions_commit']}"
        )

    from huggingface_hub import snapshot_download
    from typed_decisions.open_jev import OpenJev

    snapshot = snapshot_download(
        repo_id=expected["model_id"],
        revision=expected["model_revision"],
        local_files_only=True,
    )
    snapshot_path = Path(snapshot).resolve()
    if snapshot_path.name != expected["model_revision"]:
        raise RuntimeError(
            f"V2.1 INFERENCE LOCKED: resolved Open-Jev snapshot {snapshot_path.name} "
            f"!= registered revision {expected['model_revision']}"
        )

    model = OpenJev.from_pretrained(str(snapshot_path), device=args.device)
    names, questions = registered_questions()

    cases_path = Path(args.cases).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    records = []
    with cases_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("local_only") is not True:
                raise RuntimeError("Refusing case not explicitly marked local_only=true.")
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError("Frozen note corpus contains a missing/blank note.")
            records.append(rec)

    if len(records) != args.expected:
        raise RuntimeError(f"Frozen corpus count {len(records)} != expected {args.expected}")

    seen = set()
    with out.open("w", encoding="utf-8") as handle:
        for i, rec in enumerate(records, start=1):
            case_id = str(rec.get("case_id"))
            if not case_id or case_id == "None" or case_id in seen:
                raise RuntimeError("Missing or duplicate case_id in frozen note corpus.")
            seen.add(case_id)

            note = str(rec["model_state"]["clinical_note"])
            token_ids = model.tok(note, add_special_tokens=False)["input_ids"]
            chunks = chunk_token_ids(
                token_ids,
                size=int(expected["chunk_tokens"]),
                overlap=int(expected["chunk_overlap_tokens"]),
                max_chunks=int(expected["max_chunks"]),
            )
            chunk_texts = [model.tok.decode(ids, skip_special_tokens=True) for ids in chunks]
            per_construct = {name: [] for name in names}
            pack_sizes = []

            for chunk_text in chunk_texts:
                packs = context_safe_question_packs(
                    model,
                    chunk_text,
                    names,
                    questions,
                    max_questions_per_pack=int(args.questions_per_pack),
                )
                pack_sizes.extend(len(qp) for _, qp in packs)
                for name_pack, question_pack in packs:
                    answers = model.decide(chunk_text, question_pack)
                    for name, answer in zip(name_pack, answers):
                        value = answer.get("noul")
                        if not isinstance(value, (int, float)):
                            raise RuntimeError(f"Missing numeric Open-Jev score for {name}")
                        per_construct[name].append(float(value))

            aggregate = {
                name: {
                    "noul": aggregate_probabilities(name, values),
                    "chunk_values": values,
                }
                for name, values in per_construct.items()
            }

            result = {
                "case_id": case_id,
                "local_only": True,
                "status": "ok",
                "model": expected["model_id"],
                "model_revision": expected["model_revision"],
                "typed_decisions_commit": observed_typed_commit,
                "semantic_schema_source": "src/semantic_schema.py",
                "metadata": {
                    "corpus_variant": (rec.get("metadata") or {}).get("corpus_variant"),
                    "source_system_analysis": (rec.get("metadata") or {}).get("source_system_analysis"),
                    "note_tokens": len(token_ids),
                    "chunks_evaluated": len(chunks),
                    "chunk_tokens": int(expected["chunk_tokens"]),
                    "chunk_overlap": int(expected["chunk_overlap_tokens"]),
                    "max_chunks": int(expected["max_chunks"]),
                    "question_pack_max_requested": int(args.questions_per_pack),
                    "question_pack_sizes_used": sorted(set(pack_sizes)),
                    "aggregation": "maximum across chunks except minimum for reassuring_stability",
                },
                "response": {"answers": aggregate},
            }
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()

            if i % 25 == 0 or i == len(records):
                update_progress(
                    current=i,
                    total=len(records),
                    phase=args.progress_phase,
                    message=f"Registered Open-Jev completed {i}/{len(records)} frozen notes",
                    unit="note",
                )

    print(json.dumps({
        "completed": len(records),
        "failed": 0,
        "model_id": expected["model_id"],
        "model_revision": expected["model_revision"],
        "typed_decisions_commit": observed_typed_commit,
        "questions_per_pack": int(args.questions_per_pack),
        "forced_offline": True,
        "raw_note_text_written_to_predictions": False,
        "output": str(out),
    }, indent=2))


if __name__ == "__main__":
    main()
