from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from registration_gate import require_osf_registration
from runrelay_progress import update_progress


os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

BASE = Path("data/real_mimic_local/population_landmark12_v2_1")
POPULATION_CONTRACT = Path("config/v2_1_analysis_population_contract.json")
ATTESTATION = Path("docs/registration/exploratory_extension_osf_upload_attestation_2026-10-05.md")
PROTOCOL = Path("docs/registration/exploratory_extension_protocol_v2_1_2026-10-04.md")

MODEL_ID = "BAAI/bge-large-en-v1.5"
REVISION = "d4aa6901d3a41ba39fb536a557fa166f842b0e09"
SNAPSHOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--BAAI--bge-large-en-v1.5"
    / "snapshots"
    / REVISION
)
CHUNK_TOKENS = 448
OVERLAP_TOKENS = 64
STEP_TOKENS = CHUNK_TOKENS - OVERLAP_TOKENS
EXPECTED_DIM = 1024
EXPECTED_MAX_SEQ_LENGTH = 512

OUTCOMES = (
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_notes(path: Path) -> tuple[list[str], list[str]]:
    case_ids: list[str] = []
    texts: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("case_id"))
            if not cid or cid == "None" or cid in seen:
                raise RuntimeError("Missing or duplicate case_id in frozen note corpus")
            seen.add(cid)
            note = (rec.get("model_state") or {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"Missing note text for case_id={cid}")
            case_ids.append(cid)
            texts.append(note)
    if not case_ids:
        raise RuntimeError(f"Empty frozen note corpus: {path}")
    return case_ids, texts


def expected_note_ids(outcome: str, source: str) -> set[str]:
    path = BASE / outcome / "population_index_local.csv"
    frame = pd.read_csv(
        path,
        usecols=lambda c: c in {"case_id", "dbsource", "has_note"},
        low_memory=False,
    )
    required = {"case_id", "dbsource", "has_note"}
    if set(frame.columns) != required:
        missing = sorted(required - set(frame.columns))
        raise RuntimeError(f"{outcome}: population index missing columns {missing}")
    frame["case_id"] = frame["case_id"].astype(str)
    frame["dbsource"] = (
        frame["dbsource"].fillna("unknown").astype(str).str.strip().str.lower()
    )
    has_note = pd.to_numeric(frame["has_note"], errors="raise").astype(int).eq(1)
    return set(frame.loc[frame["dbsource"].eq(source) & has_note, "case_id"])


def token_windows(tokenizer, text: str) -> list[list[int]]:
    ids = tokenizer.encode(text, add_special_tokens=False)
    if not ids:
        raise RuntimeError("Tokenizer returned no content tokens")
    windows: list[list[int]] = []
    start = 0
    while start < len(ids):
        window = ids[start : start + CHUNK_TOKENS]
        if not window:
            break
        windows.append(window)
        if start + CHUNK_TOKENS >= len(ids):
            break
        start += STEP_TOKENS
    if not windows:
        raise RuntimeError("No embedding windows generated")
    return windows


def encode_documents(
    model,
    tokenizer,
    texts: list[str],
    *,
    note_batch_size: int,
    chunk_batch_size: int,
    progress_offset: int,
    progress_total: int,
    outcome: str,
) -> tuple[np.ndarray, dict]:
    vectors = np.zeros((len(texts), EXPECTED_DIM), dtype=np.float32)
    chunk_counts = np.zeros(len(texts), dtype=np.int32)
    token_counts = np.zeros(len(texts), dtype=np.int32)

    for batch_start in range(0, len(texts), note_batch_size):
        batch_end = min(len(texts), batch_start + note_batch_size)
        chunk_texts: list[str] = []
        owners: list[int] = []

        for local_i, text in enumerate(texts[batch_start:batch_end]):
            doc_i = batch_start + local_i
            windows = token_windows(tokenizer, text)
            chunk_counts[doc_i] = len(windows)
            token_counts[doc_i] = int(len(tokenizer.encode(text, add_special_tokens=False)))
            for window in windows:
                decoded = tokenizer.decode(
                    window,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
                if not decoded.strip():
                    raise RuntimeError(
                        f"{outcome}: decoded empty chunk for note index {doc_i}"
                    )
                chunk_texts.append(decoded)
                owners.append(doc_i)

        emb = model.encode(
            chunk_texts,
            batch_size=chunk_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        emb = np.asarray(emb, dtype=np.float32)
        if emb.ndim != 2 or emb.shape[1] != EXPECTED_DIM:
            raise RuntimeError(
                f"{outcome}: unexpected chunk embedding shape {emb.shape}"
            )
        if not np.isfinite(emb).all():
            raise RuntimeError(f"{outcome}: non-finite chunk embeddings")

        sums = np.zeros((batch_end - batch_start, EXPECTED_DIM), dtype=np.float64)
        counts = np.zeros(batch_end - batch_start, dtype=np.int32)
        for row, owner in zip(emb, owners):
            local_owner = owner - batch_start
            sums[local_owner] += row.astype(np.float64)
            counts[local_owner] += 1

        if np.any(counts <= 0):
            raise RuntimeError(f"{outcome}: note without encoded chunks")
        means = sums / counts[:, None]
        norms = np.linalg.norm(means, axis=1)
        if np.any(~np.isfinite(norms)) or np.any(norms <= 0):
            raise RuntimeError(f"{outcome}: invalid document embedding norm")
        means = means / norms[:, None]
        vectors[batch_start:batch_end] = means.astype(np.float32)

        update_progress(
            current=progress_offset + batch_end,
            total=progress_total,
            phase="extension_embedding_cache",
            message=f"{outcome}: embedded {batch_end}/{len(texts)} frozen notes",
            unit="note",
        )

    if not np.isfinite(vectors).all():
        raise RuntimeError(f"{outcome}: non-finite document embeddings")

    stats = {
        "notes": int(len(texts)),
        "total_chunks": int(chunk_counts.sum()),
        "chunks_per_note_min": int(chunk_counts.min()),
        "chunks_per_note_median": float(np.median(chunk_counts)),
        "chunks_per_note_max": int(chunk_counts.max()),
        "content_tokens_per_note_min": int(token_counts.min()),
        "content_tokens_per_note_median": float(np.median(token_counts)),
        "content_tokens_per_note_max": int(token_counts.max()),
    }
    return vectors, stats


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Cache the frozen BGE label-free document embeddings for the three "
            "primary MetaVision extension cohorts. Row-level embeddings remain local."
        )
    )
    ap.add_argument("--output", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--note-batch-size", type=int, default=32)
    ap.add_argument("--chunk-batch-size", type=int, default=64)
    args = ap.parse_args()

    require_osf_registration()
    for gate in (ATTESTATION, PROTOCOL):
        if not gate.exists():
            raise RuntimeError(f"Required extension gate missing: {gate}")
    if not SNAPSHOT.is_dir():
        raise RuntimeError(f"Frozen local model snapshot missing: {SNAPSHOT}")

    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(SNAPSHOT),
        local_files_only=True,
        use_fast=True,
    )
    model = SentenceTransformer(str(SNAPSHOT), device=args.device)
    max_seq_length = int(getattr(model, "max_seq_length", 0) or 0)
    if max_seq_length != EXPECTED_MAX_SEQ_LENGTH:
        raise RuntimeError(
            f"Frozen model max_seq_length={max_seq_length}, expected "
            f"{EXPECTED_MAX_SEQ_LENGTH}"
        )

    contract = json.loads(POPULATION_CONTRACT.read_text(encoding="utf-8"))
    expected_total = int(
        sum(
            int(contract["confirmatory_outcomes"][outcome]["note_available_rows"])
            for outcome in OUTCOMES
        )
    )

    report = {
        "analysis": "Paper 1 exploratory extension frozen embedding cache",
        "status": "started",
        "extension_status": "post-registration exploratory",
        "parent_registration": "ahxn9",
        "reads_outcome_labels": False,
        "network_used": False,
        "model": {
            "id": MODEL_ID,
            "revision": REVISION,
            "snapshot": str(SNAPSHOT),
            "embedding_dim": EXPECTED_DIM,
            "max_sequence_length": EXPECTED_MAX_SEQ_LENGTH,
            "chunk_content_tokens": CHUNK_TOKENS,
            "chunk_overlap_tokens": OVERLAP_TOKENS,
            "chunk_step_tokens": STEP_TOKENS,
            "chunk_embedding_normalization": "L2",
            "document_pooling": "unweighted arithmetic mean of normalized chunk embeddings",
            "document_normalization": "L2 after mean pooling",
            "query_prefix": None,
        },
        "outcomes": {},
        "guardrails": [
            "No outcome labels are read.",
            "No alternative embedding model is compared.",
            "The model and tokenizer are loaded from the frozen local snapshot with network disabled.",
            "Only frozen stripped primary landmark notes are embedded.",
            "Row-level embeddings and case identifiers remain local and are not declared as RunRelay artifacts.",
            "The shared artifact contains only aggregate counts and cryptographic hashes.",
        ],
    }

    progress_offset = 0
    for outcome in OUTCOMES:
        spec = contract["confirmatory_outcomes"][outcome]
        source = str(spec["source"]).strip().lower()
        if source != "metavision":
            raise RuntimeError(f"{outcome}: expected MetaVision primary source")

        note_path = BASE / outcome / "fixed_notes_stripped_v2_1_local.jsonl"
        case_ids, texts = load_notes(note_path)
        expected_n = int(spec["note_available_rows"])
        if len(case_ids) != expected_n:
            raise RuntimeError(
                f"{outcome}: note rows {len(case_ids)} != frozen {expected_n}"
            )
        ids_expected = expected_note_ids(outcome, source)
        if set(case_ids) != ids_expected:
            raise RuntimeError(
                f"{outcome}: frozen note corpus IDs differ from note-available cohort"
            )

        vectors, stats = encode_documents(
            model,
            tokenizer,
            texts,
            note_batch_size=int(args.note_batch_size),
            chunk_batch_size=int(args.chunk_batch_size),
            progress_offset=progress_offset,
            progress_total=expected_total,
            outcome=outcome,
        )
        progress_offset += len(texts)

        local_path = BASE / outcome / "extension_bge_large_embeddings_v2_1_local.npz"
        tmp_path = local_path.with_suffix(local_path.suffix + ".tmp")
        with tmp_path.open("wb") as handle:
            np.savez_compressed(
                handle,
                case_id=np.asarray(case_ids, dtype=str),
                embeddings=vectors,
            )
        tmp_path.replace(local_path)

        report["outcomes"][outcome] = {
            **stats,
            "expected_note_rows": expected_n,
            "embedding_shape": [int(vectors.shape[0]), int(vectors.shape[1])],
            "note_corpus_sha256": sha256_file(note_path),
            "local_embedding_file": str(local_path),
            "local_embedding_file_sha256": sha256_file(local_path),
        }

    if progress_offset != expected_total:
        raise RuntimeError(
            f"Embedded note total {progress_offset} != frozen expected {expected_total}"
        )

    report["status"] = "completed"
    report["total_notes"] = int(progress_offset)
    report["protocol_sha256"] = sha256_file(PROTOCOL)
    report["osf_upload_attestation_sha256"] = sha256_file(ATTESTATION)

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "total_notes": int(progress_offset),
                "outcomes": {
                    k: {
                        "notes": int(v["notes"]),
                        "total_chunks": int(v["total_chunks"]),
                        "embedding_shape": v["embedding_shape"],
                    }
                    for k, v in report["outcomes"].items()
                },
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
