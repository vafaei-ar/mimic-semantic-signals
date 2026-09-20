from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from semantic_schema import SEMANTIC_CONSTRUCTS

CANONICAL_VASO_CV = {
    30043, 30044, 30046, 30047, 30051, 30119, 30120,
    30125, 30127, 30128, 30307, 30309,
}
CANONICAL_VASO_MV = {221289, 221662, 221749, 221906, 222315, 227692}
INTUBATION_MV_ITEMID = 224385

BEDSIDE_CATEGORIES = {
    "Physician", "Consult", "Nursing", "Nursing/other", "Respiratory", "General",
}

TIME_BINS = [
    ("0_6h", 0.0, 6.0),
    ("6_12h", 6.0, 12.0),
    ("12_24h", 12.0, 24.0),
]
REQUIRED_BINS = {x[0] for x in TIME_BINS}


def assign_time_bin(hours: float) -> str | None:
    for name, lo, hi in TIME_BINS:
        if hours > lo and hours <= hi:
            return name
    return None


def death_events(root: Path) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), ["ADMISSIONS.csv.gz", "ADMISSIONS.csv"])
    if f is None:
        return pd.DataFrame()
    d = lower_columns(pd.read_csv(
        f,
        usecols=lambda c: c.lower() in {"hadm_id", "deathtime"},
        low_memory=False,
    ))
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
    status_col: str | None,
) -> pd.DataFrame:
    f = find_file(module_path(root, "mimiciii"), names)
    if f is None:
        return pd.DataFrame()
    wanted = ["hadm_id", "itemid", time_col] + ([status_col] if status_col else [])
    pieces = []
    for chunk in read_columns(f, wanted, chunksize=250_000):
        c = lower_columns(chunk)
        c["itemid"] = pd.to_numeric(c["itemid"], errors="coerce")
        c = c[c["itemid"].isin(itemids)]
        if c.empty:
            continue
        if status_col and status_col in c:
            bad = c[status_col].fillna("").astype(str).str.lower().str.contains("rewritten|cancelled")
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
    d = d.sort_values("event_time").groupby("hadm_id", as_index=False).first()
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
    for chunk in read_columns(f, ["hadm_id", "itemid", "starttime"], chunksize=250_000):
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
    d = d.sort_values("event_time").groupby("hadm_id", as_index=False).first()
    d["event_type"] = "intubation_mv_procedure"
    return d[["hadm_id", "event_time", "event_type"]]


