from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from common import find_file, lower_columns, module_path, parse_datetime, read_columns, resolve_root
from runrelay_progress import update_progress


CHAR_PATTERNS = {
    "heart_rate": [r"\bheart rate\b"],
    "sbp": [r"\bsystolic\b"],
    "dbp": [r"\bdiastolic\b"],
    "map": [r"\bmean arterial\b", r"\bmean blood pressure\b", r"\bmean bp\b", r"\bmap\b"],
    "resp_rate": [r"\brespiratory rate\b", r"\bresp rate\b"],
    "spo2": [r"\bspo2\b", r"\bo2 saturation\b", r"\boxygen saturation\b"],
    "temperature": [r"\btemperature\b", r"\btemp\b"],
    "gcs_total": [r"\bgcs.*total\b", r"\bglasgow coma.*total\b"],
    "gcs_eye": [r"\bgcs.*eye\b", r"\beye opening\b"],
    "gcs_verbal": [r"\bgcs.*verbal\b", r"\bverbal response\b"],
    "gcs_motor": [r"\bgcs.*motor\b", r"\bmotor response\b"],
}

LAB_PATTERNS = {
    "lactate": [r"\blactate\b"],
    "creatinine": [r"\bcreatinine\b"],
    "bun": [r"\burea nitrogen\b", r"\bbun\b"],
    "wbc": [r"\bwhite blood cells?\b", r"\bwbc\b"],
    "hemoglobin": [r"\bhemoglobin\b"],
    "platelets": [r"\bplatelet"],
    "sodium": [r"\bsodium\b"],
    "potassium": [r"\bpotassium\b"],
    "bicarbonate": [r"\bbicarbonate\b", r"\btotal co2\b"],
    "chloride": [r"\bchloride\b"],
    "glucose": [r"\bglucose\b"],
    "bilirubin_total": [r"\bbilirubin.*total\b", r"\btotal bilirubin\b"],
    "inr": [r"\binr\b"],
    "ph": [r"^ph$", r"\bblood ph\b"],
}

URINE_PATTERNS = [
    r"\burine\b",
    r"\burinary\b",
    r"\bfoley\b",
]


def regex_union(patterns):
    return re.compile("|".join(f"(?:{x})" for x in patterns), flags=re.I)


def read_indices(local_root: Path) -> tuple[pd.DataFrame, dict]:
    rows=[]
    reports={}
    for outcome in ("invasive_ventilation","renal_replacement_therapy","icu_death"):
        p=local_root/outcome/"population_index_local.csv"
        d=pd.read_csv(p,low_memory=False)
        required={"icustay_id","hadm_id","landmark_time","dbsource"}
        missing=required-set(d.columns)
        if missing:
            raise RuntimeError(f"{p}: missing {sorted(missing)}")
        d["icustay_id"]=pd.to_numeric(d["icustay_id"],errors="raise").astype("int64")
        d["hadm_id"]=pd.to_numeric(d["hadm_id"],errors="raise").astype("int64")
        d["landmark_time"]=pd.to_datetime(d["landmark_time"],errors="raise")
        d["outcome"]=outcome
        rows.append(d[["outcome","icustay_id","hadm_id","landmark_time","dbsource"]])
        reports[outcome]={"rows":int(len(d)),"unique_icu_stays":int(d["icustay_id"].nunique())}
    all_rows=pd.concat(rows,ignore_index=True)
    unique=all_rows.drop_duplicates(["icustay_id","hadm_id","landmark_time"]).copy()
    return unique,reports


def candidate_rows(d: pd.DataFrame, label_col: str, patterns: dict[str,list[str]]) -> dict:
    out={}
    norm=d[label_col].fillna("").astype(str)
    for concept,pats in patterns.items():
        rx=regex_union(pats)
        q=d[norm.str.contains(rx,regex=True,na=False)].copy()
        cols=[c for c in ["itemid","label","dbsource","linksto","category","unitname","fluid","loinc_code"] if c in q.columns]
        out[concept]=q[cols].sort_values(["itemid"]).to_dict(orient="records")
    return out


def candidate_id_map(cands: dict) -> dict[str,set[int]]:
    out={}
    for concept,rows in cands.items():
        out[concept]={int(r["itemid"]) for r in rows if r.get("itemid") is not None}
    return out


def add_counts(counter: dict, concept: str, outcome: str, ids: set[int], observed: pd.DataFrame, stay_col: str):
    if not ids:
        counter.setdefault(concept,{})[outcome]={"candidate_itemids":0,"stays_with_value":0,"fraction":0.0}
        return
    q=observed[observed["itemid"].isin(ids) & observed["outcome"].eq(outcome)]
    denom=int(observed.loc[observed["outcome"].eq(outcome),stay_col].nunique())
    n=int(q[stay_col].nunique())
    counter.setdefault(concept,{})[outcome]={
        "candidate_itemids":int(len(ids)),
        "stays_with_value":n,
        "fraction":float(n/denom) if denom else None,
        "observed_item_counts":{str(int(k)):int(v) for k,v in q["itemid"].value_counts().to_dict().items()},
    }


