from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


EXPECTED_FILES = [
    "dtBaseline.csv",
    "dtDrugs.csv",
    "dtICD.csv",
    "dtLab.csv",
    "dtTransfer.csv",
    "dtTansfer.csv",
    "dtNursingChart.csv",
    "dtOutcome.csv",
    "dtOutCome.csv",
    "datDictionary.csv",
]

PRESSOR_TERMS = [
    "norepinephrine",
    "noradrenaline",
    "levophed",
    "epinephrine",
    "adrenaline",
    "vasopressin",
    "dopamine",
    "phenylephrine",
    "vasopressor",
    "去甲肾上腺素",
    "肾上腺素",
    "多巴胺",
    "血管加压素",
    "苯肾上腺素",
]

NOTE_HINTS = [
    "note", "progress", "narrative", "text", "record", "desc",
    "记录", "病程", "护理",
]

TIME_HINTS = [
    "time", "hour", "date", "datetime", "offset",
    "时间", "小时",
]

ID_HINTS = ["patient_id", "inp_no", "patient", "subject", "id"]

VALUE_HINTS = [
    "value", "result", "item", "name", "label", "desc", "content",
    "项目", "名称", "结果", "内容",
]


def normalize(s: object) -> str:
    return str(s).strip()


def has_any(text: str, terms: list[str]) -> bool:
    lo = text.lower()
    return any(term.lower() in lo for term in terms)


def safe_row_count(path: Path, chunksize: int = 250_000) -> int:
    total = 0
    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        total += len(chunk)
    return total


def candidate_columns(columns: list[str], hints: list[str]) -> list[str]:
    out = []
    for c in columns:
        if has_any(c, hints):
            out.append(c)
    return out


def chinese_fraction(series: pd.Series, max_values: int = 5000) -> dict:
    vals = series.dropna().astype(str)
    if len(vals) > max_values:
        vals = vals.sample(max_values, random_state=20260920)
    if len(vals) == 0:
        return {"n_sampled": 0, "fraction_with_cjk": None}
    cjk = vals.str.contains(r"[\u3400-\u4dbf\u4e00-\u9fff]", regex=True)
    return {
        "n_sampled": int(len(vals)),
        "fraction_with_cjk": float(cjk.mean()),
    }


def inspect_table(path: Path) -> dict:
    head = pd.read_csv(path, nrows=5000, low_memory=False)
    cols = [normalize(c) for c in head.columns]

    info = {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "columns": cols,
        "candidate_id_columns": candidate_columns(cols, ID_HINTS),
        "candidate_time_columns": candidate_columns(cols, TIME_HINTS),
        "candidate_note_columns": candidate_columns(cols, NOTE_HINTS),
        "candidate_value_columns": candidate_columns(cols, VALUE_HINTS),
    }

    # Only report language statistics, never note text.
    lang = {}
    for c in info["candidate_note_columns"]:
        if c in head.columns:
            lang[c] = chinese_fraction(head[c])
    info["candidate_note_language"] = lang

    # Search safe categorical/string fields for vasopressor terminology. Output
    # only the matched medication/item terms, never arbitrary note excerpts.
    matches = []
    for c in cols:
        if c not in head.columns:
            continue
        if has_any(c, NOTE_HINTS):
            continue
        s = head[c]
        if s.dtype != object:
            continue
        values = s.dropna().astype(str).drop_duplicates()
        for value in values.head(10000):
            if has_any(value, PRESSOR_TERMS):
                matches.append({"column": c, "value": value[:200]})
    info["pressor_term_matches_in_first_5000_rows"] = matches[:200]
    return info


def nursing_deep_scan(path: Path) -> dict:
    header = pd.read_csv(path, nrows=0)
    cols = [normalize(c) for c in header.columns]

    note_cols = candidate_columns(cols, NOTE_HINTS)
    time_cols = candidate_columns(cols, TIME_HINTS)
    id_cols = candidate_columns(cols, ID_HINTS)

    non_note_string_cols = [
        c for c in cols
        if c not in note_cols
    ]

    rows = 0
    note_nonempty = Counter()
    note_cjk = Counter()
    pressor_match_counts = Counter()
    pressor_match_columns = Counter()

    for chunk in pd.read_csv(path, chunksize=100_000, low_memory=False):
        rows += len(chunk)

        for c in note_cols:
            if c not in chunk:
                continue
            s = chunk[c].dropna().astype(str)
            note_nonempty[c] += int((s.str.strip() != "").sum())
            note_cjk[c] += int(
                s.str.contains(r"[\u3400-\u4dbf\u4e00-\u9fff]", regex=True).sum()
            )

        # Search non-note fields for structured event labels/values that name
        # vasopressors. This is safe aggregate reconnaissance and avoids exposing
        # free-text nursing narratives.
        for c in non_note_string_cols:
            if c not in chunk or chunk[c].dtype != object:
                continue
            s = chunk[c].dropna().astype(str)
            if s.empty:
                continue
            lo = s.str.lower()
            mask = pd.Series(False, index=s.index)
            for term in PRESSOR_TERMS:
                mask = mask | lo.str.contains(re.escape(term.lower()), regex=True)
            n = int(mask.sum())
            if n:
                pressor_match_counts[c] += n
                pressor_match_columns[c] += int(s[mask].nunique())

    return {
        "rows": int(rows),
        "columns": cols,
        "candidate_id_columns": id_cols,
        "candidate_time_columns": time_cols,
        "candidate_note_columns": note_cols,
        "note_nonempty_counts": dict(note_nonempty),
        "note_cjk_counts": dict(note_cjk),
        "pressor_structured_match_counts_by_column": dict(pressor_match_counts),
        "pressor_structured_unique_values_by_column": dict(pressor_match_columns),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Inventory the Zigong Fourth People's Hospital critical-care database "
            "without exporting patient identifiers or progress-note text."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if not root.exists():
        raise FileNotFoundError(root)

    csvs = sorted(root.rglob("*.csv"))
    if not csvs:
        raise RuntimeError(f"No CSV files found under {root}")

    tables = []
    for path in csvs:
        info = inspect_table(path)
        try:
            info["rows"] = safe_row_count(path)
        except Exception as exc:
            info["row_count_error"] = str(exc)
        tables.append(info)

    nursing_candidates = [
        p for p in csvs
        if p.name.lower() == "dtnursingchart.csv"
    ]
    nursing_scan = (
        nursing_deep_scan(nursing_candidates[0])
        if nursing_candidates
        else None
    )

    found_names = {p.name for p in csvs}
    expected_status = {
        name: name in found_names
        for name in EXPECTED_FILES
    }

    report = {
        "dataset": "Zigong Fourth People's Hospital critical care infection database",
        "physionet_version_target": "1.1",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "csv_files_found": len(csvs),
        "expected_file_presence": expected_status,
        "tables": tables,
        "nursing_chart_deep_scan": nursing_scan,
        "decision_needed_next": (
            "Use the actual data dictionary and nursing-chart structured event labels "
            "to define vasopressor administration. Do not use dtDrugs prescription time "
            "as administration time unless the dataset proves it is administered."
        ),
    }

    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
