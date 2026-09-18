from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import resolve_root, safe_write_csv, write_json
from outcomes import build_candidate_events


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    events, meta = build_candidate_events(root)

    definitions = pd.DataFrame([
        {"outcome":"in_hospital_death","definition":"MIMIC-III ADMISSIONS.DEATHTIME","purpose":"hard deterioration endpoint"},
        {"outcome":"vasopressor_initiation","definition":"earliest INPUTEVENTS_MV starttime for D_ITEMS labels matching common vasopressors","purpose":"timestamped hemodynamic escalation"},
        {"outcome":"intubation_procedure","definition":"earliest PROCEDUREEVENTS_MV starttime for D_ITEMS labels matching intubation","purpose":"timestamped respiratory escalation; exploratory"},
    ])
    safe_write_csv(definitions, out / "candidate_outcomes.csv")

    rows = []
    if not events.empty:
        for typ, g in events.groupby("event_type"):
            rows.append({
                "outcome": typ,
                "events": len(g),
                "unique_admissions": g["hadm_id"].nunique(),
                "unique_subjects": g["subject_id"].nunique(),
                "timestamp_available_pct": round(100 * g["event_time"].notna().mean(), 3),
            })
    safe_write_csv(pd.DataFrame(rows), out / "outcome_event_counts.csv")
    write_json(meta, out / "outcome_itemid_discovery.json")


if __name__ == "__main__":
    main()