def scan_char(root:Path,snaps:pd.DataFrame,ids:set[int]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame(columns=["outcome","icustay_id","itemid"])
    f=find_file(module_path(root,"mimiciii"),["CHARTEVENTS.csv.gz","CHARTEVENTS.csv"])
    parts=[]
    lookup=snaps[["outcome","icustay_id","hadm_id","landmark_time"]]
    stay_ids=set(snaps["icustay_id"])
    for chunk in read_columns(f,["hadm_id","icustay_id","itemid","charttime","valuenum","value","error"],chunksize=600_000):
        c=lower_columns(chunk)
        c["icustay_id"]=pd.to_numeric(c["icustay_id"],errors="coerce")
        c=c[c["icustay_id"].isin(stay_ids)].copy()
        if c.empty: continue
        c["itemid"]=pd.to_numeric(c["itemid"],errors="coerce")
        c=c[c["itemid"].isin(ids)].copy()
        if c.empty: continue
        if "error" in c:
            c=c[pd.to_numeric(c["error"],errors="coerce").fillna(0).eq(0)].copy()
        c["charttime"]=parse_datetime(c["charttime"])
        c["valuenum"]=pd.to_numeric(c["valuenum"],errors="coerce")
        c=c.dropna(subset=["icustay_id","itemid","charttime"])
        c["icustay_id"]=c["icustay_id"].astype("int64")
        c=c.merge(lookup,on="icustay_id",how="inner")
        c=c[(c["charttime"]<=c["landmark_time"])&(c["charttime"]>=c["landmark_time"]-pd.to_timedelta(6,unit="h"))]
        c=c[c["valuenum"].notna() | c["value"].notna()]
        if not c.empty: parts.append(c[["outcome","icustay_id","itemid"]])
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=["outcome","icustay_id","itemid"])


def scan_labs(root:Path,snaps:pd.DataFrame,ids:set[int]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame(columns=["outcome","icustay_id","itemid"])
    f=find_file(module_path(root,"mimiciii"),["LABEVENTS.csv.gz","LABEVENTS.csv"])
    parts=[]
    lookup=snaps[["outcome","icustay_id","hadm_id","landmark_time"]]
    hadms=set(snaps["hadm_id"])
    for chunk in read_columns(f,["hadm_id","itemid","charttime","valuenum","value"],chunksize=600_000):
        c=lower_columns(chunk)
        c["hadm_id"]=pd.to_numeric(c["hadm_id"],errors="coerce")
        c=c[c["hadm_id"].isin(hadms)].copy()
        if c.empty: continue
        c["itemid"]=pd.to_numeric(c["itemid"],errors="coerce")
        c=c[c["itemid"].isin(ids)].copy()
        if c.empty: continue
        c["charttime"]=parse_datetime(c["charttime"])
        c["valuenum"]=pd.to_numeric(c["valuenum"],errors="coerce")
        c=c.dropna(subset=["hadm_id","itemid","charttime"])
        c["hadm_id"]=c["hadm_id"].astype("int64")
        c=c.merge(lookup,on="hadm_id",how="inner")
        c=c[(c["charttime"]<=c["landmark_time"])&(c["charttime"]>=c["landmark_time"]-pd.to_timedelta(24,unit="h"))]
        c=c[c["valuenum"].notna() | c["value"].notna()]
        if not c.empty: parts.append(c[["outcome","icustay_id","itemid"]])
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=["outcome","icustay_id","itemid"])


def scan_output(root:Path,snaps:pd.DataFrame,ids:set[int]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame(columns=["outcome","icustay_id","itemid"])
    f=find_file(module_path(root,"mimiciii"),["OUTPUTEVENTS.csv.gz","OUTPUTEVENTS.csv"])
    parts=[]
    lookup=snaps[["outcome","icustay_id","hadm_id","landmark_time"]]
    stays=set(snaps["icustay_id"])
    for chunk in read_columns(f,["hadm_id","icustay_id","itemid","charttime","value","valueuom","iserror"],chunksize=600_000):
        c=lower_columns(chunk)
        c["icustay_id"]=pd.to_numeric(c["icustay_id"],errors="coerce")
        c=c[c["icustay_id"].isin(stays)].copy()
        if c.empty: continue
        c["itemid"]=pd.to_numeric(c["itemid"],errors="coerce")
        c=c[c["itemid"].isin(ids)].copy()
        if c.empty: continue
        if "iserror" in c:
            c=c[pd.to_numeric(c["iserror"],errors="coerce").fillna(0).eq(0)].copy()
        c["charttime"]=parse_datetime(c["charttime"])
        c["value_num"]=pd.to_numeric(c["value"],errors="coerce")
        c=c.dropna(subset=["icustay_id","itemid","charttime","value_num"])
        c["icustay_id"]=c["icustay_id"].astype("int64")
        c=c.merge(lookup,on="icustay_id",how="inner")
        c=c[(c["charttime"]<=c["landmark_time"])&(c["charttime"]>=c["landmark_time"]-pd.to_timedelta(6,unit="h"))]
        if not c.empty: parts.append(c[["outcome","icustay_id","itemid"]])
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=["outcome","icustay_id","itemid"])


