from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset

from runrelay_progress import update_progress


OUTCOMES = [
    "invasive_ventilation",
    "renal_replacement_therapy",
    "icu_death",
]
OUTCOME_TO_INDEX = {name: i for i, name in enumerate(OUTCOMES)}


@dataclass
class NoteExample:
    case_id: str
    outcome: str
    outcome_index: int
    label: int
    chunks: list[list[int]]
    note_tokens: int
    truncated: bool
    weight: float = 1.0


class NoteDataset(Dataset):
    def __init__(self, rows: list[NoteExample]):
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> NoteExample:
        return self.rows[index]


class MultiTaskDeberta(nn.Module):
    def __init__(self, encoder: nn.Module, hidden_size: int, tasks: int = 3):
        super().__init__()
        self.encoder = encoder
        self.dropout = nn.Dropout(0.1)
        self.head = nn.Linear(hidden_size, tasks)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0]
        return self.head(self.dropout(cls))


def discover_checkpoint() -> Path:
    root = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--com-kotobalabs--open-jev-deberta-v3-large"
        / "snapshots"
    )
    candidates = sorted(p for p in root.glob("*") if p.is_dir() and (p / "config.json").exists())
    if not candidates:
        raise FileNotFoundError("Cached Open-Jev DeBERTa checkpoint was not found.")
    return candidates[-1].resolve()


def chunk_ids(ids: list[int], size: int, overlap: int, max_chunks: int) -> tuple[list[list[int]], bool]:
    if size <= 0 or overlap < 0 or overlap >= size or max_chunks <= 0:
        raise ValueError("Invalid chunking configuration.")
    if not ids:
        return [[]], False
    chunks = []
    step = size - overlap
    start = 0
    while start < len(ids):
        chunks.append(ids[start:start + size])
        if len(chunks) >= max_chunks or start + size >= len(ids):
            break
        start += step
    covered_to = min(len(ids), (len(chunks) - 1) * step + len(chunks[-1]))
    return chunks, covered_to < len(ids)


def stratified_limit(rows: list[dict], limit: int, seed: int) -> list[dict]:
    if limit <= 0 or len(rows) <= limit:
        return rows
    rng = random.Random(seed)
    by_label = {0: [], 1: []}
    for r in rows:
        by_label[int(r["label"])].append(r)
    for values in by_label.values():
        rng.shuffle(values)
    pos_target = max(2, int(round(limit * 0.25)))
    neg_target = limit - pos_target
    selected = by_label[1][:pos_target] + by_label[0][:neg_target]
    rng.shuffle(selected)
    return selected


def load_split(
    base: Path,
    split: str,
    tokenizer,
    *,
    chunk_tokens: int,
    chunk_overlap: int,
    max_chunks: int,
    limit_per_outcome: int,
    seed: int,
) -> list[NoteExample]:
    if split == "test":
        raise RuntimeError("Development code is forbidden from reading the locked test split.")
    examples: list[NoteExample] = []
    for outcome_i, outcome in enumerate(OUTCOMES):
        path = base / split / outcome / "cases.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        raw_rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                note = rec.get("model_state", {}).get("clinical_note")
                meta = rec.get("metadata", {})
                if meta.get("tuning_split") != split:
                    raise RuntimeError(f"{path}: tuning_split metadata mismatch")
                if meta.get("outcome") != outcome:
                    raise RuntimeError(f"{path}: outcome metadata mismatch")
                if not isinstance(note, str) or not note.strip():
                    raise RuntimeError(f"{path}: blank note")
                raw_rows.append(
                    {
                        "case_id": str(rec.get("case_id")),
                        "label": int(meta["label"]),
                        "note": note,
                    }
                )
        raw_rows = stratified_limit(
            raw_rows,
            limit_per_outcome,
            seed + 1000 * outcome_i + (0 if split == "train" else 500),
        )
        for row in raw_rows:
            ids = tokenizer(row["note"], add_special_tokens=False)["input_ids"]
            chunks, truncated = chunk_ids(ids, chunk_tokens, chunk_overlap, max_chunks)
            examples.append(
                NoteExample(
                    case_id=row["case_id"],
                    outcome=outcome,
                    outcome_index=OUTCOME_TO_INDEX[outcome],
                    label=int(row["label"]),
                    chunks=chunks,
                    note_tokens=len(ids),
                    truncated=truncated,
                )
            )
    return examples