def admission_dbsource(root: Path) -> dict[int, str]:
    f = find_file(module_path(root, "mimiciii"), ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"])
    if f is None:
        return {}
    d = lower_columns(pd.read_csv(
        f,
        usecols=lambda c: c.lower() in {"hadm_id", "dbsource"},
        low_memory=False,
    ))
    d["hadm_id"] = pd.to_numeric(d["hadm_id"], errors="coerce")
    d = d.dropna(subset=["hadm_id"])
    out = {}
    for hadm, g in d.groupby("hadm_id"):
        vals = sorted(set(g["dbsource"].dropna().astype(str)))
        out[int(hadm)] = vals[0] if len(vals) == 1 else ("mixed" if vals else "unknown")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build a longitudinal real-MIMIC local pilot with the same admissions across all time bins."
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--n-per-event", type=int, default=100)
    ap.add_argument("--same-category", action="store_true")
    ap.add_argument("--seed", type=int, default=20260920)
    args = ap.parse_args()

    root = resolve_root(args.root)
    output = Path(args.output).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    events = pd.concat(
        [x for x in [death_events(root), vasopressor_events(root), intubation_events(root)] if not x.empty],
        ignore_index=True,
    ).drop_duplicates(["hadm_id", "event_type"])
    event_hadm = set(events["hadm_id"].astype("int64"))

    note_file = find_file(module_path(root, "mimiciii"), ["NOTEEVENTS.csv.gz", "NOTEEVENTS.csv"])
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

    # One closest note per admission/event/time-bin/category first, so category
    # consistency can be enforced without arbitrary row-order dependence.
    closest_by_category = (
        merged.sort_values("hours_before_event")
        .groupby(["hadm_id", "event_type", "time_bin", "category"], as_index=False)
        .first()
    )

    eligible_records = []
    eligibility = []
    for (hadm_id, event_type), g in closest_by_category.groupby(["hadm_id", "event_type"]):
        bins = set(g["time_bin"])
        if bins != REQUIRED_BINS:
            continue

        selected = None
        selected_category = None
        if args.same_category:
            cats = []
            for category, cg in g.groupby("category"):
                if set(cg["time_bin"]) == REQUIRED_BINS:
                    cats.append(category)
            if not cats:
                continue
            # Prefer the most common bedside sources in a deterministic order.
            preference = ["Nursing", "Nursing/other", "Physician", "General", "Respiratory", "Consult"]
            selected_category = sorted(
                cats,
                key=lambda x: (preference.index(x) if x in preference else 99, x),
            )[0]
            selected = g[g["category"] == selected_category].copy()
        else:
            selected = (
                g.sort_values("hours_before_event")
                .groupby("time_bin", as_index=False)
                .first()
            )

        if set(selected["time_bin"]) != REQUIRED_BINS:
            continue

        eligibility.append({
            "hadm_id": int(hadm_id),
            "event_type": str(event_type),
            "same_category": bool(args.same_category),
            "selected_category": selected_category or "mixed_allowed",
        })
        eligible_records.append(selected)

    if not eligible_records:
        raise RuntimeError("No admissions had usable notes in all three time bins.")

    longitudinal = pd.concat(eligible_records, ignore_index=True)
    eligible_df = pd.DataFrame(eligibility)

    rng = random.Random(args.seed)
    selected_hadms = []
    available_by_event = {}
    for event_type, g in eligible_df.groupby("event_type"):
        hadms = sorted(g["hadm_id"].astype(int).tolist())
        rng.shuffle(hadms)
        available_by_event[event_type] = len(hadms)
        selected_hadms.extend(hadms[: min(args.n_per_event, len(hadms))])

    sample = longitudinal[longitudinal["hadm_id"].isin(selected_hadms)].copy()
    dbmap = admission_dbsource(root)
    sample["dbsource"] = sample["hadm_id"].map(dbmap).fillna("unknown")

    hadms = sorted(sample["hadm_id"].unique().tolist())
    group_map = {hadm: i + 1 for i, hadm in enumerate(hadms)}

    order = {"12_24h": 0, "6_12h": 1, "0_6h": 2}
    sample["time_order"] = sample["time_bin"].map(order)
    sample = sample.sort_values(["event_type", "hadm_id", "time_order"])

    records = []
    for i, r in sample.reset_index(drop=True).iterrows():
        group = group_map[int(r.hadm_id)]
        records.append({
            "case_id": f"reallong_{r.event_type}_{group:04d}_{r.time_bin}",
            "synthetic_only": False,
            "local_only": True,
            "model_state": {"clinical_note": str(r.text)},
            "metadata": {
                "data_source": "MIMIC-III 1.4",
                "admission_group": f"g{group:04d}",
                "event_type": str(r.event_type),
                "time_bin": str(r.time_bin),
                "hours_before_event": round(float(r.hours_before_event), 3),
                "note_category": str(r.category),
                "dbsource": str(r.dbsource),
                "note_characters": len(str(r.text)),
                "longitudinal_complete": True,
            },
            "questions": SEMANTIC_CONSTRUCTS,
            "gold": None,
        })

    with output.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest = {
        "local_only": True,
        "contains_credentialed_note_text": True,
        "data_source": "MIMIC-III 1.4",
        "design": "same admission contributes one note in each of 12-24h, 6-12h, and 0-6h windows",
        "same_category_required": bool(args.same_category),
        "n_per_event_requested": args.n_per_event,
        "seed": args.seed,
        "eligible_admissions_by_event": available_by_event,
        "sampled_admissions": len(hadms),
        "records": len(records),
        "expected_records_per_admission": 3,
        "counts_by_event": (
            sample.groupby("event_type")["hadm_id"].nunique().astype(int).to_dict()
        ),
        "counts_by_event_time_category": (
            sample.groupby(["event_type", "time_bin", "category"])
            .size()
            .rename("n")
            .reset_index()
            .to_dict(orient="records")
        ),
        "warning": (
            "Longitudinal event-only pilot. This supports within-admission temporal analysis, "
            "but controls and structured physiology are still required for predictive claims."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
