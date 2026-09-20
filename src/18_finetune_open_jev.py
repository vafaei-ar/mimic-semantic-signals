from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

import torch


def device_from_arg(arg: str) -> torch.device:
    if arg != "auto":
        return torch.device(arg)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Continue training the released Open-Jev checkpoint on a typed-decision corpus."
    )
    ap.add_argument("--base", default="com-kotobalabs/open-jev-deberta-v3-large")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--head-lr", type=float, default=1e-4)
    ap.add_argument("--warmup", type=float, default=0.06)
    ap.add_argument("--brier-weight", type=float, default=1.0)
    ap.add_argument("--augment", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--eval-batch", type=int, default=16)
    args = ap.parse_args()

    from safetensors.torch import save_file
    from typed_decisions.augment import augment
    from typed_decisions.encoder import decision_loss, predict
    from typed_decisions.metrics import fit_temperature, summarize
    from open_jev_loader import load_open_jev_corrected
    from typed_decisions.schema import read_jsonl

    torch.manual_seed(args.seed)
    random.seed(args.seed)

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    data = Path(args.data).expanduser().resolve()

    loaded = load_open_jev_corrected(args.base, device=str(device_from_arg(args.device)))
    model = loaded.model
    coll = loaded.collator
    tok = loaded.tok
    dev = loaded.device

    train = read_jsonl(data / "train.jsonl")
    val = read_jsonl(data / "val.jsonl")
    test = read_jsonl(data / "test.jsonl")
    ood = read_jsonl(data / "ood-test.jsonl") if (data / "ood-test.jsonl").exists() else []
    negation = read_jsonl(data / "negation-test.jsonl") if (data / "negation-test.jsonl").exists() else []

    model.train()
    head_params = list(model.head.parameters())
    head_ids = {id(p) for p in head_params}
    opt = torch.optim.AdamW(
        [
            {
                "params": [p for p in model.parameters() if id(p) not in head_ids],
                "lr": args.lr,
            },
            {"params": head_params, "lr": args.head_lr},
        ],
        weight_decay=0.01,
    )

    steps_per_epoch = math.ceil(len(train) / args.batch)
    total_steps = max(1, int(steps_per_epoch * args.epochs))
    warm = max(1, int(total_steps * args.warmup))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt,
        lambda s: (
            (s + 1) / warm
            if s < warm
            else max(0.0, (total_steps - s) / max(1, total_steps - warm))
        ),
    )

    use_amp = dev.type == "cuda"
    order = list(range(len(train)))
    step = 0
    losses = []
    t0 = time.time()

    while step < total_steps:
        random.shuffle(order)
        for i in range(0, len(order), args.batch):
            if step >= total_steps:
                break
            chunk = [train[j] for j in order[i:i + args.batch]]
            items = []
            for e in chunk:
                qs = [
                    augment(q, random)
                    if args.augment and random.random() < args.augment
                    else q
                    for q in e.questions
                ]
                items.append((e.state, qs))
            batch = coll(items, dev)

            with torch.autocast(
                device_type="cuda",
                dtype=torch.bfloat16,
                enabled=use_amp,
            ):
                logits = model(
                    batch["input_ids"],
                    batch["attention_mask"],
                    batch["opt_pos"],
                    batch["opt_mask"],
                    batch["q_pos"],
                    batch["seg"],
                )
            loss, info = decision_loss(
                logits.float(),
                batch["gold"],
                args.brier_weight,
            )
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()

            losses.append(float(loss.detach()))
            if step % 20 == 0:
                print(
                    f"step {step}/{total_steps} loss={loss.item():.4f} "
                    f"ce={info['ce']:.4f} brier={info['brier']:.4f}",
                    flush=True,
                )
            step += 1

    train_seconds = time.time() - t0

    model.eval()
    with torch.no_grad():
        val_raw = predict(model, coll, val, args.eval_batch, dev, temperature=1.0)
    T = fit_temperature(
        [r["logits"] for r in val_raw],
        [r["gold"] for r in val_raw],
    )
    model.temperature = T

    with torch.no_grad():
        test_rec = predict(model, coll, test, args.eval_batch, dev, temperature=T)
        ood_rec = (
            predict(model, coll, ood, args.eval_batch, dev, temperature=T)
            if ood else []
        )
        negation_rec = (
            predict(model, coll, negation, args.eval_batch, dev, temperature=T)
            if negation else []
        )

    report = {
        "base": args.base,
        "device": str(dev),
        "args": vars(args),
        "train_states": len(train),
        "val_states": len(val),
        "test_states": len(test),
        "ood_states": len(ood),
        "negation_states": len(negation),
        "train_seconds": train_seconds,
        "loss_first": losses[0] if losses else None,
        "loss_last10_mean": (
            sum(losses[-10:]) / len(losses[-10:])
            if losses else None
        ),
        "temperature": float(T),
        "metrics_test": summarize(test_rec),
        "metrics_ood": summarize(ood_rec) if ood_rec else None,
        "metrics_negation": summarize(negation_rec) if negation_rec else None,
        "per_construct_test": {qid: summarize([r for r in test_rec if r["qid"] == qid]).get("all", {}) for qid in sorted({r["qid"] for r in test_rec})},
        "per_construct_ood": {qid: summarize([r for r in ood_rec if r["qid"] == qid]).get("all", {}) for qid in sorted({r["qid"] for r in ood_rec})} if ood_rec else None,
        "per_construct_negation": {qid: summarize([r for r in negation_rec if r["qid"] == qid]).get("all", {}) for qid in sorted({r["qid"] for r in negation_rec})} if negation_rec else None,
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    bundle = out / "bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    model.backbone.save_pretrained(bundle, safe_serialization=True)
    tok.save_pretrained(bundle)
    save_file(
        {
            k: v.detach().cpu().contiguous()
            for k, v in model.head.state_dict().items()
        },
        bundle / "head.safetensors",
    )

    cfg = dict(loaded.config)
    cfg["temperature"] = float(T)
    cfg["base_model"] = args.base
    cfg["clinical_tuning"] = {
        "synthetic_only": True,
        "train_states": len(train),
        "val_states": len(val),
        "test_states": len(test),
        "epochs": args.epochs,
        "lr": args.lr,
        "head_lr": args.head_lr,
        "augment": args.augment,
        "seed": args.seed,
        "metrics_test": report["metrics_test"].get("all"),
        "metrics_ood": (
            report["metrics_ood"].get("all")
            if report["metrics_ood"] else None
        ),
        "metrics_negation": (
            report["metrics_negation"].get("all")
            if report["metrics_negation"] else None
        ),
    }
    (bundle / "open_jev_config.json").write_text(
        json.dumps(cfg, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2)[:6000])


if __name__ == "__main__":
    main()
