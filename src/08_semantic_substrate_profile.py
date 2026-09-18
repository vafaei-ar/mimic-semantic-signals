from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    find_file, lower_columns, module_path, parse_datetime, read_columns,
    resolve_root, safe_write_csv,
)
from outcomes import build_candidate_events

WINDOWS = [6, 12, 24, 48]

NOTE_GROUPS = {
    "physician_core": {"Physician", "Consult"},
    "nursing_core": {"Nursing", "Nursing/other"},
    "bedside_clinician": {
        "Physician", "Consult", "Nursing", "Nursing/other",
        "Respiratory", "General",
    },
    "extended_clinical": {
        "Physician", "Consult", "Nursing", "Nursing/other",
        "Respiratory", "General", "Case Management", "Social Work",
        "Rehab Services", "Nutrition", "Pharmacy",
    },
    "radiology_only": {"Radiology"},
}


def _admission_dbsource(root: Path) -> dict[int, str]:
    f = find_file(
        module_path(root, "mimiciii"),
        ["ICUSTAYS.csv.gz", "ICUSTAYS.csv", "icustays.csv.gz", "icustays.csv"],
    )
    if f is None:
        return {}
    df = lower_columns(pd.read_csv(f, usecols=lambda c: c.lower() in {"hadm_id", "dbsource"}, low_memory=False))
    if "hadm_id" not in df or "dbsource" not in df:
        return {}
    df["hadm_id"] = pd.to_numeric(df["hadm_id"], errors="coerce")
    df = df.dropna(subset=["hadm_id"])
    out = {}
    for hadm, g in df.groupby("hadm_id"):
        vals = sorted(set(g["dbsource"].dropna().astype(str)))
        out[int(hadm)] = vals[0] if len(vals) == 1 else ("mixed" if vals else "unknown")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)

    events, _ = build_candidate_events(root)
    note_file = find_file(
        module_path(root, "mimiciii"),
        ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv", "noteevents.csv.gz", "noteevents.csv"],
    )
    if events.empty or note_file is None:
        safe_write_csv(pd.DataFrame([{"status": "insufficient_data"}]), out / "semantic_substrate_coverage.csv")
        safe_write_csv(pd.DataFrame([{"status": "insufficient_data"}]), out / "semantic_substrate_by_dbsource.csv")
        return

    event_hadm = set(events["hadm_id"].astype("int64"))
    usable_categories = set().union(*NOTE_GROUPS.values())
    pieces = []

    reader = read_columns(
        note_file,
        ["hadm_id", "charttime", "category", "iserror"],
        chunksize=200_000,
    )
    for chunk in reader:
        c = lower_columns(chunk)
        if "iserror" in c:
            c = c[c["iserror"].fillna(0).astype(str) != "1"]
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(event_hadm)]
        if c.empty:
            continue
        c["note_time"] = parse_datetime(c["charttime"])
        c["category"] = c["category"].fillna("UNKNOWN").astype(str)
        c = c[c["category"].isin(usable_categories)]
        c = c.dropna(subset=["hadm_id", "note_time"])
        c["hadm_id"] = c["hadm_id"].astype("int64")
        pieces.append(c[["hadm_id", "note_time", "category"]])

    if not pieces:
        safe_write_csv(pd.DataFrame([{"status": "no_usable_narrative_notes"}]), out / "semantic_substrate_coverage.csv")
        safe_write_csv(pd.DataFrame([{"status": "no_usable_narrative_notes"}]), out / "semantic_substrate_by_dbsource.csv")
        return

    notes = pd.concat(pieces, ignore_index=True)
    merged = events[["hadm_id", "event_time", "event_type"]].merge(notes, on="hadm_id", how="left")
    merged["hours_before"] = (merged["event_time"] - merged["note_time"]).dt.total_seconds() / 3600
    merged = merged[(merged["hours_before"] > 0) & merged["hours_before"].notna()].copy()

    dbmap = _admission_dbsource(root)
    events = events.copy()
    events["dbsource"] = events["hadm_id"].map(dbmap).fillna("unknown")
    merged["dbsource"] = merged["hadm_id"].map(dbmap).fillna("unknown")

    rows = []
    dbrows = []

    for typ, ev in events.groupby("event_type"):
        total = len(ev)
        for w in WINDOWS:
            base = merged[(merged["event_type"] == typ) & (merged["hours_before"] <= w)]
            for group_name, cats in NOTE_GROUPS.items():
                g = base[base["category"].isin(cats)]
                counts = g.groupby("hadm_id").size()
                covered = int(counts.shape[0])
                closest = g.groupby("hadm_id")["hours_before"].min()
                rows.append({
                    "outcome": typ,
                    "window_hours": w,
                    "note_group": group_name,
                    "total_events": total,
                    "covered_events": covered,
                    "coverage_pct": round(100 * covered / total, 3) if total else 0.0,
                    "notes_in_window": int(len(g)),
                    "events_with_2plus_notes": int((counts >= 2).sum()) if len(counts) else 0,
                    "events_with_3plus_notes": int((counts >= 3).sum()) if len(counts) else 0,
                    "median_notes_among_covered": float(counts.median()) if len(counts) else 0.0,
                    "median_closest_note_hours": float(closest.median()) if len(closest) else np.nan,
                    "p25_closest_note_hours": float(closest.quantile(.25)) if len(closest) else np.nan,
                    "p75_closest_note_hours": float(closest.quantile(.75)) if len(closest) else np.nan,
                })

                for dbs, evdb in ev.groupby("dbsource"):
                    denom = len(evdb)
                    ids = set(evdb["hadm_id"].astype("int64"))
                    gd = g[g["hadm_id"].isin(ids)]
                    cov = gd["hadm_id"].nunique()
                    dbrows.append({
                        "outcome": typ,
                        "dbsource": dbs,
                        "window_hours": w,
                        "note_group": group_name,
                        "total_events": denom,
                        "covered_events": int(cov),
                        "coverage_pct": round(100 * cov / denom, 3) if denom else 0.0,
                    })

    safe_write_csv(pd.DataFrame(rows), out / "semantic_substrate_coverage.csv")
    safe_write_csv(pd.DataFrame(dbrows), out / "semantic_substrate_by_dbsource.csv")


if __name__ == "__main__":
    main()
