from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root, safe_write_csv
from outcomes import build_candidate_events

WINDOWS = [6, 12, 24, 48]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    events, _ = build_candidate_events(root)
    note_file = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz","NOTEEVENTS.csv","noteevents.csv.gz","noteevents.csv"])

    if events.empty or note_file is None:
        safe_write_csv(pd.DataFrame([{"status":"insufficient_data"}]), out / "pre_event_coverage.csv")
        safe_write_csv(pd.DataFrame([{"status":"insufficient_data"}]), out / "pre_event_coverage_by_category.csv")
        return

    event_hadm = set(events["hadm_id"].astype("int64"))
    notes = []
    reader = read_columns(note_file, ["hadm_id","charttime","category","iserror"], chunksize=200_000)
    for chunk in reader:
        c = lower_columns(chunk)
        if "iserror" in c:
            c = c[c["iserror"].fillna(0).astype(str) != "1"]
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(event_hadm)]
        if c.empty:
            continue
        c["note_time"] = parse_datetime(c["charttime"])
        c = c.dropna(subset=["note_time","hadm_id"])
        c["hadm_id"] = c["hadm_id"].astype("int64")
        if "category" not in c:
            c["category"] = "UNKNOWN"
        notes.append(c[["hadm_id","note_time","category"]])

    if not notes:
        safe_write_csv(pd.DataFrame([{"status":"no_timed_notes"}]), out / "pre_event_coverage.csv")
        safe_write_csv(pd.DataFrame([{"status":"no_timed_notes"}]), out / "pre_event_coverage_by_category.csv")
        return

    n = pd.concat(notes, ignore_index=True)
    merged = events[["hadm_id","event_time","event_type"]].merge(n, on="hadm_id", how="left")
    merged["hours_before"] = (merged["event_time"] - merged["note_time"]).dt.total_seconds() / 3600
    merged = merged[(merged["hours_before"] > 0) & merged["hours_before"].notna()]

    rows = []
    cat_rows = []
    event_totals = events.groupby("event_type").size().to_dict()

    for typ, total in event_totals.items():
        g = merged[merged["event_type"] == typ]
        for w in WINDOWS:
            gw = g[g["hours_before"] <= w]
            covered = gw["hadm_id"].nunique()
            rows.append({
                "outcome": typ,
                "window_hours": w,
                "total_events": int(total),
                "events_with_at_least_one_timed_note": int(covered),
                "coverage_pct": round(100 * covered / total, 3) if total else 0.0,
                "notes_in_window": int(len(gw)),
            })
            if not gw.empty:
                for cat, cg in gw.groupby("category"):
                    cat_rows.append({
                        "outcome": typ,
                        "window_hours": w,
                        "category": str(cat),
                        "events_with_category_note": int(cg["hadm_id"].nunique()),
                        "notes_in_window": int(len(cg)),
                    })

    safe_write_csv(pd.DataFrame(rows), out / "pre_event_coverage.csv")
    safe_write_csv(pd.DataFrame(cat_rows), out / "pre_event_coverage_by_category.csv")


if __name__ == "__main__":
    main()
