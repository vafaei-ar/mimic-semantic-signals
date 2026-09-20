from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd

from common import (
    find_file,
    lower_columns,
    module_path,
    parse_datetime,
    read_columns,
    resolve_root,
)
from semantic_schema import SEMANTIC_CONSTRUCTS


# Canonical MIMIC-III vasopressor ITEMIDs audited in src/09_event_definition_audit.py.
CANONICAL_VASO_CV = {
    30043, 30044, 30046, 30047, 30051, 30119, 30120,
    30125, 30127, 30128, 30307, 30309,
}
CANONICAL_VASO_MV = {221289, 221662, 221749, 221906, 222315, 227692}
INTUBATION_MV_ITEMID = 224385

BEDSIDE_CATEGORIES = {
    "Physician",
    "Consult",
    "Nursing",
    "Nursing/other",
    "Respiratory",
    "General",
}

TIME_BINS = [
    ("0_6h", 0.0, 6.0),
    ("6_12h", 6.0, 12.0),
    ("12_24h", 12.0, 24.0),
]


def death_events(root: Path) -> pd.DataFrame:
    f = find_file(
        module_path(root, "mimiciii"),
        ["ADMISSIONS.csv.gz", "ADMISSIONS.csv"],
    )
    if f is None:
        return pd.DataFrame()
    d = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: c.lower() in {"hadm_id", "deathtime"},
            low_memory=False,
        )
    )
    d["hadm_id"] = pd.to_numeric(d["hadm_id"], errors="coerce")
    d["event_time"] = parse_datetime(d["deathtime"])
    d = d.dropna(subset=["hadm_id", "event_time"]).copy()
    d["hadm_id"] = d["hadm_id"].astype("int64")
    d["event_type"] = "in_hospital_death"
    return d[["hadm_id", "event_time", "event_type"]]


def _pressor_file_events(
    root: Path,
    names: list[str],
    itemids: set[int],
    time_col: str,
    status_col: str | None = None,
) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), names)
    if f is None:
        return pd.DataFrame()

    wanted = ["hadm_id", "itemid", time_col]
    if status_col:
        wanted.append(status_col)

    pieces = []
    for chunk in read_columns(f, wanted, chunksize=250_000):
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(itemids)]
        if c.empty:
            continue
        if status_col and status_col in c:
            bad = c[status_col].fillna("").astype(str).str.lower().str.contains(
                "rewritten|cancelled"
            )
            c = c[~bad]
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c["event_time"] = parse_datetime(c[time_col])
        c = c.dropna(subset=["hadm_id", "event_time"])
        if not c.empty:
            pieces.append(c[["hadm_id", "event_time"]])

    if not pieces:
        return pd.DataFrame()
    d = pd.concat(pieces, ignore_index=True)
    d["hadm_id"] = d["hadm_id"].astype("int64")
    return d


def vasopressor_events(root: Path) -> pd.DataFrame:
    mv = _pressor_file_events(
        root,
        ["INPUTEVENTS_MV.csv.gz", "INPUTEVENTS_MV.csv"],
        CANONICAL_VASO_MV,
        "starttime",
        "statusdescription",
    )
    cv = _pressor_file_events(
        root,
        ["INPUTEVENTS_CV.csv.gz", "INPUTEVENTS_CV.csv"],
        CANONICAL_VASO_CV,
        "charttime",
        None,
    )
    frames = [x for x in [mv, cv] if not x.empty]
    if not frames:
        return pd.DataFrame()
    d = pd.concat(frames, ignore_index=True)
    d = (
        d.sort_values("event_time")
        .groupby("hadm_id", as_index=False)
        .first()
    )
    d["event_type"] = "vasopressor_initiation"
    return d[["hadm_id", "event_time", "event_type"]]


def intubation_events(root: Path) -> pd.DataFrame:
    f = find_file(
        module_path(root, "mimiciii"),
        ["PROCEDUREEVENTS_MV.csv.gz", "PROCEDUREEVENTS_MV.csv"],
    )
    if f is None:
        return pd.DataFrame()

    pieces = []
    for chunk in read_columns(
        f,
        ["hadm_id", "itemid", "starttime"],
        chunksize=250_000,
    ):
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"] == INTUBATION_MV_ITEMID]
        if c.empty:
            continue
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c["event_time"] = parse_datetime(c["starttime"])
        c = c.dropna(subset=["hadm_id", "event_time"])
        if not c.empty:
            pieces.append(c[["hadm_id", "event_time"]])

    if not pieces:
        return pd.DataFrame()
    d = pd.concat(pieces, ignore_index=True)
    d["hadm_id"] = d["hadm_id"].astype("int64")
    d = (
        d.sort_values("event_time")
        .groupby("hadm_id", as_index=False)
        .first()
    )
    d["event_type"] = "intubation_mv_procedure"
    return d[["hadm_id", "event_time", "event_type"]]


def admission_dbsource(root: Path) -> dict[int, str]:
    f = find_file(
        module_path(root, "mimiciii"),
        ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"],
    )
    if f is None:
        return {}
    d = lower_columns(
        pd.read_csv(
            f,
            usecols=lambda c: c.lower() in {"hadm_id", "dbsource"},
            low_memory=False,
        )
    )
    d["hadm_id"] = pd.to_numeric(d["hadm_id"], errors="coerce")
    d = d.dropna(subset=["hadm_id"])
    out = {}
    for hadm, g in d.groupby("hadm_id"):
        vals = sorted(set(g["dbsource"].dropna().astype(str)))
        out[int(hadm)] = vals[0] if len(vals) == 1 else ("mixed" if vals else "unknown")
    return out


