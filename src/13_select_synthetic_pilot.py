from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def time_bin(hours: float) -> str:
    if hours <= 6:
        return "0_6h"
    if hours <= 12:
        return "6_12h"
    return "12_24h"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20260919)
    args = ap.parse_args()

    src = Path(args.cases).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cases = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("synthetic_only") is not True:
                raise RuntimeError("Pilot selector only accepts synthetic_only=true cases.")
            h = float(rec["metadata"]["hours_before_event"])
            rec["_stratum"] = (
                str(rec.get("gold", {}).get("event_type")),
                int(rec.get("gold", {}).get("discordant", 0)),
                time_bin(h),
                str(rec["metadata"].get("note_category")),
            )
            cases.append(rec)

    rng = random.Random(args.seed)
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for rec in cases:
        strata[rec["_stratum"]].append(rec)

    for values in strata.values():
        rng.shuffle(values)

    keys = sorted(strata)
    rng.shuffle(keys)

    selected = []
    while len(selected) < min(args.n, len(cases)):
        progressed = False
        for key in keys:
            if strata[key]:
                rec = strata[key].pop()
                rec.pop("_stratum", None)
                selected.append(rec)
                progressed = True
                if len(selected) >= min(args.n, len(cases)):
                    break
        if not progressed:
            break

    with out.open("w", encoding="utf-8") as f:
        for rec in selected:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = defaultdict(int)
    for rec in selected:
        event = str(rec.get("gold", {}).get("event_type"))
        discordant = int(rec.get("gold", {}).get("discordant", 0))
        tb = time_bin(float(rec["metadata"]["hours_before_event"]))
        note_category = str(rec["metadata"].get("note_category"))
        summary[f"event::{event}"] += 1
        summary[f"discordant::{discordant}"] += 1
        summary[f"time::{tb}"] += 1
        summary[f"note::{note_category}"] += 1

    summary_obj = {
        "selected_n": len(selected),
        "source_n": len(cases),
        "seed": args.seed,
        "distribution": dict(sorted(summary.items())),
    }
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary_obj, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary_obj, indent=2))


if __name__ == "__main__":
    main()
