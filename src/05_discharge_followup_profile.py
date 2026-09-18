from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root, safe_write_csv


def _summary_hadm_ids(note_file: Path) -> set[int]:
    out: set[int] = set()
    reader = read_columns(note_file, ["hadm_id"], chunksize=250_000)
    for chunk in reader:
        c = lower_columns(chunk)
        vals = pd.to_numeric(c["hadm_id"], errors="coerce").dropna().astype("int64")
        out.update(vals.tolist())
    return out


def _next_ed_days(index: pd.DataFrame, ed: pd.DataFrame) -> np.ndarray:
    ed_by_subject = {}
    for sid, g in ed.dropna(subset=["subject_id","intime"]).groupby("subject_id"):
        arr = np.sort(g["intime"].to_numpy(dtype="datetime64[ns]"))
        ed_by_subject[int(sid)] = arr

    result = np.full(len(index), np.nan)
    for pos, row in enumerate(index[["subject_id","dischtime"]].itertuples(index=False)):
        if pd.isna(row.subject_id) or pd.isna(row.dischtime):
            continue
        arr = ed_by_subject.get(int(row.subject_id))
        if arr is None or len(arr) == 0:
            continue
        t = np.datetime64(row.dischtime.to_datetime64())
        k = np.searchsorted(arr, t, side="right")
        if k < len(arr):
            result[pos] = float((arr[k] - t) / np.timedelta64(1, "D"))
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = resolve_root(args.root)
    out = Path(args.output)

    note_file = find_file(module_path(root, "mimic_iv_note"), ["discharge.csv.gz","discharge.csv"])
    admissions_file = find_file(module_path(root, "mimiciv"), ["admissions.csv.gz","admissions.csv"])
    ed_file = find_file(module_path(root, "mimic_iv_ed"), ["edstays.csv.gz","edstays.csv"])

    if note_file is None or admissions_file is None:
        safe_write_csv(pd.DataFrame([{"status":"insufficient_data"}]), out / "discharge_followup.csv")
        return

    summary_hadm = _summary_hadm_ids(note_file)
    adm = lower_columns(pd.read_csv(admissions_file, low_memory=False))
    needed = ["subject_id","hadm_id","admittime","dischtime"]
    if any(c not in adm.columns for c in needed):
        safe_write_csv(pd.DataFrame([{"status":"required_columns_missing"}]), out / "discharge_followup.csv")
        return

    adm["subject_id"] = pd.to_numeric(adm["subject_id"], errors="coerce")
    adm["hadm_id"] = pd.to_numeric(adm["hadm_id"], errors="coerce")
    adm["admittime"] = parse_datetime(adm["admittime"])
    adm["dischtime"] = parse_datetime(adm["dischtime"])
    adm = adm.dropna(subset=["subject_id","hadm_id","admittime","dischtime"]).copy()
    adm["subject_id"] = adm["subject_id"].astype("int64")
    adm["hadm_id"] = adm["hadm_id"].astype("int64")
    adm = adm.sort_values(["subject_id","admittime"])
    adm["next_admittime"] = adm.groupby("subject_id")["admittime"].shift(-1)
    adm["days_to_next_admission"] = (adm["next_admittime"] - adm["dischtime"]).dt.total_seconds() / 86400

    index = adm[adm["hadm_id"].isin(summary_hadm)].copy()
    index = index[index["days_to_next_admission"].isna() | (index["days_to_next_admission"] > 0)].copy()

    if ed_file is not None:
        ed = lower_columns(pd.read_csv(ed_file, low_memory=False))
        if "subject_id" in ed and "intime" in ed:
            ed["subject_id"] = pd.to_numeric(ed["subject_id"], errors="coerce")
            ed["intime"] = parse_datetime(ed["intime"])
            index["days_to_next_ed"] = _next_ed_days(index.reset_index(drop=True), ed)
        else:
            index["days_to_next_ed"] = np.nan
    else:
        index["days_to_next_ed"] = np.nan

    n = len(index)
    rows = [{
        "status":"ok",
        "discharge_summaries_linked_to_admissions": n,
        "unique_subjects": int(index["subject_id"].nunique()),
        "hospital_readmission_7d_n": int(((index["days_to_next_admission"] > 0) & (index["days_to_next_admission"] <= 7)).sum()),
        "hospital_readmission_7d_pct": round(100 * ((index["days_to_next_admission"] > 0) & (index["days_to_next_admission"] <= 7)).mean(), 3) if n else 0.0,
        "hospital_readmission_30d_n": int(((index["days_to_next_admission"] > 0) & (index["days_to_next_admission"] <= 30)).sum()),
        "hospital_readmission_30d_pct": round(100 * ((index["days_to_next_admission"] > 0) & (index["days_to_next_admission"] <= 30)).mean(), 3) if n else 0.0,
        "ed_return_7d_n": int(((index["days_to_next_ed"] > 0) & (index["days_to_next_ed"] <= 7)).sum()),
        "ed_return_7d_pct": round(100 * ((index["days_to_next_ed"] > 0) & (index["days_to_next_ed"] <= 7)).mean(), 3) if n else 0.0,
        "ed_return_30d_n": int(((index["days_to_next_ed"] > 0) & (index["days_to_next_ed"] <= 30)).sum()),
        "ed_return_30d_pct": round(100 * ((index["days_to_next_ed"] > 0) & (index["days_to_next_ed"] <= 30)).mean(), 3) if n else 0.0,
    }]
    safe_write_csv(pd.DataFrame(rows), out / "discharge_followup.csv")


if __name__ == "__main__":
    main()
