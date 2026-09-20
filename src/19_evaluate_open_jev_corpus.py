from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch



def summarize_by_qid(records: list[dict]) -> dict:
    from typed_decisions.metrics import summarize

    out = {}
    qids = sorted({r["qid"] for r in records})
    for qid in qids:
        subset = [r for r in records if r["qid"] == qid]
        out[qid] = summarize(subset).get("all", {})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="com-kotobalabs/open-jev-deberta-v3-large")
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--device", default=None)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()

    from typed_decisions.metrics import summarize
    from open_jev_loader import load_open_jev_corrected
    from typed_decisions.schema import read_jsonl
    from typed_decisions.encoder import predict

    loaded = load_open_jev_corrected(args.model, device=args.device)
    data = Path(args.data).expanduser().resolve()
    test = read_jsonl(data / "test.jsonl")
    ood = read_jsonl(data / "ood-test.jsonl")
    negation = read_jsonl(data / "negation-test.jsonl") if (data / "negation-test.jsonl").exists() else []

    with torch.no_grad():
        test_rec = predict(
            loaded.model,
            loaded.collator,
            test,
            args.batch,
            loaded.device,
            temperature=loaded.model.temperature,
        )
        ood_rec = predict(
            loaded.model,
            loaded.collator,
            ood,
            args.batch,
            loaded.device,
            temperature=loaded.model.temperature,
        )
        negation_rec = (
            predict(
                loaded.model,
                loaded.collator,
                negation,
                args.batch,
                loaded.device,
                temperature=loaded.model.temperature,
            )
            if negation else []
        )

    report = {
        "model": args.model,
        "device": str(loaded.device),
        "test_states": len(test),
        "ood_states": len(ood),
        "negation_states": len(negation),
        "temperature": float(loaded.model.temperature),
        "metrics_test": summarize(test_rec),
        "metrics_ood": summarize(ood_rec),
        "metrics_negation": summarize(negation_rec) if negation_rec else None,
        "per_construct_test": summarize_by_qid(test_rec),
        "per_construct_ood": summarize_by_qid(ood_rec),
        "per_construct_negation": summarize_by_qid(negation_rec) if negation_rec else None,
    }
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2)[:6000])


if __name__ == "__main__":
    main()