def main():
    ap=argparse.ArgumentParser(description="Model-free discovery audit for enhanced v2 structured baseline.")
    ap.add_argument("--root",required=True)
    ap.add_argument("--local-root",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    root=resolve_root(args.root)
    local_root=Path(args.local_root).expanduser().resolve()
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)

    update_progress(current=1,total=5,phase="cohorts",message="Loading corrected v2 cohort indices without labels",unit="stage")
    snaps,cohort_report=read_indices(local_root)

    update_progress(current=2,total=5,phase="dictionary",message="Discovering candidate structured item mappings from MIMIC dictionaries",unit="stage")
    ditem=lower_columns(pd.read_csv(find_file(module_path(root,"mimiciii"),["D_ITEMS.csv.gz","D_ITEMS.csv"]),low_memory=False))
    dlab=lower_columns(pd.read_csv(find_file(module_path(root,"mimiciii"),["D_LABITEMS.csv.gz","D_LABITEMS.csv"]),low_memory=False))
    for d in (ditem,dlab):
        d["itemid"]=pd.to_numeric(d["itemid"],errors="coerce")
        d.dropna(subset=["itemid"],inplace=True)
        d["itemid"]=d["itemid"].astype(int)
    char_candidates=candidate_rows(ditem,"label",CHAR_PATTERNS)
    lab_candidates=candidate_rows(dlab,"label",LAB_PATTERNS)
    urine_rx=regex_union(URINE_PATTERNS)
    u=ditem[
        ditem["linksto"].fillna("").astype(str).str.lower().eq("outputevents")
        & ditem["label"].fillna("").astype(str).str.contains(urine_rx,regex=True,na=False)
    ].copy()
    ucols=[c for c in ["itemid","label","dbsource","linksto","category","unitname"] if c in u.columns]
    urine_candidates=u[ucols].sort_values("itemid").to_dict(orient="records")

    char_ids=candidate_id_map(char_candidates)
    lab_ids=candidate_id_map(lab_candidates)
    urine_ids={int(r["itemid"]) for r in urine_candidates}

    update_progress(current=3,total=5,phase="char",message="Auditing six-hour bedside feature availability",unit="stage")
    char_obs=scan_char(root,snaps,set().union(*char_ids.values()) if char_ids else set())

    update_progress(current=4,total=5,phase="labs_output",message="Auditing 24-hour laboratory and six-hour urine-output availability",unit="stage")
    lab_obs=scan_labs(root,snaps,set().union(*lab_ids.values()) if lab_ids else set())
    urine_obs=scan_output(root,snaps,urine_ids)

    availability={"chartevents":{},"labevents":{},"urine_output":{}}
    outcomes=("invasive_ventilation","renal_replacement_therapy","icu_death")
    for concept,ids in char_ids.items():
        for outcome in outcomes:
            add_counts(availability["chartevents"],concept,outcome,ids,char_obs,"icustay_id")
    for concept,ids in lab_ids.items():
        for outcome in outcomes:
            add_counts(availability["labevents"],concept,outcome,ids,lab_obs,"icustay_id")
    for outcome in outcomes:
        add_counts(availability["urine_output"],"urine_output_6h",outcome,urine_ids,urine_obs,"icustay_id")

    update_progress(current=5,total=5,phase="done",message="Completed model-free enhanced baseline discovery audit",unit="stage")
    report={
        "analysis":"Enhanced structured baseline discovery audit v2",
        "protocol":"docs/enhanced_structured_baseline_discovery_protocol_v2.md",
        "local_only":True,
        "contains_patient_identifiers":False,
        "contains_row_level_data":False,
        "outcome_labels_read":False,
        "predictive_model_fitted":False,
        "cohorts":cohort_report,
        "dictionary_candidates":{
            "chartevents":char_candidates,
            "labevents":lab_candidates,
            "urine_output":urine_candidates,
        },
        "availability":availability,
        "guardrail":"Dictionary and prospective availability audit only. Final exact item mappings must be frozen before structured feature extraction or predictive evaluation."
    }
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
