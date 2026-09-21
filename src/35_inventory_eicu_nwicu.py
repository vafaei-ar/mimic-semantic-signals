from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path

import pandas as pd


PRESSOR_TERMS = [
    "norepinephrine", "noradrenaline", "levophed",
    "epinephrine", "adrenaline",
    "vasopressin", "dopamine", "phenylephrine", "neosynephrine",
]

VITAL_TERMS = [
    "heart rate", "pulse", "map", "mean arterial", "systolic", "diastolic",
    "spo2", "oxygen saturation", "respiratory rate", "resp rate",
    "temperature", "urine",
]

LAB_TERMS = ["lactate", "creatinine", "wbc", "white blood"]


def find_one(root: Path, name: str) -> Path | None:
    hits = list(root.rglob(name))
    return hits[0] if hits else None


def read_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def count_rows(path: Path, chunksize: int = 250_000) -> int:
    total = 0
    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        total += len(chunk)
    return total


def contains_any(series: pd.Series, terms: list[str]) -> pd.Series:
    pattern = "|".join(re.escape(x) for x in terms)
    return series.astype(str).str.contains(pattern, case=False, regex=True, na=False)


def scan_eicu(eicu_root: Path) -> dict:
    names = [
        "patient.csv.gz", "infusionDrug.csv.gz", "vitalPeriodic.csv.gz",
        "vitalAperiodic.csv.gz", "lab.csv.gz", "note.csv.gz",
    ]
    paths = {name: find_one(eicu_root, name) for name in names}
    out = {"tables": {}}

    for name, path in paths.items():
        if path is None:
            out["tables"][name] = {"exists": False}
            continue
        out["tables"][name] = {
            "exists": True,
            "path": str(path.relative_to(eicu_root)),
            "columns": read_header(path),
        }

    p = paths.get("patient.csv.gz")
    if p:
        df = pd.read_csv(
            p,
            usecols=lambda c: c in {
                "patientunitstayid", "patienthealthsystemstayid",
                "hospitalid", "unitadmittime24", "unitdischargeoffset",
            },
            low_memory=False,
        )
        out["patients"] = {
            "icu_stays": int(df["patientunitstayid"].nunique())
            if "patientunitstayid" in df else None,
            "health_system_stays": int(df["patienthealthsystemstayid"].nunique())
            if "patienthealthsystemstayid" in df else None,
            "hospitals": int(df["hospitalid"].nunique())
            if "hospitalid" in df else None,
        }

    p = paths.get("infusionDrug.csv.gz")
    if p:
        header = read_header(p)
        drug_col = next((c for c in header if c.lower() in {"drugname", "drug"}), None)
        stay_col = next((c for c in header if c.lower() == "patientunitstayid"), None)
        offset_col = next((c for c in header if "offset" in c.lower()), None)
        match_rows = 0
        stays = set()
        values = {}
        for chunk in pd.read_csv(
            p,
            chunksize=200_000,
            usecols=lambda c: c in {x for x in [drug_col, stay_col, offset_col] if x},
            low_memory=False,
        ):
            if drug_col is None:
                break
            m = contains_any(chunk[drug_col], PRESSOR_TERMS)
            q = chunk.loc[m]
            match_rows += len(q)
            if stay_col and stay_col in q:
                stays.update(pd.to_numeric(q[stay_col], errors="coerce").dropna().astype("int64").tolist())
            for value, n in q[drug_col].dropna().astype(str).value_counts().items():
                values[value] = values.get(value, 0) + int(n)
        out["pressor_infusion_audit"] = {
            "drug_column": drug_col,
            "stay_column": stay_col,
            "time_column_candidate": offset_col,
            "matched_rows": int(match_rows),
            "unique_icu_stays": int(len(stays)),
            "matched_drug_values": [
                {"value": k, "rows": v}
                for k, v in sorted(values.items(), key=lambda x: -x[1])[:100]
            ],
        }

    return out