def assign_time_bin(hours: float) -> str | None:
    for name, lo, hi in TIME_BINS:
        if hours > lo and hours <= hi:
            return name
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Build a local-only real MIMIC-III event-anchored note pilot. "
            "The output contains credentialed note text and must stay local."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--n-per-stratum", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260920)
    args = ap.parse_args()

    root = resolve_root(args.root)
    output = Path(args.output).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    event_frames = [
        death_events(root),
        vasopressor_events(root),
        intubation_events(root),
    ]
    event_frames = [x for x in event_frames if not x.empty]
    if not event_frames:
        raise RuntimeError("No canonical pilot events were found.")

    events = pd.concat(event_frames, ignore_index=True)
    events = events.drop_duplicates(["hadm_id", "event_type"]).copy()
    event_hadm = set(events["hadm_id"].astype("int64"))

    note_file = find_file(
        module_path(root, "mimiciii"),
        ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"],
    )
    if note_file is None:
        raise FileNotFoundError("MIMIC-III NOTEEVENTS was not found.")

    note_parts = []
    for chunk in read_columns(
        note_file,
        ["hadm_id", "charttime", "category", "iserror", "text"],
        chunksize=100_000,
    ):
        c = lower_columns(chunk)
        c["hadm_id"] = pd.to_numeric(c["hadm_id"], errors="coerce")
        c = c[c["hadm_id"].isin(event_hadm)]
        if c.empty:
            continue
        if "iserror" in c:
            c = c[c["iserror"].fillna(0).astype(str) != "1"]
        c["category"] = c["category"].fillna("UNKNOWN").astype(str)
        c = c[c["category"].isin(BEDSIDE_CATEGORIES)]
        if c.empty:
            continue
        c["note_time"] = parse_datetime(c["charttime"])
        c = c.dropna(subset=["hadm_id", "note_time", "text"])
        c["hadm_id"] = c["hadm_id"].astype("int64")
        note_parts.append(c[["hadm_id", "note_time", "category", "text"]])

    if not note_parts:
        raise RuntimeError("No usable bedside clinician notes were found.")

    notes = pd.concat(note_parts, ignore_index=True)
    merged = events.merge(notes, on="hadm_id", how="inner")
    merged["hours_before_event"] = (
        merged["event_time"] - merged["note_time"]
    ).dt.total_seconds() / 3600
    merged = merged[
        (merged["hours_before_event"] > 0)
        & (merged["hours_before_event"] <= 24)
    ].copy()
    merged["time_bin"] = merged["hours_before_event"].map(assign_time_bin)
    merged = merged.dropna(subset=["time_bin"])

    # Keep the closest note to the event within each admission/event/time bin.
    merged = (
        merged.sort_values("hours_before_event")
        .groupby(["hadm_id", "event_type", "time_bin"], as_index=False)
        .first()
    )

    rng = random.Random(args.seed)
    sampled_parts = []
    for (event_type, time_bin), g in merged.groupby(
        ["event_type", "time_bin"],
        sort=True,
    ):
        rows = list(g.index)
        rng.shuffle(rows)
        take = rows[: min(args.n_per_stratum, len(rows))]
        sampled_parts.append(g.loc[take])

    if not sampled_parts:
        raise RuntimeError("No event-note strata were available for sampling.")

    sample = pd.concat(sampled_parts, ignore_index=True)
    dbmap = admission_dbsource(root)
    sample["dbsource"] = sample["hadm_id"].map(dbmap).fillna("unknown")

    hadms = sorted(sample["hadm_id"].unique().tolist())
    group_map = {hadm: i + 1 for i, hadm in enumerate(hadms)}

    records = []
    for i, r in sample.iterrows():
        group = group_map[int(r.hadm_id)]
        records.append(
            {
                "case_id": (
                    f"realpilot_{r.event_type}_{group:04d}_{r.time_bin}_{i:04d}"
                ),
                "synthetic_only": False,
                "local_only": True,
                "model_state": {
                    "clinical_note": str(r.text),
                },
                "metadata": {
                    "data_source": "MIMIC-III 1.4",
                    "admission_group": f"g{group:04d}",
                    "event_type": str(r.event_type),
                    "time_bin": str(r.time_bin),
                    "hours_before_event": round(float(r.hours_before_event), 3),
                    "note_category": str(r.category),
                    "dbsource": str(r.dbsource),
                    "note_characters": len(str(r.text)),
                },
                "questions": SEMANTIC_CONSTRUCTS,
                "gold": None,
            }
        )

    with output.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    counts = (
        sample.groupby(["event_type", "time_bin"])
        .size()
        .rename("n")
        .reset_index()
        .to_dict(orient="records")
    )
    category_counts = (
        sample.groupby(["event_type", "time_bin", "category"])
        .size()
        .rename("n")
        .reset_index()
        .to_dict(orient="records")
    )

    manifest = {
        "local_only": True,
        "contains_credentialed_note_text": True,
        "data_source": "MIMIC-III 1.4",
        "event_definitions": {
            "vasopressor": "canonical audited vasopressor ITEMIDs; first event per admission",
            "intubation": "MetaVision PROCEDUREEVENTS_MV ITEMID 224385; first event per admission",
            "death": "ADMISSIONS.DEATHTIME",
        },
        "note_categories": sorted(BEDSIDE_CATEGORIES),
        "selection": "closest note within each admission/event/time-bin, then deterministic stratum sample",
        "n_per_stratum_requested": args.n_per_stratum,
        "seed": args.seed,
        "records": len(records),
        "unique_admission_groups": len(hadms),
        "counts_by_event_time_bin": counts,
        "counts_by_event_time_bin_category": category_counts,
        "warning": (
            "Exploratory local pilot only. No controls and no structured physiology are "
            "included, so these results cannot estimate discrimination or incremental value."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
