from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import pandas as pd

from common import choose_anchor_with_column, find_file, lower_columns, module_path, read_columns, resolve_root, safe_write_csv

ANCHORS = {
    "mimiciv_core": ("mimiciv", ["admissions.csv.gz","admissions.csv"]),
    "mimic_iv_note": ("mimic_iv_note", ["discharge.csv.gz","discharge.csv"]),
    "mimic_iv_ecg": ("mimic_iv_ecg", ["record_list.csv.gz","record_list.csv"]),
    "mimic_iv_echo": ("mimic_iv_echo", ["echo_measurements.csv.gz","echo_measurements.csv","record_list.csv.gz","record_list.csv"]),
}


def _ids(path: Path) -> tuple[set[int], set[int], int]:
    subjects: set[int] = set()
    hadms: set[int] = set()
    rows = 0
    reader = read_columns(path, ["subject_id","hadm_id"], chunksize=250_000)
    for chunk in reader:
        c = lower_columns(chunk)
        rows += len(c)
        if "subject_id" in c:
            subjects.update(pd.to_numeric(c["subject_id"], errors="coerce").dropna().astype("int64").tolist())
        if "hadm_id" in c:
            hadms.update(pd.to_numeric(c["hadm_id"], errors="coerce").dropna().astype("int64").tolist())
    return subjects, hadms, rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)
    data = {}
    detail = []

    for label, (module, names) in ANCHORS.items():
        base = module_path(root, module)
        f = find_file(base, names)
        if f is None:
            f = choose_anchor_with_column(base, "subject_id")
        if f is None:
            detail.append({"dataset":label,"anchor_found":False,"records":0,"unique_subjects":0,"unique_admissions":0})
            continue
        subjects, hadms, rows = _ids(f)
        data[label] = (subjects, hadms)
        detail.append({
            "dataset":label,
            "anchor_found":True,
            "records":rows,
            "unique_subjects":len(subjects),
            "unique_admissions":len(hadms),
        })

    rows = list(detail)
    for a, b in combinations(sorted(data), 2):
        sa, ha = data[a]
        sb, hb = data[b]
        rows.append({
            "dataset":f"{a}__AND__{b}",
            "anchor_found":True,
            "records":0,
            "unique_subjects":len(sa & sb),
            "unique_admissions":len(ha & hb) if ha and hb else 0,
        })

    if "mimic_iv_ecg" in data and "mimic_iv_echo" in data:
        se, he = data["mimic_iv_ecg"]
        sx, hx = data["mimic_iv_echo"]
        sc = data.get("mimiciv_core", (set(),set()))[0]
        sn = data.get("mimic_iv_note", (set(),set()))[0]
        rows.append({
            "dataset":"ECG__AND__ECHO__AND__CORE",
            "anchor_found":True,
            "records":0,
            "unique_subjects":len(se & sx & sc),
            "unique_admissions":0,
        })
        rows.append({
            "dataset":"ECG__AND__ECHO__AND__CORE__AND__NOTE",
            "anchor_found":True,
            "records":0,
            "unique_subjects":len(se & sx & sc & sn),
            "unique_admissions":0,
        })

    safe_write_csv(pd.DataFrame(rows), out / "cardiac_linkage.csv")


if __name__ == "__main__":
    main()
