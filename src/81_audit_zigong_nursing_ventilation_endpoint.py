from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

CSV_ENCODINGS=["utf-8-sig","utf-8","gb18030"]
DIRECT_LEAK_RX=re.compile(r"插管|气管导管|气插导管|气管插管|呼吸机|机械通气|拔管|拔除",re.IGNORECASE)
ETT_MODE_RX=re.compile(r"气插导管|气管插管|气管导管",re.IGNORECASE)


def read_csv_robust(path: Path, **kwargs):
    last=None
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(path,encoding=enc,**kwargs)
        except UnicodeDecodeError as exc:
            last=exc
    if last is not None:
        raise last


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


def norm(x:str)->str:
    return re.sub(r"[^a-z0-9]+","",str(x).lower())


def qstats(vals):
    a=np.asarray(list(vals),dtype=float)
    a=a[np.isfinite(a)]
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


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--washout-hours",type=float,default=6.0)
    ap.add_argument("--horizon-hours",type=float,default=12.0)
    args=ap.parse_args()

    root=Path(args.root).expanduser().resolve()
    out=Path(args.output).expanduser().resolve()
    nursing=[p for p in root.rglob("dtNursingChart.csv") if not p.name.startswith("._")]
    dictionary=[p for p in root.rglob("datDictionary.csv") if not p.name.startswith("._")]
    baseline=[p for p in root.rglob("dtBaseline.csv") if not p.name.startswith("._")]
    if len(nursing)!=1 or len(dictionary)!=1 or len(baseline)!=1:
        raise RuntimeError("Expected exactly one nursing, dictionary, and baseline CSV.")

    d=read_csv_robust(dictionary[0],low_memory=False)
    d["_tn"]=d["table_name"].map(norm)
    d["_cn"]=d["column_name"].map(norm)
    target_cols=[
        "endotrachealintubation","endotrachealintubationdepth","extubation",
        "oxygeninhalationmode","vtsetting","fio2","f","vtsupervisor","nursingdesc","charttime"
    ]
    dict_rows=[]
    for col in target_cols:
        hit=d[(d["_tn"].str.contains("dtnursingchart",regex=False)) & (d["_cn"]==col)]
        for r in hit[["table_name","column_name","description"]].itertuples(index=False):
            dict_rows.append({"column_name":str(r.column_name),"description":str(r.description)})

    b=read_csv_robust(baseline[0],usecols=lambda c:c in {"PATIENT_ID","INP_NO"},low_memory=False)
    b["PATIENT_ID"]=pd.to_numeric(b["PATIENT_ID"],errors="coerce")
    b["INP_NO"]=pd.to_numeric(b["INP_NO"],errors="coerce")
    b=b.dropna(subset=["PATIENT_ID","INP_NO"]).copy()
    b["PATIENT_ID"]=b["PATIENT_ID"].astype("int64")
    b["INP_NO"]=b["INP_NO"].astype("int64")
    inp_to_patient=dict(zip(b["INP_NO"],b["PATIENT_ID"]))

    cols={"INP_NO","ChartTime","Endotracheal_intubation","Endotracheal_intubation_Depth","Extubation","Oxygen_inhalation_mode","Vt_setting","NURSING_DESC"}
    by_inp=defaultdict(list)
    for chunk in iter_csv_robust(nursing[0],100_000,usecols=lambda c:c in cols,low_memory=False):
        chunk["INP_NO"]=pd.to_numeric(chunk["INP_NO"],errors="coerce")
        chunk["ChartTime"]=pd.to_numeric(chunk["ChartTime"],errors="coerce")
        chunk=chunk.dropna(subset=["INP_NO","ChartTime"]).copy()
        if chunk.empty:
            continue
        chunk["INP_NO"]=chunk["INP_NO"].astype("int64")
        for row in chunk.itertuples(index=False):
            rec=row._asdict()
            inp=int(rec["INP_NO"])
            by_inp[inp].append(rec)

    definitions={
        "ett_depth_10_40":[],
        "ett_depth_10_40_plus_vt_100_1000":[],
        "explicit_ett_oxygen_mode":[],
        "consensus_invasive_ventilation":[],
    }
    case_details={k:[] for k in definitions}
    patients_by_definition={k:set() for k in definitions}
    first_chart_times=[]
    spans=[]

    for inp,rows in by_inp.items():
        rows=sorted(rows,key=lambda r:float(r["ChartTime"]))
        t0=float(rows[0]["ChartTime"])
        first_chart_times.append(t0)
        spans.append(float(rows[-1]["ChartTime"])-t0)

        first_event={k:None for k in definitions}
        first_extubation=None
        notes=[]
        for r in rows:
            t=float(r["ChartTime"])
            rel=t-t0
            note=r.get("NURSING_DESC")
            if isinstance(note,str) and note.strip():
                notes.append((rel,note))

            ext=str(r.get("Extubation")).strip().lower()
            if first_extubation is None and ext=="true":
                first_extubation=rel

            ett_raw=r.get("Endotracheal_intubation")
            ett_depth_raw=r.get("Endotracheal_intubation_Depth")
            ett=pd.to_numeric(pd.Series([ett_raw]),errors="coerce").iloc[0]
            ett2=pd.to_numeric(pd.Series([ett_depth_raw]),errors="coerce").iloc[0]
            depth=ett if pd.notna(ett) else ett2
            depth_pos=pd.notna(depth) and 10.0 <= float(depth) <= 40.0

            vt=pd.to_numeric(pd.Series([r.get("Vt_setting")]),errors="coerce").iloc[0]
            vt_pos=pd.notna(vt) and 100.0 <= float(vt) <= 1000.0

            mode=str(r.get("Oxygen_inhalation_mode") or "")
            mode_pos=bool(ETT_MODE_RX.search(mode))

            flags={
                "ett_depth_10_40":depth_pos,
                "ett_depth_10_40_plus_vt_100_1000":depth_pos and vt_pos,
                "explicit_ett_oxygen_mode":mode_pos,
                "consensus_invasive_ventilation":(depth_pos and vt_pos) or (mode_pos and vt_pos),
            }
            for name,flag in flags.items():
                if flag and first_event[name] is None:
                    first_event[name]=rel

        for name,ev in first_event.items():
            if ev is None:
                continue
            patients_by_definition[name].add(inp_to_patient.get(inp,inp))
            definitions[name].append(ev)
            prior=[(t,n) for t,n in notes if t < ev]
            prior12=[(t,n) for t,n in prior if t >= ev-args.horizon_hours]
            clean12=[(t,n) for t,n in prior12 if not DIRECT_LEAK_RX.search(n)]
            last_gap=None
            if prior:
                last_gap=ev-max(t for t,_ in prior)
            case_details[name].append({
                "event_time_from_first_nursing":ev,
                "incident_after_washout":ev >= args.washout_hours,
                "has_prior_note":bool(prior),
                "has_prior_note_within_12h":bool(prior12),
                "has_clean_prior_note_within_12h":bool(clean12),
                "last_prior_note_gap_hours":last_gap,
                "extubation_before_event":first_extubation is not None and first_extubation < ev,
            })

    report_defs={}
    for name,events in definitions.items():
        details=case_details[name]
        incident=[x for x in details if x["incident_after_washout"]]
        report_defs[name]={
            "encounters_with_event":int(len(events)),
            "patients_with_event":int(len(patients_by_definition[name])),
            "first_event_time_from_first_nursing_hours":qstats(events),
            "incident_after_6h_washout":int(len(incident)),
            "incident_with_any_prior_note":int(sum(x["has_prior_note"] for x in incident)),
            "incident_with_prior_note_within_12h":int(sum(x["has_prior_note_within_12h"] for x in incident)),
            "incident_with_clean_prior_note_within_12h":int(sum(x["has_clean_prior_note_within_12h"] for x in incident)),
            "incident_with_extubation_before_event":int(sum(x["extubation_before_event"] for x in incident)),
            "last_prior_note_gap_hours_for_incident":qstats([x["last_prior_note_gap_hours"] for x in incident if x["last_prior_note_gap_hours"] is not None]),
        }

    report={
        "dataset":"Zigong Fourth People's Hospital critical care infection database v1.1",
        "analysis":"Within-nursing prospective invasive-ventilation endpoint feasibility audit",
        "local_only":True,
        "contains_note_text":False,
        "contains_patient_identifiers":False,
        "washout_hours_from_first_timed_nursing_row":float(args.washout_hours),
        "prediction_horizon_hours":float(args.horizon_hours),
        "time_origin_rule":"Use only within-dtNursingChart relative time from each encounter's first timed nursing row. No cross-table clock alignment or fixed offset correction.",
        "dictionary_rows":dict_rows,
        "patients_mapped_in_baseline":int(b["PATIENT_ID"].nunique()),
        "nursing_encounters_with_timed_rows":int(len(by_inp)),
        "first_chart_time_absolute_offset_distribution":qstats(first_chart_times),
        "within_nursing_span_hours":qstats(spans),
        "candidate_definitions":{
            "ett_depth_10_40":"First nursing row with a numeric endotracheal-intubation depth between 10 and 40 cm.",
            "ett_depth_10_40_plus_vt_100_1000":"Depth criterion plus same-row numeric tidal-volume setting 100-1000 mL.",
            "explicit_ett_oxygen_mode":"First row whose oxygen-inhalation mode explicitly names an endotracheal airway (气插导管/气管插管/气管导管).",
            "consensus_invasive_ventilation":"Depth + tidal-volume setting OR explicit endotracheal-airway mode + tidal-volume setting."
        },
        "definitions":report_defs,
        "leakage_screen":"Direct Chinese intubation/airway/mechanical-ventilation/extubation terms are excluded only for the clean-note availability count; no model input is created.",
        "decision_rule":"Select an endpoint only if the dictionary semantics and aggregate incidence support a clinically coherent definition with adequate incident cases and clean pre-event narrative availability. Freeze the definition before cohort construction or model scoring."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
