from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030"]

PRESSOR_PATTERNS = {
    "norepinephrine": [
        r"norepinephrine",
        r"noradrenaline",
        r"levophed",
        r"去甲肾上腺素",
    ],
    "epinephrine": [
        r"epinephrine",
        r"adrenaline",
        r"(?<!去甲)(?<!去氧)肾上腺素",
    ],
    "dopamine": [
        r"dopamine",
        r"多巴胺",
    ],
    "vasopressin": [
        r"vasopressin",
        r"血管加压素",
    ],
    "phenylephrine": [
        r"phenylephrine",
        r"deoxyepinephrine",
        r"去氧肾上腺素",
        r"苯肾上腺素",
    ],
}

ADMIN_CUES = [
    r"泵入",
    r"微泵",
    r"静脉泵",
    r"静滴",
    r"静脉滴注",
    r"输注",
    r"给予",
    r"予以",
    r"予",
    r"使用",
    r"维持",
    r"持续",
    r"滴速",
    r"ml/?h",
    r"ml/小时",
    r"(?:ug|μg|mcg)/kg/min",
    r"(?:ug|μg|mcg)/min",
]

NEGATION_OR_PLAN_CUES = [
    r"未用",
    r"未使用",
    r"未予",
    r"停用",
    r"停",
    r"拟",
    r"计划",
    r"考虑",
]


def read_csv_robust(path: Path, **kwargs) -> pd.DataFrame:
    last_error = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.read_csv(path, **kwargs)


def iter_csv_robust(path: Path, chunksize: int, **kwargs):
    last_error = None
    for encoding in CSV_ENCODINGS:
        first = True
        try:
            reader = pd.read_csv(
                path,
                encoding=encoding,
                chunksize=chunksize,
                **kwargs,
            )
            for chunk in reader:
                first = False
                yield chunk
            return
        except UnicodeDecodeError as exc:
            if not first:
                raise
            last_error = exc
    if last_error is not None:
        raise last_error


def discover_csvs(root: Path) -> dict[str, Path]:
    csvs = [
        p for p in root.rglob("*.csv")
        if not p.name.startswith("._")
    ]
    if not csvs:
        archives = sorted(root.rglob("DataTables.zip"))
        if not archives:
            raise RuntimeError(f"No CSV files or DataTables.zip found under {root}")
        if len(archives) > 1:
            raise RuntimeError("Multiple DataTables.zip archives found; narrow --root.")
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
                    raise RuntimeError(
                        f"Unsafe archive path: {member.filename}"
                    ) from exc
            zf.extractall(extract_dir)
        csvs = [
            p for p in extract_dir.rglob("*.csv")
            if not p.name.startswith("._")
        ]
    return {p.name.lower(): p for p in csvs}


def compile_patterns(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), flags=re.IGNORECASE)


PRESSOR_RX = {
    name: compile_patterns(patterns)
    for name, patterns in PRESSOR_PATTERNS.items()
}
ANY_PRESSOR_RX = compile_patterns(
    [p for pats in PRESSOR_PATTERNS.values() for p in pats]
)
ADMIN_RX = compile_patterns(ADMIN_CUES)
NEG_PLAN_RX = compile_patterns(NEGATION_OR_PLAN_CUES)


