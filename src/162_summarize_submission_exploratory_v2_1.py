from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract compact manuscript-facing summaries from the safe Paper 1 exploratory aggregate artifact."
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    src = Path(args.input).expanduser().resolve()
    obj = json.loads(src.read_text(encoding="utf-8"))

    if obj.get("status") != "completed":
        raise RuntimeError("Source exploratory artifact is not completed")

    out = {
        "analysis": "Compact summary of post-registration Paper 1 exploratory explanatory analyses",
        "source_analysis": obj.get("analysis"),
        "source_artifact": str(Path(args.input)),
        "status": "completed",
        "uncertainty": obj.get("uncertainty"),
        "semantic_only_population": obj.get("semantic_only_population"),
        "results": {},
    }

    for key, rec in (obj.get("results") or {}).items():
        sem = rec["semantic_only_note_available"]
        dest = {
            "outcome": rec["outcome"],
            "source": rec["source"],
            "n": rec["n"],
            "cases": rec["cases"],
            "note_available_rows": rec["note_available_rows"],
            "frozen_split_sha256": rec.get("frozen_split_sha256"),
            "semantic_only": {
                "primary_repeat": sem["primary_repeat"],
                "auroc_range": sem["auroc_range"],
                "repeat_auroc": [float(x["auroc"]) for x in sem["repeats"]],
                "repeat_auprc": [float(x["auprc"]) for x in sem["repeats"]],
            },
            "comparator_decomposition": {},
        }
        for level, lr in rec["comparator_decomposition"].items():
            dest["comparator_decomposition"][level] = {
                "feature_count": lr["feature_count"],
                "primary_repeat": lr["primary_repeat"],
                "delta_auroc_range": lr["delta_auroc_range"],
                "repeat_delta_auroc": [float(x["delta"]["auroc"]) for x in lr["repeats"]],
                "repeat_delta_auprc": [float(x["delta"]["auprc"]) for x in lr["repeats"]],
            }
        out["results"][key] = dest

    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(target)}))


if __name__ == "__main__":
    main()
