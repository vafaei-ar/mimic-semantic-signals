from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from semantic_schema import SEMANTIC_CONSTRUCTS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--window-hours", type=float, default=24.0)
    args = ap.parse_args()

    root = Path(args.synthetic_root).expanduser().resolve()
    mimic = root / "mimiciii" / "1.4"
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    notes = pd.read_csv(mimic / "NOTEEVENTS.csv.gz", compression="gzip", low_memory=False)
    truth = pd.read_csv(root / "synthetic_truth.csv", low_memory=False)
    notes.columns = [c.lower() for c in notes.columns]
    truth.columns = [c.lower() for c in truth.columns]

    notes["charttime"] = pd.to_datetime(notes["charttime"], errors="coerce")
    truth["event_time"] = pd.to_datetime(truth["event_time"], errors="coerce")
    truth["note_time"] = pd.to_datetime(truth["note_time"], errors="coerce")

    event_truth = (
        truth[truth["event_type"] != "none"]
        .sort_values(["hadm_id", "event_time"])
        .drop_duplicates("hadm_id")
        [["hadm_id", "event_type", "event_time", "gold_discordant"]]
    )

    merged = notes.merge(event_truth, on="hadm_id", how="inner")
    merged["hours_before_event"] = (
        merged["event_time"] - merged["charttime"]
    ).dt.total_seconds() / 3600
    merged = merged[
        (merged["hours_before_event"] > 0)
        & (merged["hours_before_event"] <= args.window_hours)
    ]

    note_truth = (
        truth[
            [
                "hadm_id",
                "note_time",
                "gold_concern_level",
                "gold_high_concern",
                "gold_discordant",
            ]
        ]
        .drop_duplicates()
    )

    merged = merged.merge(
        note_truth,
        left_on=["hadm_id", "charttime"],
        right_on=["hadm_id", "note_time"],
        how="left",
        suffixes=("", "_truth"),
    )

    records = []
    for i, r in merged.reset_index(drop=True).iterrows():
        concern = int(r.gold_concern_level) if pd.notna(r.gold_concern_level) else None
        high = int(r.gold_high_concern) if pd.notna(r.gold_high_concern) else None
        event = str(r.event_type)

        construct_gold = {
            "overall_clinician_concern": None if concern is None else int(concern >= 1),
            "worsening_trajectory": None if concern is None else int(concern >= 1),
            "respiratory_concern": None if concern is None else int(event == "intubation" and concern >= 1),
            "hemodynamic_concern": None if concern is None else int(event == "vasopressor" and concern >= 1),
            "poor_treatment_response": None if concern is None else int(concern >= 2),
            "escalation_considered": None if concern is None else int(concern >= 2),
            "diagnostic_uncertainty": 0,
            "reassuring_stability": None if concern is None else int(concern == 0),
        }

        records.append(
            {
                "case_id": f"syn_{int(r.hadm_id)}_{i:06d}",\n                "synthetic_only": True,
                "state": {
                    "note_category": str(r.category),
                    "hours_before_event": round(float(r.hours_before_event), 3),
                    "clinical_note": str(r.text),
                },
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": {
                    "event_type": event,
                    "high_concern": high,
                    "concern_level": concern,
                    "discordant": int(r.gold_discordant)
                    if pd.notna(r.gold_discordant)
                    else None,
                    "constructs": construct_gold,
                },
            }
        )

    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = {
        "records": len(records),
        "window_hours": args.window_hours,
        "questions_per_record": len(SEMANTIC_CONSTRUCTS),
        "synthetic_only": True,
        "provider_specific_format": False,
    }
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