def assign_outcome_weights(rows: list[NoteExample]) -> dict[str, float]:
    counts = {o: sum(1 for r in rows if r.outcome == o) for o in OUTCOMES}
    total = sum(counts.values())
    weights = {o: total / (len(OUTCOMES) * counts[o]) for o in OUTCOMES}
    for r in rows:
        r.weight = weights[r.outcome]
    return weights


def make_collate(tokenizer):
    def collate(notes: list[NoteExample]) -> dict:
        flat_ids = []
        chunk_note_index = []
        for note_i, ex in enumerate(notes):
            for ids in ex.chunks:
                flat_ids.append(tokenizer.build_inputs_with_special_tokens(ids))
                chunk_note_index.append(note_i)
        padded = tokenizer.pad(
            {"input_ids": flat_ids},
            padding=True,
            return_tensors="pt",
        )
        return {
            "input_ids": padded["input_ids"],
            "attention_mask": padded["attention_mask"],
            "chunk_note_index": torch.tensor(chunk_note_index, dtype=torch.long),
            "outcome_index": torch.tensor([x.outcome_index for x in notes], dtype=torch.long),
            "labels": torch.tensor([x.label for x in notes], dtype=torch.float32),
            "weights": torch.tensor([x.weight for x in notes], dtype=torch.float32),
            "case_ids": [x.case_id for x in notes],
            "outcomes": [x.outcome for x in notes],
        }
    return collate


def aggregate_note_logits(
    chunk_logits: torch.Tensor,
    chunk_note_index: torch.Tensor,
    outcome_index: torch.Tensor,
    n_notes: int,
) -> torch.Tensor:
    note_logits = []
    for note_i in range(n_notes):
        mask = chunk_note_index == note_i
        task = int(outcome_index[note_i].item())
        note_logits.append(chunk_logits[mask, task].max())
    return torch.stack(note_logits)


@torch.no_grad()
def evaluate(model, loader, device) -> dict:
    model.eval()
    by_outcome = {
        o: {"y": [], "p": []}
        for o in OUTCOMES
    }
    for batch in loader:
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        attention_mask = batch["attention_mask"].to(device, non_blocking=True)
        chunk_note_index = batch["chunk_note_index"].to(device)
        outcome_index = batch["outcome_index"].to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            chunk_logits = model(input_ids, attention_mask)
            note_logits = aggregate_note_logits(
                chunk_logits,
                chunk_note_index,
                outcome_index,
                len(batch["case_ids"]),
            )
        probs = torch.sigmoid(note_logits).float().cpu().numpy()
        labels = batch["labels"].numpy().astype(int)
        for outcome, y, p in zip(batch["outcomes"], labels, probs):
            by_outcome[outcome]["y"].append(int(y))
            by_outcome[outcome]["p"].append(float(p))

    out = {}
    aucs = []
    aprs = []
    for outcome in OUTCOMES:
        y = np.asarray(by_outcome[outcome]["y"], dtype=int)
        p = np.asarray(by_outcome[outcome]["p"], dtype=float)
        if len(np.unique(y)) != 2:
            raise RuntimeError(f"Validation split for {outcome} lacks both classes.")
        auroc = float(roc_auc_score(y, p))
        auprc = float(average_precision_score(y, p))
        out[outcome] = {
            "n": int(len(y)),
            "cases": int(y.sum()),
            "controls": int((1 - y).sum()),
            "auroc": auroc,
            "auprc": auprc,
            "brier": float(brier_score_loss(y, p)),
        }
        aucs.append(auroc)
        aprs.append(auprc)
    out["mean_auroc"] = float(np.mean(aucs))
    out["mean_auprc"] = float(np.mean(aprs))
    return out