def scan_nwicu(nw_root: Path) -> dict:
    names = [
        "patients.csv.gz", "admissions.csv.gz", "icustays.csv.gz",
        "emar.csv.gz", "prescriptions.csv.gz", "chartevents.csv.gz",
        "d_items.csv.gz", "labevents.csv.gz", "d_labitems.csv.gz",
        "procedureevents.csv.gz",
    ]
    paths = {name: find_one(nw_root, name) for name in names}
    out = {"tables": {}}
    for name, path in paths.items():
        if path is None:
            out["tables"][name] = {"exists": False}
            continue
        out["tables"][name] = {
            "exists": True,
            "path": str(path.relative_to(nw_root)),
            "columns": read_header(path),
        }

    p = paths.get("icustays.csv.gz")
    if p:
        df = pd.read_csv(
            p,
            usecols=lambda c: c in {"subject_id", "hadm_id", "stay_id", "intime", "outtime"},
            low_memory=False,
        )
        out["patients"] = {
            "subjects": int(df["subject_id"].nunique()) if "subject_id" in df else None,
            "admissions": int(df["hadm_id"].nunique()) if "hadm_id" in df else None,
            "icu_stays": int(df["stay_id"].nunique()) if "stay_id" in df else None,
        }

    p = paths.get("emar.csv.gz")
    if p:
        header = read_header(p)
        med_col = next((c for c in header if c.lower() == "medication"), None)
        event_col = next((c for c in header if c.lower() == "event_txt"), None)
        subject_col = next((c for c in header if c.lower() == "subject_id"), None)
        hadm_col = next((c for c in header if c.lower() == "hadm_id"), None)
        time_col = next((c for c in header if c.lower() in {"charttime", "scheduletime"}), None)
        match_rows = 0
        subjects = set()
        admissions = set()
        med_values = {}
        event_values = {}
        use = {x for x in [med_col, event_col, subject_col, hadm_col, time_col] if x}
        for chunk in pd.read_csv(
            p,
            chunksize=200_000,
            usecols=lambda c: c in use,
            low_memory=False,
        ):
            if med_col is None:
                break
            m = contains_any(chunk[med_col], PRESSOR_TERMS)
            q = chunk.loc[m]
            match_rows += len(q)
            if subject_col and subject_col in q:
                subjects.update(pd.to_numeric(q[subject_col], errors="coerce").dropna().astype("int64").tolist())
            if hadm_col and hadm_col in q:
                admissions.update(pd.to_numeric(q[hadm_col], errors="coerce").dropna().astype("int64").tolist())
            for value, n in q[med_col].dropna().astype(str).value_counts().items():
                med_values[value] = med_values.get(value, 0) + int(n)
            if event_col and event_col in q:
                for value, n in q[event_col].dropna().astype(str).value_counts().items():
                    event_values[value] = event_values.get(value, 0) + int(n)
        out["pressor_emar_audit"] = {
            "medication_column": med_col,
            "event_column": event_col,
            "subject_column": subject_col,
            "admission_column": hadm_col,
            "time_column_candidate": time_col,
            "matched_rows": int(match_rows),
            "unique_subjects": int(len(subjects)),
            "unique_admissions": int(len(admissions)),
            "matched_medication_values": [
                {"value": k, "rows": v}
                for k, v in sorted(med_values.items(), key=lambda x: -x[1])[:100]
            ],
            "matched_event_values": [
                {"value": k, "rows": v}
                for k, v in sorted(event_values.items(), key=lambda x: -x[1])[:50]
            ],
        }

    p = paths.get("d_items.csv.gz")
    if p:
        df = pd.read_csv(p, low_memory=False)
        label_col = next((c for c in df.columns if c.lower() == "label"), None)
        item_col = next((c for c in df.columns if c.lower() == "itemid"), None)
        if label_col:
            m = contains_any(df[label_col], VITAL_TERMS)
            cols = [x for x in [item_col, label_col] if x]
            out["candidate_vital_items"] = df.loc[m, cols].drop_duplicates().head(300).to_dict("records")

    p = paths.get("d_labitems.csv.gz")
    if p:
        df = pd.read_csv(p, low_memory=False)
        label_col = next((c for c in df.columns if c.lower() == "label"), None)
        item_col = next((c for c in df.columns if c.lower() == "itemid"), None)
        if label_col:
            m = contains_any(df[label_col], LAB_TERMS)
            cols = [x for x in [item_col, label_col] if x]
            out["candidate_lab_items"] = df.loc[m, cols].drop_duplicates().head(200).to_dict("records")

    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Safe schema and vasopressor audit for downloaded eICU and NWICU datasets."
    )
    ap.add_argument("--eicu-root", required=True)
    ap.add_argument("--nwicu-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    eicu_root = Path(args.eicu_root).expanduser().resolve()
    nw_root = Path(args.nwicu_root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "eicu": scan_eicu(eicu_root),
        "nwicu": scan_nwicu(nw_root),
    }
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
