from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from semantic_schema import SEMANTIC_CONSTRUCTS


def text_faithful_gold(text: str) -> dict[str, int]:
    """Assign synthetic gold from what the note actually says, not the future event."""
    t = text.lower()

    stable = any(
        phrase in t
        for phrase in [
            "resting comfortably",
            "clinical status remains similar",
            "remains stable on current support",
            "no acute change",
            "no new concern",
        ]
    )

    concern = any(
        phrase in t
        for phrase in [
            "more tired than earlier",
            "somewhat less well",
            "subtle change from earlier",
            "increasingly difficult to arouse",
            "clinical appearance is worsening",
            "substantially worse than earlier",
            "poorly perfused",
            "circulatory instability",
            "work of breathing is progressively increasing",
            "respiratory effort has worsened",
            "overall clinical condition is worsening",
            "increasingly frail",
            "growing concern",
        ]
    )

    worsening = any(
        phrase in t
        for phrase in [
            "more tired than earlier",
            "less well than the prior assessment",
            "change from earlier",
            "increasingly difficult to arouse",
            "worsening",
            "worse than earlier",
            "progressively increasing",
            "has worsened",
            "increasingly frail",
        ]
    )

    respiratory = any(
        phrase in t
        for phrase in [
            "respiratory effort is intermittently increased",
            "breathing is more labored",
            "work of breathing is progressively increasing",
            "respiratory effort has worsened",
            "respiratory support may need escalation",
            "invasive airway support",
        ]
    )

    hemodynamic = any(
        phrase in t
        for phrase in [
            "poorly perfused",
            "hemodynamic deterioration",
            "circulatory instability",
            "vasoactive support",
        ]
    )

    poor_response = any(
        phrase in t
        for phrase in [
            "response to the current plan is incomplete",
            "response to recent treatment has been limited",
            "has not produced the expected response",
            "less responsive to treatment",
            "reassessing response to fluids",
        ]
    )

    if "no escalation is being considered" in t:
        escalation = False
    else:
        escalation = any(
            phrase in t
            for phrase in [
                "considering escalation",
                "discussing a higher level of support",
                "escalation is being considered",
                "discussing vasoactive support",
                "support may need escalation",
                "discussing whether invasive airway support",
            ]
        )

    uncertainty = any(
        phrase in t
        for phrase in [
            "diagnosis remains unclear",
            "cause remains unclear",
            "uncertain whether",
            "diagnostic uncertainty",
        ]
    )

    reassuring = stable and not concern

    return {
        "overall_clinician_concern": int(concern),
        "worsening_trajectory": int(worsening),
        "respiratory_concern": int(respiratory),
        "hemodynamic_concern": int(hemodynamic),
        "poor_treatment_response": int(poor_response),
        "escalation_considered": int(escalation),
        "diagnostic_uncertainty": int(uncertainty),
        "reassuring_stability": int(reassuring),
    }


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

    notes = pd.read_csv(
        mimic / "NOTEEVENTS.csv.gz",
        compression="gzip",
        low_memory=False,
    )
    truth = pd.read_csv(root / "synthetic_truth.csv", low_memory=False)
    notes.columns = [c.lower() for c in notes.columns]
    truth.columns = [c.lower() for c in truth.columns]

    notes["charttime"] = pd.to_datetime(notes["charttime"], errors="coerce")
    truth["event_time"] = pd.to_datetime(truth["event_time"], errors="coerce")
    truth["note_time"] = pd.to_datetime(truth["note_time"], errors="coerce")

    admission_truth = (
        truth.sort_values(["hadm_id", "note_time"])
        .groupby("hadm_id", as_index=False)
        .agg(
            event_type=("event_type", "first"),
            event_time=("event_time", "first"),
            gold_discordant=("gold_discordant", "max"),
            last_truth_note=("note_time", "max"),
        )
    )

    # Stable admissions need a pseudo-anchor so their notes can serve as matched
    # negative controls in the same 24-hour temporal framing.
    is_none = admission_truth["event_type"].eq("none")
    admission_truth.loc[is_none, "event_time"] = (
        admission_truth.loc[is_none, "last_truth_note"] + pd.to_timedelta(3, unit="h")
    )
    admission_truth["anchor_type"] = admission_truth["event_type"].where(
        ~is_none,
        "stable_control",
    )

    merged = notes.merge(
        admission_truth[
            [
                "hadm_id",
                "event_type",
                "event_time",
                "gold_discordant",
                "anchor_type",
            ]
        ],
        on="hadm_id",
        how="inner",
    )
    merged["hours_before_event"] = (
        merged["event_time"] - merged["charttime"]
    ).dt.total_seconds() / 3600
    merged = merged[
        (merged["hours_before_event"] > 0)
        & (merged["hours_before_event"] <= args.window_hours)
    ].copy()

    records = []
    for i, r in merged.reset_index(drop=True).iterrows():
        event = str(r.event_type)
        construct_gold = text_faithful_gold(str(r.text))
        concern = int(construct_gold["overall_clinician_concern"])
        high = int(
            construct_gold["escalation_considered"]
            or construct_gold["poor_treatment_response"]
            or construct_gold["respiratory_concern"]
            or construct_gold["hemodynamic_concern"]
        )

        records.append(
            {
                "case_id": f"syn_{int(r.hadm_id)}_{i:06d}",
                "synthetic_only": True,
                "model_state": {
                    "clinical_note": str(r.text),
                },
                "metadata": {
                    "note_category": str(r.category),
                    "hours_before_event": round(float(r.hours_before_event), 3),
                },
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": {
                    "event_type": event,
                    "anchor_type": str(r.anchor_type),
                    "high_concern": high,
                    "concern_level": int(concern + high),
                    "discordant": int(r.gold_discordant)
                    if pd.notna(r.gold_discordant)
                    else 0,
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
        "gold_definition": "text_faithful_v2",
        "includes_stable_controls": True,
    }
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
