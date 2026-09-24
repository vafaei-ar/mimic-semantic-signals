from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030"]

PRESSOR_PATTERNS = {
    "norepinephrine": [r"norepinephrine", r"noradrenaline", r"levophed", r"去甲肾上腺素"],
    "epinephrine": [
        r"(?<!nor)(?<!deoxy)epinephrine",
        r"(?<!nor)adrenaline",
        r"(?<!去甲)(?<!去氧)肾上腺素",
    ],
    "dopamine": [r"dopamine", r"多巴胺"],
    "vasopressin": [r"vasopressin", r"血管加压素"],
    "phenylephrine": [r"phenylephrine", r"deoxyepinephrine", r"去氧肾上腺素", r"苯肾上腺素"],
}
ADMIN_CUES = [
    r"泵入", r"微泵", r"静脉泵", r"静滴", r"静脉滴注", r"输注", r"给予",
    r"予以", r"予", r"使用", r"维持", r"持续", r"滴速", r"ml/?h",
    r"ml/小时", r"(?:ug|μg|mcg)/kg/min", r"(?:ug|μg|mcg)/min",
]
NEGATION_OR_PLAN_CUES = [r"未用", r"未使用", r"未予", r"停用", r"停", r"拟", r"计划", r"考虑"]


def compile_patterns(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


PRESSOR_RX = {name: compile_patterns(pats) for name, pats in PRESSOR_PATTERNS.items()}
ANY_PRESSOR_RX = compile_patterns([p for pats in PRESSOR_PATTERNS.values() for p in pats])
ADMIN_RX = compile_patterns(ADMIN_CUES)
NEG_PLAN_RX = compile_patterns(NEGATION_OR_PLAN_CUES)


def read_csv_robust(path: Path, **kwargs) -> pd.DataFrame:
    last = None
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError as exc:
            last = exc
    if last is not None:
        raise last
    return pd.read_csv(path, **kwargs)


def iter_csv_robust(path: Path, chunksize: int, **kwargs):
    last = None
    for enc in CSV_ENCODINGS:
        first = True
        try:
            reader = pd.read_csv(path, encoding=enc, chunksize=chunksize, **kwargs)
            for chunk in reader:
                first = False
                yield chunk
            return
        except UnicodeDecodeError as exc:
            if not first:
                raise
            last = exc
    if last is not None:
        raise last


def discover_csvs(root: Path) -> dict[str, Path]:
    csvs = [p for p in root.rglob("*.csv") if not p.name.startswith("._")]
    if not csvs:
        archives = sorted(root.rglob("DataTables.zip"))
        if len(archives) != 1:
            raise RuntimeError("Expected one DataTables.zip under --root.")
        archive = archives[0]
        extract_dir = archive.parent / "_inventory_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "r") as zf:
            base = extract_dir.resolve()
            for member in zf.infolist():
                target = (extract_dir / member.filename).resolve()
                try:
                    target.relative_to(base)
                except ValueError as exc:
                    raise RuntimeError(f"Unsafe archive path: {member.filename}") from exc
            zf.extractall(extract_dir)
        csvs = [p for p in extract_dir.rglob("*.csv") if not p.name.startswith("._")]
    return {p.name.lower(): p for p in csvs}


def qstats(values) -> dict:
    x = pd.Series(values, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if x.empty:
        return {"n": 0, "p05": None, "p25": None, "median": None, "p75": None, "p95": None}
    return {
        "n": int(len(x)),
        "p05": float(x.quantile(0.05)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p95": float(x.quantile(0.95)),
    }


def relevant_dictionary_rows(path: Path) -> list[dict]:
    df = read_csv_robust(path, low_memory=False)
    if not {"table_name", "column_name", "description"}.issubset(df.columns):
        return []
    table_norm = df["table_name"].astype(str).str.lower()
    col_norm = df["column_name"].astype(str).str.lower()
    wanted = (
        ((table_norm == "dtnursingchart") & col_norm.isin(["charttime", "nursing_desc"]))
        | ((table_norm == "dtdrugs") & col_norm.isin(["drug_time", "drugname"]))
        | ((table_norm == "dttransfer") & col_norm.isin(["starttime", "stoptime", "transferdept"]))
        | ((table_norm == "dtbaseline") & col_norm.isin(["icu_discharge_time", "discharge_date_time"]))
    )
    out = []
    for row in df.loc[wanted, ["table_name", "column_name", "description"]].itertuples(index=False):
        out.append({
            "table_name": str(row.table_name),
            "column_name": str(row.column_name),
            "description": str(row.description),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate Zigong nursing-clock alignment diagnostic.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    files = discover_csvs(root)

    required = ["dtbaseline.csv", "dtdrugs.csv", "dtnursingchart.csv", "datdictionary.csv"]
    missing = [x for x in required if x not in files]
    if missing:
        raise RuntimeError(f"Missing required Zigong tables: {missing}")

    baseline = read_csv_robust(
        files["dtbaseline.csv"],
        usecols=lambda c: c in {"PATIENT_ID", "INP_NO"},
        low_memory=False,
    )
    baseline["PATIENT_ID"] = pd.to_numeric(baseline["PATIENT_ID"], errors="coerce")
    baseline["INP_NO"] = pd.to_numeric(baseline["INP_NO"], errors="coerce")
    baseline = baseline.dropna(subset=["PATIENT_ID", "INP_NO"]).copy()
    baseline["PATIENT_ID"] = baseline["PATIENT_ID"].astype("int64")
    baseline["INP_NO"] = baseline["INP_NO"].astype("int64")
    inp_to_patient = dict(zip(baseline["INP_NO"], baseline["PATIENT_ID"]))

    order_groups: dict[tuple[int, str], list[float]] = defaultdict(list)
    for chunk in iter_csv_robust(
        files["dtdrugs.csv"],
        chunksize=200_000,
        usecols=lambda c: c in {"PATIENT_ID", "DrugName", "Drug_time"},
        low_memory=False,
    ):
        chunk["PATIENT_ID"] = pd.to_numeric(chunk["PATIENT_ID"], errors="coerce")
        chunk["Drug_time"] = pd.to_numeric(chunk["Drug_time"], errors="coerce")
        chunk = chunk.dropna(subset=["PATIENT_ID", "DrugName", "Drug_time"])
        if chunk.empty:
            continue
        chunk["PATIENT_ID"] = chunk["PATIENT_ID"].astype("int64")
        names = chunk["DrugName"].astype(str)
        mask = names.str.contains(ANY_PRESSOR_RX, regex=True, na=False)
        p = chunk.loc[mask].copy()
        if p.empty:
            continue
        for agent, rx in PRESSOR_RX.items():
            m = p["DrugName"].astype(str).str.contains(rx, regex=True, na=False)
            for row in p.loc[m, ["PATIENT_ID", "Drug_time"]].itertuples(index=False):
                order_groups[(int(row.PATIENT_ID), agent)].append(float(row.Drug_time))

    order_arrays = {k: np.sort(np.asarray(v, dtype=float)) for k, v in order_groups.items()}

    first_admin: dict[tuple[int, str], float] = {}
    strict_rows = 0
    for chunk in iter_csv_robust(
        files["dtnursingchart.csv"],
        chunksize=100_000,
        usecols=lambda c: c in {"INP_NO", "NURSING_DESC", "ChartTime"},
        low_memory=False,
    ):
        chunk["INP_NO"] = pd.to_numeric(chunk["INP_NO"], errors="coerce")
        chunk["ChartTime"] = pd.to_numeric(chunk["ChartTime"], errors="coerce")
        chunk = chunk.dropna(subset=["INP_NO", "NURSING_DESC", "ChartTime"])
        if chunk.empty:
            continue
        chunk["INP_NO"] = chunk["INP_NO"].astype("int64")
        desc = chunk["NURSING_DESC"].astype(str)
        p_mask = desc.str.contains(ANY_PRESSOR_RX, regex=True, na=False)
        if not p_mask.any():
            continue
        p = chunk.loc[p_mask].copy()
        pdesc = p["NURSING_DESC"].astype(str)
        admin = pdesc.str.contains(ADMIN_RX, regex=True, na=False)
        neg = pdesc.str.contains(NEG_PLAN_RX, regex=True, na=False)
        p = p.loc[admin & ~neg].copy()
        if p.empty:
            continue
        strict_rows += len(p)
        pdesc = p["NURSING_DESC"].astype(str)
        for agent, rx in PRESSOR_RX.items():
            m = pdesc.str.contains(rx, regex=True, na=False)
            for row in p.loc[m, ["INP_NO", "ChartTime"]].itertuples(index=False):
                patient = inp_to_patient.get(int(row.INP_NO))
                if patient is None:
                    continue
                key = (int(patient), agent)
                t = float(row.ChartTime)
                old = first_admin.get(key)
                if old is None or t < old:
                    first_admin[key] = t

    pairs = []
    for key, nursing_time in first_admin.items():
        arr = order_arrays.get(key)
        if arr is None or len(arr) == 0:
            continue
        pairs.append((key[1], float(nursing_time), arr))

    if not pairs:
        raise RuntimeError("No same-agent nursing/order pairs available for clock alignment.")

    def evaluate_shift(shift: float) -> dict:
        signed = []
        absolute = []
        by_agent = defaultdict(list)
        for agent, nursing_time, arr in pairs:
            shifted = nursing_time + shift
            d = shifted - arr
            nearest = float(d[np.argmin(np.abs(d))])
            signed.append(nearest)
            absolute.append(abs(nearest))
            by_agent[agent].append(nearest)
        a = np.asarray(absolute, dtype=float)
        s = np.asarray(signed, dtype=float)
        return {
            "shift_hours_added_to_nursing": float(shift),
            "n_pairs": int(len(a)),
            "median_absolute_nearest_order_hours": float(np.median(a)),
            "p75_absolute_nearest_order_hours": float(np.quantile(a, 0.75)),
            "median_signed_nearest_order_hours": float(np.median(s)),
            "within_1h": int(np.sum(a <= 1.0)),
            "within_6h": int(np.sum(a <= 6.0)),
            "within_12h": int(np.sum(a <= 12.0)),
            "fraction_within_1h": float(np.mean(a <= 1.0)),
            "fraction_within_6h": float(np.mean(a <= 6.0)),
            "fraction_within_12h": float(np.mean(a <= 12.0)),
        }

    scan = [evaluate_shift(float(x)) for x in range(-48, 49)]
    best = min(
        scan,
        key=lambda x: (
            x["median_absolute_nearest_order_hours"],
            -x["fraction_within_6h"],
            abs(x["shift_hours_added_to_nursing"]),
        ),
    )
    selected_offsets = {-48, -36, -24, -12, 0, 12, 24, 36, 48, int(best["shift_hours_added_to_nursing"])}
    selected = [x for x in scan if int(x["shift_hours_added_to_nursing"]) in selected_offsets]

    raw_first_admin_times = [x[1] for x in pairs]
    report = {
        "dataset": "Zigong Fourth People's Hospital critical care infection database v1.1",
        "analysis": "Aggregate nursing-clock alignment diagnostic before endpoint freeze",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "dictionary_rows": relevant_dictionary_rows(files["datdictionary.csv"]),
        "strict_admin_like_nursing_rows_scanned": int(strict_rows),
        "first_admin_same_agent_order_pairs": int(len(pairs)),
        "raw_first_admin_time_hours": qstats(raw_first_admin_times),
        "candidate_shift_scan_definition": (
            "Add each integer offset from -48 to +48 hours to the first high-specificity "
            "same-agent nursing administration-like time, then measure distance to the nearest "
            "same-agent physician order for that patient. This is a clock diagnostic, not an endpoint."
        ),
        "selected_shift_summaries": selected,
        "best_shift_by_median_absolute_nearest_order": best,
        "guardrail": (
            "Do not build an incident vasopressor cohort from nursing ChartTime until a clock rule "
            "is frozen. A shift is not automatically accepted merely because it optimizes order alignment."
        ),
    }
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
