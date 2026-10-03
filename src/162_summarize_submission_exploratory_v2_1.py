from __future__ import annotations

import argparse
import json
from pathlib import Path

from runrelay_progress import update_progress


METRIC_KEYS = ("auroc", "auprc", "brier", "log_loss")


def pick_metrics(d: dict) -> dict:
    return {k: float(d[k]) for k in METRIC_KEYS if k in d}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    src = Path(args.input).expanduser().resolve()
    obj = json.loads(src.read_text(encoding="utf-8"))
    if obj.get("status") != "completed":
        raise RuntimeError("Source exploratory artifact is not completed")

    out = {
        "analysis": "Micro-summary of post-registration Paper 1 explanatory analyses",
        "status": "completed",
        "source_artifact": str(Path(args.input)),
        "uncertainty": obj.get("uncertainty"),
        "semantic_only_population": obj.get("semantic_only_population"),
        "results": {},
    }

    for key, rec in (obj.get("results") or {}).items():
        sem = rec["semantic_only_note_available"]
        sem_primary = sem["primary_repeat"]
        dest = {
            "outcome": rec["outcome"],
            "source": rec["source"],
            "n": int(rec["n"]),
            "cases": int(rec["cases"]),
            "note_available_rows": int(rec["note_available_rows"]),
            "frozen_split_sha256": rec.get("frozen_split_sha256"),
            "semantic_only": {
                "primary_n": int(sem_primary["n"]),
                "primary_cases": int(sem_primary["cases"]),
                "primary_controls": int(sem_primary["controls"]),
                "primary_metrics": pick_metrics(sem_primary),
                "auroc_range": [float(x) for x in sem["auroc_range"]],
                "repeat_auroc": [float(x["auroc"]) for x in sem["repeats"]],
                "repeat_auprc": [float(x["auprc"]) for x in sem["repeats"]],
            },
            "comparator_decomposition": {},
        }

        for level, lr in rec["comparator_decomposition"].items():
            pr = lr["primary_repeat"]
            dest["comparator_decomposition"][level] = {
                "feature_count": int(lr["feature_count"]),
                "primary_comparator": pick_metrics(pr["comparator"]),
                "primary_plus_openjev": pick_metrics(pr["comparator_plus_openjev"]),
                "primary_delta": pick_metrics(pr["delta"]),
                "delta_auroc_range": [float(x) for x in lr["delta_auroc_range"]],
                "repeat_delta_auroc": [float(x["delta"]["auroc"]) for x in lr["repeats"]],
                "repeat_delta_auprc": [float(x["delta"]["auprc"]) for x in lr["repeats"]],
            }

        out["results"][key] = dest

    target = Path(args.output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")

    labels = {
        "ventilation": "vent",
        "rrt": "rrt",
        "death_metavision": "death",
    }
    parts = []
    for key in ("ventilation", "rrt", "death_metavision"):
        rec = out["results"][key]
        sem = rec["semantic_only"]
        sem_auc = sem["primary_metrics"]["auroc"]
        sem_rng = sem["auroc_range"]
        lv = rec["comparator_decomposition"]
        level_parts = []
        for level in (
            "A_structured_34",
            "B_plus_treatment_support",
            "C_plus_documentation_behavior",
            "D_registered_rich_comparator",
        ):
            x = lv[level]
            b = x["primary_comparator"]["auroc"]
            a = x["primary_plus_openjev"]["auroc"]
            d = x["primary_delta"]["auroc"]
            rr = x["delta_auroc_range"]
            level_parts.append(
                f"{level[0]}:{b:.5f}>{a:.5f} d{d:+.5f}[{rr[0]:+.5f},{rr[1]:+.5f}]"
            )
        parts.append(
            f"{labels[key]} sem={sem_auc:.5f}[{sem_rng[0]:.5f},{sem_rng[1]:.5f}] "
            + " ".join(level_parts)
        )
    update_progress(
        current=1,
        total=1,
        phase="submission_metric_extract",
        message=" | ".join(parts),
        unit="summary",
    )
    print(json.dumps({"status": "completed", "output": str(target)}))


if __name__ == "__main__":
    main()
