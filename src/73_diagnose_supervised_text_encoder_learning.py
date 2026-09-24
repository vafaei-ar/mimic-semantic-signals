from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from torch.nn import functional as F
from torch.utils.data import DataLoader

from runrelay_progress import update_progress


def load_training_module():
    path = Path(__file__).with_name("71_train_supervised_text_encoder.py")
    spec = importlib.util.spec_from_file_location("supervised_text_encoder_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load supervised encoder module.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_notes(base: Path, split: str, outcome: str) -> tuple[list[str], np.ndarray]:
    if split == "test":
        raise RuntimeError("Diagnostic code is forbidden from reading the locked test split.")
    path = base / split / outcome / "cases.jsonl"
    texts = []
    labels = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            meta = rec.get("metadata", {})
            if meta.get("tuning_split") != split or meta.get("outcome") != outcome:
                raise RuntimeError(f"{path}: metadata mismatch")
            note = rec.get("model_state", {}).get("clinical_note")
            if not isinstance(note, str) or not note.strip():
                raise RuntimeError(f"{path}: blank note")
            texts.append(note)
            labels.append(int(meta["label"]))
    return texts, np.asarray(labels, dtype=int)


def tfidf_probe(base: Path, outcomes: list[str]) -> dict:
    out = {}
    for outcome in outcomes:
        x_train, y_train = read_notes(base, "train", outcome)
        x_val, y_val = read_notes(base, "validation", outcome)
        vec = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            min_df=5,
            max_df=0.98,
            max_features=10000,
            sublinear_tf=True,
            dtype=np.float64,
        )
        a = vec.fit_transform(x_train)
        b = vec.transform(x_val)
        clf = LogisticRegression(max_iter=3000, solver="liblinear", C=1.0)
        clf.fit(a, y_train)
        p = clf.predict_proba(b)[:, 1]
        out[outcome] = {
            "train_n": int(len(y_train)),
            "validation_n": int(len(y_val)),
            "vocabulary_size": int(len(vec.vocabulary_)),
            "validation_auroc": float(roc_auc_score(y_val, p)),
            "validation_auprc": float(average_precision_score(y_val, p)),
        }
    return out


@torch.no_grad()
def evaluate_detail(mod, model, loader, device) -> dict:
    model.eval()
    by = {o: {"y": [], "p": []} for o in mod.OUTCOMES}
    for batch in loader:
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        attention_mask = batch["attention_mask"].to(device, non_blocking=True)
        chunk_note_index = batch["chunk_note_index"].to(device)
        outcome_index = batch["outcome_index"].to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            chunk_logits = model(input_ids, attention_mask)
            note_logits = mod.aggregate_note_logits(
                chunk_logits, chunk_note_index, outcome_index, len(batch["case_ids"])
            )
        probs = torch.sigmoid(note_logits).float().cpu().numpy()
        ys = batch["labels"].numpy().astype(int)
        for outcome, y, p in zip(batch["outcomes"], ys, probs):
            by[outcome]["y"].append(int(y))
            by[outcome]["p"].append(float(p))
    out = {}
    for outcome in mod.OUTCOMES:
        y = np.asarray(by[outcome]["y"], dtype=int)
        p = np.asarray(by[outcome]["p"], dtype=float)
        out[outcome] = {
            "n": int(len(y)),
            "cases": int(y.sum()),
            "controls": int((1-y).sum()),
            "auroc": float(roc_auc_score(y, p)),
            "auprc": float(average_precision_score(y, p)),
            "probability_mean": float(p.mean()),
            "probability_sd": float(p.std(ddof=1)) if len(p) > 1 else 0.0,
            "case_probability_mean": float(p[y == 1].mean()),
            "control_probability_mean": float(p[y == 0].mean()),
        }
    out["mean_auroc"] = float(np.mean([out[o]["auroc"] for o in mod.OUTCOMES]))
    return out


def encoder_delta(model, checkpoint_state: dict[str, torch.Tensor]) -> dict:
    current = model.state_dict()
    diff_sq = 0.0
    base_sq = 0.0
    abs_sum = 0.0
    count = 0
    changed_tensors = 0
    total_tensors = 0
    for name, tuned in checkpoint_state.items():
        if not name.startswith("encoder.") or not torch.is_floating_point(tuned):
            continue
        if name not in current:
            continue
        base = current[name].detach().cpu().float()
        tuned_f = tuned.detach().cpu().float()
        delta = tuned_f - base
        total_tensors += 1
        if torch.any(delta != 0):
            changed_tensors += 1
        diff_sq += float(torch.sum(delta * delta))
        base_sq += float(torch.sum(base * base))
        abs_sum += float(torch.sum(torch.abs(delta)))
        count += int(delta.numel())
    return {
        "encoder_float_tensors_compared": total_tensors,
        "encoder_float_tensors_changed": changed_tensors,
        "encoder_parameter_elements": count,
        "encoder_relative_l2_delta": float((diff_sq / max(base_sq, 1e-30)) ** 0.5),
        "encoder_mean_absolute_delta": float(abs_sum / max(count, 1)),
    }