def summary(rows: list[NoteExample]) -> dict:
    out = {}
    for outcome in OUTCOMES:
        sub = [r for r in rows if r.outcome == outcome]
        out[outcome] = {
            "notes": len(sub),
            "cases": sum(r.label for r in sub),
            "controls": sum(1 - r.label for r in sub),
            "median_note_tokens": float(np.median([r.note_tokens for r in sub])) if sub else None,
            "max_note_tokens": int(max([r.note_tokens for r in sub], default=0)),
            "max_chunks": int(max([len(r.chunks) for r in sub], default=0)),
            "truncated_notes": int(sum(r.truncated for r in sub)),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Post-freeze supervised Open-Jev encoder multitask development.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--checkpoint-dir", required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--note-batch-size", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--learning-rate", type=float, default=2e-5)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--warmup-fraction", type=float, default=0.10)
    ap.add_argument("--chunk-tokens", type=int, default=384)
    ap.add_argument("--chunk-overlap", type=int, default=64)
    ap.add_argument("--max-chunks", type=int, default=5)
    ap.add_argument("--limit-notes-per-outcome", type=int, default=0)
    ap.add_argument("--max-train-batches", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for supervised encoder development.")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    base = Path(args.base).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    checkpoint_dir = Path(args.checkpoint_dir).expanduser().resolve()
    model_path = discover_checkpoint()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)

    train_rows = load_split(
        base,
        "train",
        tokenizer,
        chunk_tokens=args.chunk_tokens,
        chunk_overlap=args.chunk_overlap,
        max_chunks=args.max_chunks,
        limit_per_outcome=args.limit_notes_per_outcome,
        seed=args.seed,
    )
    val_rows = load_split(
        base,
        "validation",
        tokenizer,
        chunk_tokens=args.chunk_tokens,
        chunk_overlap=args.chunk_overlap,
        max_chunks=args.max_chunks,
        limit_per_outcome=args.limit_notes_per_outcome,
        seed=args.seed,
    )
    outcome_weights = assign_outcome_weights(train_rows)

    generator = torch.Generator()
    generator.manual_seed(args.seed)
    collate = make_collate(tokenizer)
    train_loader = DataLoader(
        NoteDataset(train_rows),
        batch_size=args.note_batch_size,
        shuffle=True,
        generator=generator,
        num_workers=0,
        collate_fn=collate,
        pin_memory=True,
    )
    val_loader = DataLoader(
        NoteDataset(val_rows),
        batch_size=args.note_batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=collate,
        pin_memory=True,
    )

    encoder = AutoModel.from_pretrained(str(model_path), local_files_only=True)
    hidden_size = int(encoder.config.hidden_size)
    model = MultiTaskDeberta(encoder, hidden_size, len(OUTCOMES))
    device = torch.device("cuda:0")
    model.to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    batches_per_epoch = len(train_loader)
    if args.max_train_batches > 0:
        batches_per_epoch = min(batches_per_epoch, args.max_train_batches)
    optimizer_steps_per_epoch = math.ceil(batches_per_epoch / args.grad_accum)
    total_optimizer_steps = max(1, args.epochs * optimizer_steps_per_epoch)
    warmup_steps = int(round(args.warmup_fraction * total_optimizer_steps))
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_optimizer_steps,
    )

    total_progress = args.epochs * batches_per_epoch
    global_batch = 0
    best = None
    history = []
    started = time.perf_counter()

    optimizer.zero_grad(set_to_none=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        seen_batches = 0
        for batch_i, batch in enumerate(train_loader, start=1):
            if args.max_train_batches > 0 and batch_i > args.max_train_batches:
                break
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            chunk_note_index = batch["chunk_note_index"].to(device)
            outcome_index = batch["outcome_index"].to(device)
            labels = batch["labels"].to(device)
            weights = batch["weights"].to(device)

            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                chunk_logits = model(input_ids, attention_mask)
                note_logits = aggregate_note_logits(
                    chunk_logits,
                    chunk_note_index,
                    outcome_index,
                    len(batch["case_ids"]),
                )
                per_note = F.binary_cross_entropy_with_logits(
                    note_logits,
                    labels,
                    reduction="none",
                )
                loss = (per_note * weights).mean() / args.grad_accum

            loss.backward()
            running_loss += float(loss.detach().cpu()) * args.grad_accum
            seen_batches += 1

            if batch_i % args.grad_accum == 0 or batch_i == batches_per_epoch:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)

            global_batch += 1
            if global_batch % 25 == 0 or global_batch == total_progress:
                update_progress(
                    current=global_batch,
                    total=total_progress,
                    phase="supervised_text_encoder_training",
                    message=f"Epoch {epoch}/{args.epochs}, batch {batch_i}/{batches_per_epoch}",
                    unit="batch",
                )

        validation = evaluate(model, val_loader, device)
        row = {
            "epoch": epoch,
            "train_loss_mean": running_loss / max(seen_batches, 1),
            "validation": validation,
        }
        history.append(row)

        key = (validation["mean_auroc"], validation["mean_auprc"])
        if best is None or key > best["selection_key"]:
            best = {
                "epoch": epoch,
                "selection_key": key,
                "validation": validation,
            }
            if not args.no_save:
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        "protocol": "docs/multitask_supervised_text_encoder_protocol_v1.md",
                        "base_checkpoint": "com-kotobalabs/open-jev-deberta-v3-large",
                        "epoch": epoch,
                        "outcomes": OUTCOMES,
                        "chunk_tokens": args.chunk_tokens,
                        "chunk_overlap": args.chunk_overlap,
                        "max_chunks": args.max_chunks,
                        "model_state_dict": model.state_dict(),
                    },
                    checkpoint_dir / "best_model.pt",
                )
                tokenizer.save_pretrained(checkpoint_dir / "tokenizer")

    elapsed = time.perf_counter() - started
    report = {
        "analysis": "Post-freeze supervised Open-Jev DeBERTa multitask upper-bound development v1",
        "protocol": "docs/multitask_supervised_text_encoder_protocol_v1.md",
        "cohorts": "docs/multitask_tuning_cohort_freeze_v1.md",
        "local_only": True,
        "network_enabled": False,
        "test_split_read": False,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "semantic_preservation_claimed": False,
        "scientific_role": "Outcome-supervised predictive upper bound/comparator, not a semantic-preserving JEV result.",
        "base_checkpoint": "com-kotobalabs/open-jev-deberta-v3-large",
        "architecture": "Shared DeBERTa-v2 encoder with three binary outcome heads; note-level multiple-instance max over chunk logits.",
        "training_config": {
            "epochs": args.epochs,
            "note_batch_size": args.note_batch_size,
            "gradient_accumulation": args.grad_accum,
            "effective_note_batch_size": args.note_batch_size * args.grad_accum,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "warmup_fraction": args.warmup_fraction,
            "chunk_tokens": args.chunk_tokens,
            "chunk_overlap": args.chunk_overlap,
            "max_chunks": args.max_chunks,
            "precision": "bfloat16 autocast",
            "gradient_checkpointing": false,
            "gradient_clip_norm": 1.0,
            "seed": args.seed,
            "outcome_weights": outcome_weights,
            "limit_notes_per_outcome": args.limit_notes_per_outcome,
            "max_train_batches": args.max_train_batches,
        },
        "train_summary": summary(train_rows),
        "validation_summary": summary(val_rows),
        "history": history,
        "best_epoch": int(best["epoch"]),
        "best_validation": best["validation"],
        "selection_rule": "Highest mean validation AUROC across three outcomes; mean validation AUPRC tie-breaker.",
        "checkpoint_saved_locally": bool(not args.no_save),
        "checkpoint_shared": False,
        "runtime_seconds": float(elapsed),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        report_path = None
        for i, arg in enumerate(sys.argv[:-1]):
            if arg == "--report":
                report_path = Path(sys.argv[i + 1]).expanduser().resolve()
                break
        failure = {
            "analysis": "Post-freeze supervised Open-Jev DeBERTa multitask development failure diagnostic",
            "local_only": True,
            "network_enabled": False,
            "test_split_read": False,
            "contains_note_text": False,
            "contains_source_patient_identifiers": False,
            "patient_level_predictions_shared": False,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:2000],
        }
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure, indent=2))
        raise
