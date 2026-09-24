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
from sklearn.metrics import average_precision_score, roc_auc_score
from torch import nn
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


class ProbeModel(nn.Module):
    def __init__(self, encoder: nn.Module, hidden_size: int, tasks: int, pooling: str):
        super().__init__()
        self.encoder = encoder
        self.pooling = pooling
        self.head = nn.Linear(hidden_size, tasks)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        hidden = out.last_hidden_state
        if self.pooling == "cls":
            pooled = hidden[:, 0]
        elif self.pooling == "mean":
            mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        else:
            raise ValueError(self.pooling)
        return self.head(pooled)


def aggregate(chunk_logits, chunk_note_index, outcome_index, n_notes):
    vals = []
    for note_i in range(n_notes):
        mask = chunk_note_index == note_i
        task = int(outcome_index[note_i].item())
        vals.append(chunk_logits[mask, task].max())
    return torch.stack(vals)


@torch.no_grad()
def evaluate(mod, model, loader, device):
    model.eval()
    by = {o: {"y": [], "p": []} for o in mod.OUTCOMES}
    for batch in loader:
        ids = batch["input_ids"].to(device)
        mask = batch["attention_mask"].to(device)
        cni = batch["chunk_note_index"].to(device)
        oi = batch["outcome_index"].to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            chunk_logits = model(ids, mask)
            logits = aggregate(chunk_logits, cni, oi, len(batch["case_ids"]))
        probs = torch.sigmoid(logits).float().cpu().numpy()
        ys = batch["labels"].numpy().astype(int)
        for outcome, y, p in zip(batch["outcomes"], ys, probs):
            by[outcome]["y"].append(int(y))
            by[outcome]["p"].append(float(p))
    out = {}
    for outcome in mod.OUTCOMES:
        y = np.asarray(by[outcome]["y"], dtype=int)
        p = np.asarray(by[outcome]["p"], dtype=float)
        out[outcome] = {
            "auroc": float(roc_auc_score(y, p)),
            "auprc": float(average_precision_score(y, p)),
            "probability_mean": float(p.mean()),
            "probability_sd": float(p.std(ddof=1)) if len(p) > 1 else 0.0,
            "case_probability_mean": float(p[y == 1].mean()),
            "control_probability_mean": float(p[y == 0].mean()),
        }
    out["mean_auroc"] = float(np.mean([out[o]["auroc"] for o in mod.OUTCOMES]))
    return out


def train_variant(
    *,
    mod,
    model_path: Path,
    rows,
    tokenizer,
    device,
    pooling: str,
    freeze_encoder: bool,
    encoder_lr: float,
    head_lr: float,
    epochs: int,
    variant_index: int,
    total_variants: int,
    seed: int,
):
    from transformers import AutoModel

    torch.manual_seed(seed + variant_index)
    torch.cuda.manual_seed_all(seed + variant_index)
    encoder = AutoModel.from_pretrained(str(model_path), local_files_only=True)
    model = ProbeModel(encoder, int(encoder.config.hidden_size), len(mod.OUTCOMES), pooling).to(device)

    if freeze_encoder:
        for p in model.encoder.parameters():
            p.requires_grad = False
        params = [{"params": model.head.parameters(), "lr": head_lr}]
    else:
        params = [
            {"params": model.encoder.parameters(), "lr": encoder_lr},
            {"params": model.head.parameters(), "lr": head_lr},
        ]

    optimizer = torch.optim.AdamW(params, weight_decay=0.01 if not freeze_encoder else 0.0)
    collate = mod.make_collate(tokenizer)
    generator = torch.Generator()
    generator.manual_seed(seed + 100 + variant_index)
    train_loader = DataLoader(
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

    before = evaluate(mod, model, eval_loader, device)
    pos_weight = torch.tensor(3.0, device=device)
    losses = []
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_losses = []
        for batch in train_loader:
            ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            cni = batch["chunk_note_index"].to(device)
            oi = batch["outcome_index"].to(device)
            labels = batch["labels"].to(device)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                chunk_logits = model(ids, mask)
                logits = aggregate(chunk_logits, cni, oi, len(batch["case_ids"]))
                loss = F.binary_cross_entropy_with_logits(
                    logits, labels, pos_weight=pos_weight
                )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))
        losses.append(float(np.mean(epoch_losses)))
        completed = variant_index * epochs + epoch
        update_progress(
            current=completed,
            total=total_variants * epochs,
            phase="encoder_recipe_probe",
            message=f"Variant {variant_index + 1}/{total_variants}, epoch {epoch}/{epochs}",
            unit="variant_epoch",
        )

    after = evaluate(mod, model, eval_loader, device)
    result = {
        "pooling": pooling,
        "freeze_encoder": freeze_encoder,
        "encoder_learning_rate": encoder_lr if not freeze_encoder else 0.0,
        "head_learning_rate": head_lr,
        "positive_class_weight": 3.0,
        "epochs": epochs,
        "loss_first": losses[0],
        "loss_last": losses[-1],
        "loss_min": float(min(losses)),
        "before": before,
        "after": after,
    }
    del model
    del encoder
    torch.cuda.empty_cache()
    return result


