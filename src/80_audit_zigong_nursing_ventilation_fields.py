from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

CSV_ENCODINGS=["utf-8-sig","utf-8","gb18030"]
FIELDS=[
    "Endotracheal_intubation",
    "Endotracheal_intubation_Depth",
    "Extubation",
    "Oxygen_inhalation_mode",
    "F",
    "Vt_setting",
    "PSIPAP",
    "R",
    "FIO2",
    "Vt_Supervisor",
    "Hemodialysis_tube",
]
VENT_SUPPORT_FIELDS=["F","Vt_setting","PSIPAP","R","FIO2","Vt_Supervisor"]


def iter_csv_robust(path: Path, chunksize: int, **kwargs):
    last=None
    for enc in CSV_ENCODINGS:
        first=True
        try:
            reader=pd.read_csv(path,encoding=enc,chunksize=chunksize,**kwargs)
            for chunk in reader:
                first=False
                yield chunk
            return
        except UnicodeDecodeError as exc:
            if not first:
                raise
            last=exc
    if last is not None:
        raise last


def clean_value(x):
    if pd.isna(x):
        return None
    s=str(x).strip()
    if not s or s.lower() in {"nan","none","null"}:
        return None
    return s


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    root=Path(args.root).expanduser().resolve()
    out=Path(args.output).expanduser().resolve()
    matches=[p for p in root.rglob("dtNursingChart.csv") if not p.name.startswith("._")]
    if len(matches)!=1:
        raise RuntimeError(f"Expected one dtNursingChart.csv, found {len(matches)}")
    path=matches[0]

    value_counts={f:Counter() for f in FIELDS}
    nonempty_counts=Counter()
    numeric_counts=Counter()
    patient_sets={f:set() for f in FIELDS}
    support_cooccurrence={f:Counter() for f in FIELDS}
    chart_times_by_patient=defaultdict(list)
    rows_total=0

    usecols=set(["INP_NO","ChartTime"]+FIELDS)
    for chunk in iter_csv_robust(path,100_000,usecols=lambda c:c in usecols,low_memory=False):
        rows_total += len(chunk)
        chunk["INP_NO"]=pd.to_numeric(chunk["INP_NO"],errors="coerce")
        chunk["ChartTime"]=pd.to_numeric(chunk["ChartTime"],errors="coerce")

        for r in chunk.dropna(subset=["INP_NO","ChartTime"])[["INP_NO","ChartTime"]].itertuples(index=False):
            chart_times_by_patient[int(r.INP_NO)].append(float(r.ChartTime))

        support_any=pd.Series(False,index=chunk.index)
        for sf in VENT_SUPPORT_FIELDS:
            if sf in chunk.columns:
                support_any |= chunk[sf].map(clean_value).notna()

        for f in FIELDS:
            if f not in chunk.columns:
                continue
            cleaned=chunk[f].map(clean_value)
            mask=cleaned.notna()
            nonempty_counts[f] += int(mask.sum())
            numeric=pd.to_numeric(cleaned,errors="coerce")
            numeric_counts[f] += int(numeric.notna().sum())
            for val,count in cleaned[mask].value_counts(dropna=False).items():
                value_counts[f][str(val)] += int(count)

            sub=chunk.loc[mask & chunk["INP_NO"].notna(),["INP_NO"]]
            patient_sets[f].update(int(x) for x in sub["INP_NO"].tolist())

            if f not in VENT_SUPPORT_FIELDS:
                tmp=pd.DataFrame({"value":cleaned[mask],"support":support_any[mask]})
                if not tmp.empty:
                    grp=tmp.groupby("value")["support"].agg(["count","sum"])
                    for val,row in grp.iterrows():
                        support_cooccurrence[f][str(val)] += int(row["sum"])

    field_reports={}
    for f in FIELDS:
        n=nonempty_counts[f]
        tops=[]
        for val,count in value_counts[f].most_common(30):
            if count < 5:
                continue
            item={"value":val,"count":int(count)}
            if f not in VENT_SUPPORT_FIELDS:
                item["rows_with_any_vent_support_field"]=int(support_cooccurrence[f].get(val,0))
            tops.append(item)
        field_reports[f]={
            "nonempty_rows":int(n),
            "patients_with_nonempty":int(len(patient_sets[f])),
            "numeric_parse_fraction":float(numeric_counts[f]/n) if n else None,
            "n_unique_nonempty":int(len(value_counts[f])),
            "top_values_count_ge_5":tops,
        }

    spans=[]
    firsts=[]
    for vals in chart_times_by_patient.values():
        if not vals:
            continue
        a=np.asarray(vals,dtype=float)
        firsts.append(float(np.min(a)))
        spans.append(float(np.max(a)-np.min(a)))

    def qstats(x):
        a=np.asarray(x,dtype=float)
        if len(a)==0:
            return {"n":0}
        return {
            "n":int(len(a)),
            "p05":float(np.quantile(a,0.05)),
            "p25":float(np.quantile(a,0.25)),
            "median":float(np.median(a)),
            "p75":float(np.quantile(a,0.75)),
            "p95":float(np.quantile(a,0.95)),
        }

    report={
        "dataset":"Zigong Fourth People's Hospital critical care infection database v1.1",
        "analysis":"Aggregate within-nursing ventilation-field feasibility audit",
        "local_only":True,
        "contains_note_text":False,
        "contains_patient_identifiers":False,
        "rows_total":int(rows_total),
        "patients_with_timed_nursing_rows":int(len(chart_times_by_patient)),
        "first_nursing_chart_time_hours":qstats(firsts),
        "within_patient_nursing_time_span_hours":qstats(spans),
        "fields":field_reports,
        "guardrail":"This audit only characterizes structured nursing fields. No endpoint definition, cohort selection, or model scoring is performed."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
