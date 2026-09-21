from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


CSV_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030"]

PRESSOR_RX = re.compile(
    "|".join(
        [
            r"(?:norepinephrine)",
            r"(?:noradrenaline)",
            r"(?:levophed)",
            r"(?:去甲肾上腺素)",
            r"(?:(?<!nor)(?<!deoxy)epinephrine)",
            r"(?:(?<!nor)adrenaline)",
            r"(?:(?<!去甲)(?<!去氧)肾上腺素)",
            r"(?:dopamine)",
            r"(?:多巴胺)",
            r"(?:vasopressin)",
            r"(?:血管加压素)",
            r"(?:phenylephrine)",
            r"(?:deoxyepinephrine)",
            r"(?:去氧肾上腺素)",
            r"(?:苯肾上腺素)",
        ]
    ),
    flags=re.IGNORECASE,
)

ICU_RX = re.compile(
    r"\bICU\b|intensive\s*care|重症|重症监护|重症医学",
    flags=re.IGNORECASE,
)


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


def qstats(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if x.empty:
        return {
            "n": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
        }
    return {
        "n": int(len(x)),
        "min": float(x.min()),
        "p05": float(x.quantile(0.05)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.median()),
        "p75": float(x.quantile(0.75)),
        "p95": float(x.quantile(0.95)),
        "max": float(x.max()),
    }


def first_numeric_time_by_key(
    path: Path,
    key: str,
    time_col: str,
    chunksize: int = 200_000,
    extra_filter=None,
) -> pd.DataFrame:
    parts = []
    for chunk in iter_csv_robust(
        path,
        chunksize=chunksize,
        usecols=lambda c: c in {key, time_col} or (extra_filter is not None and c in extra_filter["columns"]),
        low_memory=False,
    ):
        if extra_filter is not None:
            chunk = extra_filter["apply"](chunk)
        chunk[key] = pd.to_numeric(chunk[key], errors="coerce")
        chunk[time_col] = pd.to_numeric(chunk[time_col], errors="coerce")
        chunk = chunk.dropna(subset=[key, time_col])
        if chunk.empty:
            continue
        g = chunk.groupby(key, as_index=False)[time_col].min()
        parts.append(g)
    if not parts:
        return pd.DataFrame(columns=[key, time_col])
    allg = pd.concat(parts, ignore_index=True)
    return allg.groupby(key, as_index=False)[time_col].min()


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Audit Zigong time origins across nursing, transfer, and medication tables "
            "without exporting note text or patient identifiers."
        )
    )
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    files = discover_csvs(root)
    for name in ["dtbaseline.csv", "dtdrugs.csv", "dtnursingchart.csv", "dttransfer.csv"]:
        if name not in files:
            raise RuntimeError(f"Missing {name}")

    baseline = read_csv_robust(
        files["dtbaseline.csv"],
        usecols=lambda c: c in {
            "PATIENT_ID", "INP_NO", "ICU_discharge_time", "DISCHARGE_DATE_TIME"
        },
        low_memory=False,
    )
    for col in ["PATIENT_ID", "INP_NO", "ICU_discharge_time", "DISCHARGE_DATE_TIME"]:
        baseline[col] = pd.to_numeric(baseline[col], errors="coerce")
    baseline = baseline.dropna(subset=["PATIENT_ID", "INP_NO"]).copy()
    baseline["PATIENT_ID"] = baseline["PATIENT_ID"].astype("int64")
    baseline["INP_NO"] = baseline["INP_NO"].astype("int64")

    inp_to_patient = dict(zip(baseline["INP_NO"], baseline["PATIENT_ID"]))

    nursing_first = first_numeric_time_by_key(
        files["dtnursingchart.csv"], "INP_NO", "ChartTime", chunksize=150_000
    )
    nursing_first["patient_id"] = nursing_first["INP_NO"].map(inp_to_patient)
    nursing_first = nursing_first.dropna(subset=["patient_id"])
    nursing_first["patient_id"] = nursing_first["patient_id"].astype("int64")
    nursing_first = (
        nursing_first.groupby("patient_id", as_index=False)["ChartTime"].min()
        .rename(columns={"ChartTime": "first_nursing_time"})
    )

    any_order_first = first_numeric_time_by_key(
        files["dtdrugs.csv"], "PATIENT_ID", "Drug_time", chunksize=200_000
    ).rename(columns={"PATIENT_ID": "patient_id", "Drug_time": "first_any_order_time"})
    if not any_order_first.empty:
        any_order_first["patient_id"] = any_order_first["patient_id"].astype("int64")

    def pressor_filter(chunk: pd.DataFrame) -> pd.DataFrame:
        if "DrugName" not in chunk:
            return chunk.iloc[0:0]
        return chunk[
            chunk["DrugName"].astype(str).str.contains(PRESSOR_RX, regex=True, na=False)
        ].copy()

    pressor_first = first_numeric_time_by_key(
        files["dtdrugs.csv"],
        "PATIENT_ID",
        "Drug_time",
        chunksize=200_000,
        extra_filter={"columns": {"DrugName"}, "apply": pressor_filter},
    ).rename(columns={"PATIENT_ID": "patient_id", "Drug_time": "first_pressor_order_time"})
    if not pressor_first.empty:
        pressor_first["patient_id"] = pressor_first["patient_id"].astype("int64")

    # Transfer table: inspect department names safely and identify ICU transfers.
    transfer_parts = []
    dept_counts: dict[str, int] = {}
    for chunk in iter_csv_robust(
        files["dttransfer.csv"],
        chunksize=100_000,
        usecols=lambda c: c in {"PATIENT_ID", "INP_NO", "StartTime", "StopTime", "TransferDept"},
        low_memory=False,
    ):
        chunk["PATIENT_ID"] = pd.to_numeric(chunk["PATIENT_ID"], errors="coerce")
        chunk["StartTime"] = pd.to_numeric(chunk["StartTime"], errors="coerce")
        chunk["StopTime"] = pd.to_numeric(chunk["StopTime"], errors="coerce")
        for dept, n in chunk["TransferDept"].dropna().astype(str).value_counts().items():
            dept_counts[str(dept)] = dept_counts.get(str(dept), 0) + int(n)
        mask = chunk["TransferDept"].astype(str).str.contains(ICU_RX, regex=True, na=False)
        t = chunk.loc[mask, ["PATIENT_ID", "StartTime", "StopTime", "TransferDept"]].dropna(
            subset=["PATIENT_ID", "StartTime"]
        )
        if not t.empty:
            transfer_parts.append(t)

    if transfer_parts:
        transfers = pd.concat(transfer_parts, ignore_index=True)
        transfers["PATIENT_ID"] = transfers["PATIENT_ID"].astype("int64")
        icu_first = (
            transfers.sort_values("StartTime")
            .groupby("PATIENT_ID", as_index=False)
            .first()
            .rename(
                columns={
                    "PATIENT_ID": "patient_id",
                    "StartTime": "first_icu_transfer_start",
                    "StopTime": "first_icu_transfer_stop",
                }
            )
        )
    else:
        icu_first = pd.DataFrame(
            columns=[
                "patient_id",
                "first_icu_transfer_start",
                "first_icu_transfer_stop",
                "TransferDept",
            ]
        )

    merged = baseline.rename(columns={"PATIENT_ID": "patient_id"})[
        ["patient_id", "ICU_discharge_time", "DISCHARGE_DATE_TIME"]
    ].copy()
    merged = merged.merge(nursing_first, on="patient_id", how="left")
    merged = merged.merge(any_order_first, on="patient_id", how="left")
    merged = merged.merge(pressor_first, on="patient_id", how="left")
    merged = merged.merge(icu_first, on="patient_id", how="left")

    for col in [
        "first_nursing_time",
        "first_any_order_time",
        "first_pressor_order_time",
        "first_icu_transfer_start",
        "first_icu_transfer_stop",
    ]:
        if col not in merged:
            merged[col] = np.nan

    merged["nursing_minus_icu_start"] = (
        merged["first_nursing_time"] - merged["first_icu_transfer_start"]
    )
    merged["any_order_minus_icu_start"] = (
        merged["first_any_order_time"] - merged["first_icu_transfer_start"]
    )
    merged["pressor_order_minus_icu_start"] = (
        merged["first_pressor_order_time"] - merged["first_icu_transfer_start"]
    )
    merged["nursing_minus_pressor_order"] = (
        merged["first_nursing_time"] - merged["first_pressor_order_time"]
    )

    top_depts = sorted(dept_counts.items(), key=lambda x: (-x[1], x[0]))[:30]

    report = {
        "dataset": "Zigong Fourth People's Hospital critical care infection database v1.1",
        "local_only": True,
        "contains_note_text": False,
        "contains_patient_identifiers": False,
        "source_documentation_time_origin": (
            "all event times are intended to be offsets in hours from hospital admission"
        ),
        "patients": int(merged["patient_id"].nunique()),
        "time_distributions_hours_from_hospital_admission": {
            "first_nursing_chart": qstats(merged["first_nursing_time"]),
            "first_any_drug_order": qstats(merged["first_any_order_time"]),
            "first_pressor_order": qstats(merged["first_pressor_order_time"]),
            "first_icu_transfer_start": qstats(merged["first_icu_transfer_start"]),
            "icu_discharge_time": qstats(merged["ICU_discharge_time"]),
            "hospital_discharge_time": qstats(merged["DISCHARGE_DATE_TIME"]),
        },
        "paired_time_differences_hours": {
            "first_nursing_minus_first_icu_transfer": qstats(
                merged["nursing_minus_icu_start"]
            ),
            "first_any_order_minus_first_icu_transfer": qstats(
                merged["any_order_minus_icu_start"]
            ),
            "first_pressor_order_minus_first_icu_transfer": qstats(
                merged["pressor_order_minus_icu_start"]
            ),
            "first_nursing_minus_first_pressor_order": qstats(
                merged["nursing_minus_pressor_order"]
            ),
        },
        "icu_like_transfer_departments_top": [
            {"department": dept, "rows": n}
            for dept, n in top_depts
            if ICU_RX.search(dept)
        ],
        "all_transfer_departments_top30": [
            {"department": dept, "rows": n}
            for dept, n in top_depts
        ],
        "negative_time_counts": {
            "first_nursing_time": int((merged["first_nursing_time"] < 0).sum()),
            "first_any_order_time": int((merged["first_any_order_time"] < 0).sum()),
            "first_pressor_order_time": int((merged["first_pressor_order_time"] < 0).sum()),
            "first_icu_transfer_start": int((merged["first_icu_transfer_start"] < 0).sum()),
        },
        "decision": (
            "Use this audit to determine whether nursing and HIS medication times are "
            "on the same practical origin. A stable offset between systems would require "
            "explicit correction/validation before defining a cross-table endpoint."
        ),
    }

    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
