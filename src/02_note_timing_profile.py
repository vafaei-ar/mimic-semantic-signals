from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root, safe_write_csv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    note_file = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv", "noteevents.csv.gz", "noteevents.csv"])
    if note_file is None:
        safe_write_csv(pd.DataFrame([{"status": "not_available"}]), out / "note_timing_summary.csv")
        safe_write_csv(pd.DataFrame([{"status": "not_available"}]), out / "note_categories.csv")
        return

    counts = Counter()
    timed = Counter()
    hadm_sets = defaultdict(set)
    subject_sets = defaultdict(set)
    note_counts_by_hadm = Counter()
    total = 0
    total_with_charttime = 0
    total_with_hadm = 0

    reader = read_columns(
        note_file,
        ["subject_id", "hadm_id", "chartdate", "charttime", "category", "description", "iserror"],
        chunksize=200_000,
    )
    for chunk in reader:
        c = lower_columns(chunk)
        if "iserror" in c:
            c = c[c["iserror"].fillna(0).astype(str) != "1"]
        n = len(c)
        total += n
        if "charttime" in c:
            ct = parse_datetime(c["charttime"])
            total_with_charttime += int(ct.notna().sum())
        else:
            ct = pd.Series(pd.NaT, index=c.index)
        if "hadm_id" in c:
            hadm_num = pd.to_numeric(c["hadm_id"], errors="coerce")
            total_with_hadm += int(hadm_num.notna().sum())
        else:
            hadm_num = pd.Series(np.nan, index=c.index)

        cats = c["category"].fillna("UNKNOWN").astype(str) if "category" in c else pd.Series("UNKNOWN", index=c.index)
        subs = pd.to_numeric(c["subject_id"], errors="coerce") if "subject_id" in c else pd.Series(np.nan, index=c.index)

        for cat, idx in cats.groupby(cats).groups.items():
            idx = list(idx)
            counts[cat] += len(idx)
            timed[cat] += int(ct.loc[idx].notna().sum())
            hadms = hadm_num.loc[idx].dropna().astype("int64").unique().tolist()
            subs2 = subs.loc[idx].dropna().astype("int64").unique().tolist()
            hadm_sets[cat].update(hadms)
            subject_sets[cat].update(subs2)

        valid_hadm = hadm_num.dropna().astype("int64")
        note_counts_by_hadm.update(valid_hadm.value_counts().to_dict())

    rows = []
    for cat in sorted(counts):
        rows.append({
            "category": cat,
            "notes": counts[cat],
            "unique_admissions": len(hadm_sets[cat]),
            "unique_subjects": len(subject_sets[cat]),
            "charttime_available_n": timed[cat],
            "charttime_available_pct": round(100 * timed[cat] / counts[cat], 3) if counts[cat] else 0.0,
        })
    safe_write_csv(pd.DataFrame(rows), out / "note_categories.csv")

    per_hadm = np.array(list(note_counts_by_hadm.values()), dtype=float)
    summary = pd.DataFrame([{
        "status": "ok",
        "total_notes": total,
        "notes_with_charttime": total_with_charttime,
        "charttime_available_pct": round(100 * total_with_charttime / total, 3) if total else 0.0,
        "notes_with_hadm_id": total_with_hadm,
        "hadm_available_pct": round(100 * total_with_hadm / total, 3) if total else 0.0,
        "admissions_with_notes": int(len(per_hadm)),
        "median_notes_per_admission": float(np.median(per_hadm)) if len(per_hadm) else 0.0,
        "p25_notes_per_admission": float(np.quantile(per_hadm, .25)) if len(per_hadm) else 0.0,
        "p75_notes_per_admission": float(np.quantile(per_hadm, .75)) if len(per_hadm) else 0.0,
    }])
    safe_write_csv(summary, out / "note_timing_summary.csv")


if __name__ == "__main__":
    main()