def numeric_time(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def quantiles(values: pd.Series) -> dict:
    x = pd.to_numeric(values, errors="coerce").dropna()
    if x.empty:
        return {
            "n": 0,
            "median": None,
            "p25": None,
            "p75": None,
            "p05": None,
            "p95": None,
        }
    return {
        "n": int(len(x)),
        "median": float(x.median()),
        "p25": float(x.quantile(0.25)),
        "p75": float(x.quantile(0.75)),
        "p05": float(x.quantile(0.05)),
        "p95": float(x.quantile(0.95)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Audit candidate vasopressor start definitions in the Zigong database "
            "using aggregate order/nursing-note timing only."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    files = discover_csvs(root)
    required = ["dtbaseline.csv", "dtdrugs.csv", "dtnursingchart.csv"]
    missing = [name for name in required if name not in files]
    if missing:
        raise RuntimeError(f"Missing required Zigong tables: {missing}")

    baseline = read_csv_robust(
        files["dtbaseline.csv"],
        usecols=lambda c: c in {"PATIENT_ID", "INP_NO"},
        low_memory=False,
    )
    baseline["PATIENT_ID"] = pd.to_numeric(
        baseline["PATIENT_ID"], errors="coerce"
    )
    baseline["INP_NO"] = pd.to_numeric(
        baseline["INP_NO"], errors="coerce"
    )
    baseline = baseline.dropna(subset=["PATIENT_ID", "INP_NO"]).copy()
    baseline["PATIENT_ID"] = baseline["PATIENT_ID"].astype("int64")
    baseline["INP_NO"] = baseline["INP_NO"].astype("int64")

    inp_to_patient = dict(
        zip(baseline["INP_NO"], baseline["PATIENT_ID"])
    )

    # Drug-order audit.
    drug_rows = []
    drug_name_counts = Counter()
    drug_patient_counts = Counter()

    for chunk in iter_csv_robust(
        files["dtdrugs.csv"],
        chunksize=200_000,
        usecols=lambda c: c in {"PATIENT_ID", "DrugName", "Drug_time", "Formula"},
        low_memory=False,
    ):
        chunk["PATIENT_ID"] = pd.to_numeric(
            chunk["PATIENT_ID"], errors="coerce"
        )
        chunk["Drug_time"] = numeric_time(chunk["Drug_time"])
        chunk = chunk.dropna(subset=["PATIENT_ID", "DrugName", "Drug_time"])
        if chunk.empty:
            continue
        chunk["PATIENT_ID"] = chunk["PATIENT_ID"].astype("int64")
        names = chunk["DrugName"].astype(str)

        mask = names.str.contains(ANY_PRESSOR_RX, regex=True, na=False)
        p = chunk[mask].copy()
        if p.empty:
            continue

        p["agent"] = "other"
        for agent, rx in PRESSOR_RX.items():
            m = p["DrugName"].astype(str).str.contains(rx, regex=True, na=False)
            p.loc[m, "agent"] = agent

        for row in p[["PATIENT_ID", "Drug_time", "DrugName", "agent"]].itertuples(index=False):
            drug_rows.append(
                {
                    "patient_id": int(row.PATIENT_ID),
                    "time": float(row.Drug_time),
                    "agent": str(row.agent),
                }
            )
            drug_name_counts[str(row.DrugName)] += 1
            drug_patient_counts[str(row.agent)] += 1

    drug_df = pd.DataFrame(drug_rows)
    if not drug_df.empty:
        first_order = (
            drug_df.sort_values("time")
            .groupby("patient_id", as_index=False)
            .first()
            .rename(columns={"time": "first_order_time"})
        )
    else:
        first_order = pd.DataFrame(
            columns=["patient_id", "first_order_time", "agent"]
        )

    # Nursing-note audit. Never save note text.
    first_any: dict[int, float] = {}
    first_admin: dict[int, float] = {}
    any_rows = 0
    admin_rows = 0
    neg_plan_rows = 0
    agent_any_counts = Counter()
    agent_admin_counts = Counter()

    for chunk in iter_csv_robust(
        files["dtnursingchart.csv"],
        chunksize=100_000,
        usecols=lambda c: c in {"INP_NO", "NURSING_DESC", "ChartTime"},
        low_memory=False,
    ):
        chunk["INP_NO"] = pd.to_numeric(chunk["INP_NO"], errors="coerce")
        chunk["ChartTime"] = numeric_time(chunk["ChartTime"])
        chunk = chunk.dropna(subset=["INP_NO", "ChartTime", "NURSING_DESC"])
        if chunk.empty:
            continue

        chunk["INP_NO"] = chunk["INP_NO"].astype("int64")
        desc = chunk["NURSING_DESC"].astype(str)

        pressor_mask = desc.str.contains(ANY_PRESSOR_RX, regex=True, na=False)
        if not pressor_mask.any():
            continue

        p = chunk[pressor_mask].copy()
        pdesc = p["NURSING_DESC"].astype(str)
        any_rows += int(len(p))

        admin_mask = pdesc.str.contains(ADMIN_RX, regex=True, na=False)
        neg_plan_mask = pdesc.str.contains(NEG_PLAN_RX, regex=True, na=False)
        admin_high_specificity = admin_mask & ~neg_plan_mask

        admin_rows += int(admin_high_specificity.sum())
        neg_plan_rows += int(neg_plan_mask.sum())

        for agent, rx in PRESSOR_RX.items():
            m = pdesc.str.contains(rx, regex=True, na=False)
            agent_any_counts[agent] += int(m.sum())
            agent_admin_counts[agent] += int((m & admin_high_specificity).sum())

        for row in p[["INP_NO", "ChartTime"]].itertuples(index=False):
            patient = inp_to_patient.get(int(row.INP_NO))
            if patient is None:
                continue
            t = float(row.ChartTime)
            old = first_any.get(patient)
            if old is None or t < old:
                first_any[patient] = t

        pa = p[admin_high_specificity]
        for row in pa[["INP_NO", "ChartTime"]].itertuples(index=False):
            patient = inp_to_patient.get(int(row.INP_NO))
            if patient is None:
                continue
            t = float(row.ChartTime)
            old = first_admin.get(patient)
            if old is None or t < old:
                first_admin[patient] = t

    any_df = pd.DataFrame(
        [{"patient_id": k, "first_note_pressor_time": v} for k, v in first_any.items()]
    )
    admin_df = pd.DataFrame(
        [{"patient_id": k, "first_admin_like_note_time": v} for k, v in first_admin.items()]
    )

    compare = first_order[["patient_id", "first_order_time"]].copy()
    compare = compare.merge(any_df, on="patient_id", how="outer")
    compare = compare.merge(admin_df, on="patient_id", how="outer")

    if not compare.empty:
        compare["admin_minus_order_h"] = (
            compare["first_admin_like_note_time"] - compare["first_order_time"]
        )
        compare["any_note_minus_order_h"] = (
            compare["first_note_pressor_time"] - compare["first_order_time"]
        )

    both_admin = compare.dropna(
        subset=["first_order_time", "first_admin_like_note_time"]
    )
    both_any = compare.dropna(
        subset=["first_order_time", "first_note_pressor_time"]
    )

    windows = {}
    if not both_admin.empty:
        delta = both_admin["admin_minus_order_h"]
        windows = {
            "admin_note_before_order_gt_6h": int((delta < -6).sum()),
            "admin_note_before_order_0_to_6h": int(((delta >= -6) & (delta < 0)).sum()),
            "admin_note_within_0_to_1h_after_order": int(((delta >= 0) & (delta <= 1)).sum()),
            "admin_note_within_1_to_6h_after_order": int(((delta > 1) & (delta <= 6)).sum()),
            "admin_note_gt_6h_after_order": int((delta > 6).sum()),
        }

    report = {
        "dataset": "Zigong Fourth People's Hospital critical care infection database v1.1",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "source_documentation_warning": (
            "dtDrugs is a physician-order table; Drug_time is prescription time "
            "and is not necessarily administration time."
        ),
        "patients_in_baseline": int(baseline["PATIENT_ID"].nunique()),
        "pressor_order_rows": int(len(drug_df)),
        "patients_with_pressor_order": int(first_order["patient_id"].nunique()),
        "first_pressor_order_time_hours": quantiles(
            first_order["first_order_time"]
            if not first_order.empty
            else pd.Series(dtype=float)
        ),
        "pressor_order_agents": (
            drug_df.groupby("agent")["patient_id"].nunique().astype(int).to_dict()
            if not drug_df.empty
            else {}
        ),
        "nursing_pressor_mention_rows": int(any_rows),
        "patients_with_any_nursing_pressor_mention": int(len(first_any)),
        "nursing_admin_like_pressor_rows_high_specificity": int(admin_rows),
        "patients_with_admin_like_nursing_pressor_mention": int(len(first_admin)),
        "nursing_pressor_rows_with_negation_or_plan_cue": int(neg_plan_rows),
        "nursing_any_pressor_mentions_by_agent": dict(agent_any_counts),
        "nursing_admin_like_mentions_by_agent": dict(agent_admin_counts),
        "patients_with_both_order_and_any_nursing_mention": int(len(both_any)),
        "patients_with_both_order_and_admin_like_nursing_mention": int(len(both_admin)),
        "any_nursing_mention_minus_order_hours": quantiles(
            both_any["any_note_minus_order_h"]
            if not both_any.empty
            else pd.Series(dtype=float)
        ),
        "admin_like_nursing_mention_minus_order_hours": quantiles(
            both_admin["admin_minus_order_h"]
            if not both_admin.empty
            else pd.Series(dtype=float)
        ),
        "admin_like_timing_windows_relative_to_order": windows,
        "decision_rule": (
            "If admin-like nursing mentions are common and temporally coherent with "
            "orders, prefer first high-specificity nursing administration mention as "
            "the external endpoint. Otherwise use first pressor order only as a "
            "secondary operational endpoint and state clearly that it is prescription, "
            "not administration."
        ),
    }

    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
