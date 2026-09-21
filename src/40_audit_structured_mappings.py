from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


MIMIC_PRESSOR_IDS = {
    30043, 30044, 30046, 30047, 30051, 30119, 30120,
    30125, 30127, 30128, 30307, 30309,
    221289, 221662, 221749, 221906, 222315, 227692,
}


def find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"Expected exactly one {name} under {root}; found {len(hits)}")
    return hits[0]


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def audit_nwicu_bp(root: Path) -> dict:
    d_items = pd.read_csv(find_one(root, "d_items.csv.gz"), low_memory=False)
    label = d_items["label"].fillna("").astype(str)

    candidate_mask = label.str.contains(
        r"mean|pressure|\bbp\b|abp|nibp|nbp|arterial|systolic|diastolic",
        case=False,
        regex=True,
        na=False,
    )
    cand = d_items.loc[candidate_mask].copy()

    # Keep chart-event candidates preferentially but report all matching dictionary rows.
    candidate_ids = set(
        pd.to_numeric(cand["itemid"], errors="coerce").dropna().astype(int).tolist()
    )

    counts = Counter()
    numeric_counts = Counter()
    stay_counts: dict[int, set[int]] = {i: set() for i in candidate_ids}

    if candidate_ids:
        chart = find_one(root, "chartevents.csv.gz")
        for chunk in pd.read_csv(
            chart,
            chunksize=500_000,
            usecols=["stay_id", "itemid", "valuenum"],
            low_memory=False,
        ):
            chunk["itemid"] = pd.to_numeric(chunk["itemid"], errors="coerce")
            q = chunk[chunk["itemid"].isin(candidate_ids)].copy()
            if q.empty:
                continue
            q["stay_id"] = pd.to_numeric(q["stay_id"], errors="coerce")
            q["valuenum"] = pd.to_numeric(q["valuenum"], errors="coerce")
            for itemid, n in q["itemid"].value_counts().items():
                counts[int(itemid)] += int(n)
            for itemid, n in q.loc[q["valuenum"].notna(), "itemid"].value_counts().items():
                numeric_counts[int(itemid)] += int(n)
            for itemid, group in q.dropna(subset=["stay_id"]).groupby("itemid"):
                stay_counts[int(itemid)].update(group["stay_id"].astype(int).tolist())

    rows = []
    cols = [c for c in ["itemid", "label", "category", "unitname", "linksto"] if c in cand.columns]
    for rec in cand[cols].drop_duplicates().to_dict("records"):
        itemid = int(rec["itemid"])
        rows.append({
            **rec,
            "row_count": int(counts[itemid]),
            "numeric_row_count": int(numeric_counts[itemid]),
            "unique_stays": int(len(stay_counts[itemid])),
        })

    rows.sort(key=lambda x: (-x["numeric_row_count"], str(x.get("label", ""))))
    return {
        "candidate_count": len(rows),
        "candidates": rows,
    }


def audit_mimic_pressors(root: Path) -> dict:
    mimic = root / "mimiciii"
    d_items_path = find_one(mimic, "D_ITEMS.csv.gz")
    d_items = pd.read_csv(d_items_path, low_memory=False)
    d_items.columns = [str(c).lower() for c in d_items.columns]
    d_items["itemid"] = pd.to_numeric(d_items["itemid"], errors="coerce")
    labels = d_items[d_items["itemid"].isin(MIMIC_PRESSOR_IDS)].copy()

    dictionary = labels[
        [c for c in ["itemid", "label", "abbreviation", "dbsource", "linksto", "unitname"] if c in labels.columns]
    ].sort_values("itemid").to_dict("records")

    usage: dict[str, dict] = {}

    cv = find_one(mimic, "INPUTEVENTS_CV.csv.gz")
    cv_counts = Counter()
    cv_hadms: dict[int, set[int]] = {}
    for chunk in pd.read_csv(
        cv,
        chunksize=500_000,
        usecols=lambda c: str(c).lower() in {"hadm_id", "itemid", "amount", "rate"},
        low_memory=False,
    ):
        chunk.columns = [str(c).lower() for c in chunk.columns]
        chunk["itemid"] = pd.to_numeric(chunk["itemid"], errors="coerce")
        q = chunk[chunk["itemid"].isin(MIMIC_PRESSOR_IDS)].copy()
        if q.empty:
            continue
        q["hadm_id"] = pd.to_numeric(q["hadm_id"], errors="coerce")
        for itemid, n in q["itemid"].value_counts().items():
            cv_counts[int(itemid)] += int(n)
        for itemid, g in q.dropna(subset=["hadm_id"]).groupby("itemid"):
            cv_hadms.setdefault(int(itemid), set()).update(g["hadm_id"].astype(int).tolist())

    mv = find_one(mimic, "INPUTEVENTS_MV.csv.gz")
    mv_counts = Counter()
    mv_hadms: dict[int, set[int]] = {}
    for chunk in pd.read_csv(
        mv,
        chunksize=500_000,
        usecols=lambda c: str(c).lower() in {"hadm_id", "itemid", "amount", "rate", "statusdescription"},
        low_memory=False,
    ):
        chunk.columns = [str(c).lower() for c in chunk.columns]
        chunk["itemid"] = pd.to_numeric(chunk["itemid"], errors="coerce")
        q = chunk[chunk["itemid"].isin(MIMIC_PRESSOR_IDS)].copy()
        if q.empty:
            continue
        if "statusdescription" in q:
            bad = q["statusdescription"].fillna("").astype(str).str.lower().str.contains(
                "rewritten|cancelled"
            )
            q = q[~bad]
        q["hadm_id"] = pd.to_numeric(q["hadm_id"], errors="coerce")
        for itemid, n in q["itemid"].value_counts().items():
            mv_counts[int(itemid)] += int(n)
        for itemid, g in q.dropna(subset=["hadm_id"]).groupby("itemid"):
            mv_hadms.setdefault(int(itemid), set()).update(g["hadm_id"].astype(int).tolist())

    for itemid in sorted(MIMIC_PRESSOR_IDS):
        usage[str(itemid)] = {
            "carevue_rows": int(cv_counts[itemid]),
            "carevue_unique_admissions": int(len(cv_hadms.get(itemid, set()))),
            "metavision_rows": int(mv_counts[itemid]),
            "metavision_unique_admissions": int(len(mv_hadms.get(itemid, set()))),
        }

    item_30125 = next(
        (x for x in dictionary if int(x.get("itemid", -1)) == 30125),
        None,
    )

    return {
        "dictionary": dictionary,
        "usage": usage,
        "item_30125": item_30125,
        "recommendation_rule": (
            "If item 30125 is not a vasopressor label, exclude it from the frozen "
            "MIMIC vasopressor endpoint before constructing the exact-6h cohort."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Audit NWICU blood-pressure dictionary items and MIMIC-III pressor item 30125."
    )
    ap.add_argument("--nwicu-root", required=True)
    ap.add_argument("--mimic-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    report = {
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "contains_patient_level_rows": False,
        "nwicu_bp_dictionary_audit": audit_nwicu_bp(
            Path(args.nwicu_root).expanduser().resolve()
        ),
        "mimic_pressor_dictionary_audit": audit_mimic_pressors(
            Path(args.mimic_root).expanduser().resolve()
        ),
    }

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