def main():
    ap = argparse.ArgumentParser(description="Train-only recipe probe for supervised encoder collapse.")
    ap.add_argument("--base", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--seed", type=int, default=20260924)
    args = ap.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required.")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    from transformers import AutoTokenizer

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    mod = load_training_module()
    base = Path(args.base).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    model_path = mod.discover_checkpoint()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)

    rows = mod.load_split(
        base,
        "train",
        tokenizer,
        chunk_tokens=384,
        chunk_overlap=64,
        max_chunks=5,
        limit_per_outcome=24,
        seed=args.seed + 313,
    )
    counts = {
        o: {
            "n": sum(1 for r in rows if r.outcome == o),
            "cases": sum(r.label for r in rows if r.outcome == o),
        }
        for o in mod.OUTCOMES
    }

    variants = [
        {"name": "frozen_cls_posweight", "pooling": "cls", "freeze_encoder": True, "encoder_lr": 0.0, "head_lr": 1e-3},
        {"name": "frozen_mean_posweight", "pooling": "mean", "freeze_encoder": True, "encoder_lr": 0.0, "head_lr": 1e-3},
        {"name": "full_cls_differential_posweight", "pooling": "cls", "freeze_encoder": False, "encoder_lr": 5e-6, "head_lr": 1e-4},
        {"name": "full_mean_differential_posweight", "pooling": "mean", "freeze_encoder": False, "encoder_lr": 5e-6, "head_lr": 1e-4},
    ]
    epochs = 15
    device = torch.device("cuda:0")
    results = {}
    started = time.perf_counter()
    for i, spec in enumerate(variants):
        results[spec["name"]] = train_variant(
            mod=mod,
            model_path=model_path,
            rows=rows,
            tokenizer=tokenizer,
            device=device,
            pooling=spec["pooling"],
            freeze_encoder=spec["freeze_encoder"],
            encoder_lr=spec["encoder_lr"],
            head_lr=spec["head_lr"],
            epochs=epochs,
            variant_index=i,
            total_variants=len(variants),
            seed=args.seed,
        )

    report = {
        "analysis": "Train-only supervised encoder recipe probe v1",
        "parent_diagnostic_job": "P7K4M9R2",
        "local_only": True,
        "network_enabled": False,
        "validation_split_read": False,
        "test_split_read": False,
        "contains_note_text": False,
        "contains_source_patient_identifiers": False,
        "patient_level_predictions_shared": False,
        "subset": {
            "selection": "Deterministic 24-note sample per outcome from train only",
            "counts": counts,
            "case_control_ratio": "1:3",
        },
        "fixed_probe_choices": {
            "positive_class_weight": 3.0,
            "epochs": epochs,
            "batch_size": 2,
            "chunk_tokens": 384,
            "chunk_overlap": 64,
            "max_chunks": 5,
            "purpose": "Mechanistic capacity/optimization probe only; not validation-based model selection.",
        },
        "variants": results,
        "runtime_seconds": float(time.perf_counter() - started),
        "guardrail": "No validation or test files are opened. Results may justify a separately frozen v2 development recipe but are not performance claims.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
