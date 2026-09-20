from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="com-kotobalabs/open-jev-deberta-v3-large")
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--device", default=None)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()

    from typed_decisions.metrics import summarize
    from typed_decisions.open_jev import OpenJev
    from typed_decisions.schema import read_jsonl
    from typed_decisions.encoder import predict

    loaded = OpenJev.from_pretrained(args.model, device=args.device)
    data = Path(args.data).expanduser().resolve()
    test = read_jsonl(data / "test.jsonl")
    ood = read_jsonl(data / "ood-test.jsonl")

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

    report = {
        "model": args.model,
        "device": str(loaded.device),
        "test_states": len(test),
        "ood_states": len(ood),
        "temperature": float(loaded.model.temperature),
        "metrics_test": summarize(test_rec),
        "metrics_ood": summarize(ood_rec),
    }
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2)[:6000])


if __name__ == "__main__":
    main()