def tiny_overfit_probe(mod, model_path: Path, tokenizer, base: Path, device, seed: int) -> dict:
    from transformers import AutoModel

    rows = mod.load_split(
        base,
        "train",
        tokenizer,
        chunk_tokens=384,
        chunk_overlap=64,
        max_chunks=5,
        limit_per_outcome=24,
        seed=seed + 77,
    )
    mod.assign_outcome_weights(rows)
    collate = mod.make_collate(tokenizer)
    generator = torch.Generator()
    generator.manual_seed(seed + 99)
    loader = DataLoader(
        mod.NoteDataset(rows),
        batch_size=2,
        shuffle=True,
        generator=generator,
        num_workers=0,
        collate_fn=collate,
        pin_memory=True,
    )
    eval_loader = DataLoader(
        mod.NoteDataset(rows),
        batch_size=2,
        shuffle=False,
        num_workers=0,
        collate_fn=collate,
        pin_memory=True,
    )

    encoder = AutoModel.from_pretrained(str(model_path), local_files_only=True)
    model = mod.MultiTaskDeberta(encoder, int(encoder.config.hidden_size), len(mod.OUTCOMES)).to(device)
    before = evaluate_detail(mod, model, eval_loader, device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.0)
    losses = []
    total_epochs = 10
    for epoch in range(1, total_epochs + 1):
        model.train()
        epoch_losses = []
        for batch in loader:
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            chunk_note_index = batch["chunk_note_index"].to(device)
            outcome_index = batch["outcome_index"].to(device)
            labels = batch["labels"].to(device)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                chunk_logits = model(input_ids, attention_mask)
                note_logits = mod.aggregate_note_logits(
                    chunk_logits, chunk_note_index, outcome_index, len(batch["case_ids"])
                )
                loss = F.binary_cross_entropy_with_logits(note_logits, labels)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))
        losses.append(float(np.mean(epoch_losses)))
        update_progress(
            current=epoch,
            total=total_epochs,
            phase="encoder_learning_diagnostic",
            message=f"Tiny train-only overfit probe epoch {epoch}/{total_epochs}",
            unit="epoch",
        )

    after = evaluate_detail(mod, model, eval_loader, device)
    return {
        "notes_per_outcome": 24,
        "epochs": total_epochs,
        "learning_rate": 1e-4,
        "weight_decay": 0.0,
        "loss_by_epoch": losses,
        "before": before,
        "after": after,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnose failed supervised text-encoder learning without reading test data.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--seed", type=int, default=20260924)
    args = ap.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required.")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    from transformers import AutoModel, AutoTokenizer

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    mod = load_training_module()
    base = Path(args.base).expanduser().resolve()
    ckpt_path = Path(args.checkpoint).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    if not ckpt_path.exists():
        raise FileNotFoundError(ckpt_path)

    started = time.perf_counter()
    model_path = mod.discover_checkpoint()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)

    update_progress(current=0, total=10, phase="encoder_learning_diagnostic", message="Running TF-IDF cohort-signal probe", unit="epoch")
    lexical = tfidf_probe(base, mod.OUTCOMES)

    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    checkpoint_state = checkpoint["model_state_dict"]
    encoder = AutoModel.from_pretrained(str(model_path), local_files_only=True)
    tuned_model = mod.MultiTaskDeberta(encoder, int(encoder.config.hidden_size), len(mod.OUTCOMES))
    delta = encoder_delta(tuned_model, checkpoint_state)
    tuned_model.load_state_dict(checkpoint_state)
    device = torch.device("cuda:0")
    tuned_model.to(device)

    train_rows = mod.load_split(
        base,
        "train",
        tokenizer,
        chunk_tokens=384,
        chunk_overlap=64,
        max_chunks=5,
        limit_per_outcome=400,
        seed=args.seed + 11,
    )
    val_rows = mod.load_split(
        base,
        "validation",
        tokenizer,
        chunk_tokens=384,
        chunk_overlap=64,
        max_chunks=5,
        limit_per_outcome=0,
        seed=args.seed,
    )
    collate = mod.make_collate(tokenizer)
    train_loader = DataLoader(mod.NoteDataset(train_rows), batch_size=2, shuffle=False, num_workers=0, collate_fn=collate, pin_memory=True)
    val_loader = DataLoader(mod.NoteDataset(val_rows), batch_size=2, shuffle=False, num_workers=0, collate_fn=collate, pin_memory=True)

    selected_checkpoint_fit = {
        "checkpoint_epoch": int(checkpoint.get("epoch", -1)),
        "encoder_delta_from_base": delta,
        "train_sample": evaluate_detail(mod, tuned_model, train_loader, device),
        "validation": evaluate_detail(mod, tuned_model, val_loader, device),
    }

    del tuned_model
    del encoder
    torch.cuda.empty_cache()

    overfit = tiny_overfit_probe(mod, model_path, tokenizer, base, device, args.seed)

    report = {
        "analysis": "Post-freeze supervised encoder learning-failure diagnostic v1",
        "development_job": "M7K3V8R2",
        "development_artifact_sha256": "5f8e2c798f9b509402ab6c2cafe66e831e87eb5d121f3917ad7245a5725bb4b4",
        "local_only": True,
        "network_enabled": False,
        "test_split_read": False,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "purpose": "Determine whether chance validation reflects a cohort-signal problem, failure of the selected checkpoint to learn, or inability of the implementation to overfit a tiny train-only subset.",
        "tfidf_train_to_validation_probe": lexical,
        "selected_checkpoint_fit": selected_checkpoint_fit,
        "tiny_train_only_overfit_probe": overfit,
        "runtime_seconds": float(time.perf_counter() - started),
        "guardrail": "This diagnostic does not alter the locked test set and is not a tuned-model performance claim.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
