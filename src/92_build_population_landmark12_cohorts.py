from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress

LANDMARK=12.0
HORIZON=12.0
LOOKBACK=12.0
EXPECTED={
    "invasive_ventilation":{"observable":28699,"cases":282,"controls":28417,"note":19426,"note_cases":124,"note_controls":19302},
    "renal_replacement_therapy":{"observable":48831,"cases":391,"controls":48440,"note":33834,"note_cases":155,"note_controls":33679},
    "icu_death":{"observable":49555,"cases":537,"controls":49018,"note":33749,"note_cases":302,"note_controls":33447},
}


def load_audit_module():
    path=Path(__file__).with_name("91_audit_population_landmark_feasibility.py")
    spec=importlib.util.spec_from_file_location("population_landmark_audit_helpers",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load population landmark audit helpers.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def case_id(outcome:str, icustay_id:int)->str:
    raw=f"population_landmark12_v1|{outcome}|{int(icustay_id)}"
    return "pl12_"+hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def main():
    ap=argparse.ArgumentParser(description="Build frozen population-representative 12-hour landmark cohorts.")
    ap.add_argument("--root",required=True)
    ap.add_argument("--local-output-root",required=True)
    ap.add_argument("--manifest",required=True)
    args=ap.parse_args()

    audit=load_audit_module()
    mod=audit.load_builder()
    root=mod.resolve_root(args.root)
    local_root=Path(args.local_output_root).expanduser().resolve()
    manifest_path=Path(args.manifest).expanduser().resolve()
    local_root.mkdir(parents=True,exist_ok=True)
    manifest_path.parent.mkdir(parents=True,exist_ok=True)

    update_progress(current=1,total=5,phase="source",message="Loading ICU stays and frozen endpoint evidence",unit="stage")
    icu=mod.load_icustays(root).copy()
    icu["icustay_id"]=pd.to_numeric(icu["icustay_id"],errors="coerce").astype(int)
    icu["subject_id"]=pd.to_numeric(icu["subject_id"],errors="coerce").astype(int)
    evidence=mod.scan_event_evidence(root)
    assigned=mod.assign_evidence_to_icu(evidence,icu)
    endpoint_tables=audit.build_stay_endpoint_tables(mod,assigned,icu,root,6.0)

    update_progress(current=2,total=5,phase="notes",message="Loading prospectively available bedside notes",unit="stage")
    notes=mod.load_notes(root,set(icu["hadm_id"].astype(int)))
    note_icu=mod.assign_notes_to_icu(notes,icu)
    note_icu["icustay_id"]=pd.to_numeric(note_icu["icustay_id"],errors="coerce").astype(int)

    manifest_outcomes={}
    for oi,outcome in enumerate(("invasive_ventilation","renal_replacement_therapy","icu_death"),start=1):
        update_progress(current=2+oi,total=5,phase="cohorts",message=f"Building population cohort for {outcome}",unit="stage")
        info=endpoint_tables[outcome]
        spec=mod.OUTCOME_SPECS[outcome]
        rx=mod.compile_rx(spec["language_patterns"])

        risk=icu.copy()
        risk["landmark_time"]=risk["intime"]+pd.to_timedelta(LANDMARK,unit="h")
        risk["horizon_end"]=risk["landmark_time"]+pd.to_timedelta(HORIZON,unit="h")
        risk=risk[risk["outtime"]>risk["landmark_time"]].copy()
        prevalent=info["prevalent_stays"]
        if prevalent:
            risk=risk[~risk["icustay_id"].isin(prevalent)].copy()

        risk["first_disqualifying_time"]=risk["icustay_id"].map(info["first_disqual"])
        risk=risk[
            risk["first_disqualifying_time"].isna()
            | (risk["first_disqualifying_time"]>risk["landmark_time"])
        ].copy()

        risk["event_time"]=risk["icustay_id"].map(info["first_event"])
        risk["is_case"]=(
            risk["event_time"].notna()
            & (risk["event_time"]>risk["landmark_time"])
            & (risk["event_time"]<=risk["horizon_end"])
        )
        risk["fully_observed_control"]=~risk["is_case"] & (risk["outtime"]>=risk["horizon_end"])
        pop=risk[risk["is_case"]|risk["fully_observed_control"]].copy()
        pop["label"]=pop["is_case"].astype(int)

        outcome_notes=note_icu[
            ~note_icu["text"].fillna("").astype(str).str.contains(rx,regex=True,na=False)
        ].copy()
        candidate=outcome_notes[
            (outcome_notes["hours_since_icu"]<=LANDMARK)
            & (outcome_notes["hours_since_icu"]>=0.0)
        ].copy()
        note_cols=[
            "icustay_id","note_time","hours_since_icu","category","dbsource",
            "storetime_available","documentation_delay_hours","text"
        ]
        last_notes=(
            candidate.sort_values(["icustay_id","note_time"])
            .groupby("icustay_id",as_index=False)
            .last()[note_cols]
        )
        pop=pop.merge(last_notes,on="icustay_id",how="left",suffixes=("","_note"))
        pop["has_note"]=pop["note_time"].notna()
        pop["case_id"]=[case_id(outcome,x) for x in pop["icustay_id"]]
        if pop["case_id"].duplicated().any():
            raise RuntimeError(f"{outcome}: duplicate generated case ids")

        exp=EXPECTED[outcome]
        n=len(pop); nc=int(pop["label"].sum()); nctrl=n-nc
        with_note=pop[pop["has_note"]].copy()
        nn=len(with_note); nnc=int(with_note["label"].sum()); nnctrl=nn-nnc
        got={"observable":n,"cases":nc,"controls":nctrl,"note":nn,"note_cases":nnc,"note_controls":nnctrl}
        if got!=exp:
            raise RuntimeError(f"{outcome}: cohort counts differ from frozen feasibility audit: got={got}, expected={exp}")

        outdir=local_root/outcome
        outdir.mkdir(parents=True,exist_ok=True)
        index_cols=[
            "case_id","subject_id","hadm_id","icustay_id","label",
            "landmark_time","horizon_end","event_time","outtime",
            "has_note","note_time","hours_since_icu","category","dbsource",
            "storetime_available","documentation_delay_hours",
        ]
        pop[[c for c in index_cols if c in pop.columns]].to_csv(outdir/"population_index_local.csv",index=False)

        with (outdir/"cases.jsonl").open("w",encoding="utf-8") as f:
            for row in with_note.itertuples(index=False):
                rec={
                    "case_id":str(row.case_id),
                    "synthetic_only":False,
                    "local_only":True,
                    "model_state":{"clinical_note":str(row.text)},
                    "metadata":{
                        "analysis":"population_landmark12_v1",
                        "outcome":outcome,
                        "label":int(row.label),
                        "note_available":True,
                        "note_category":str(row.category),
                        "dbsource":str(row.dbsource),
                        "landmark_hours":LANDMARK,
                        "prediction_horizon_hours":HORIZON,
                        "hours_since_icu_at_note":round(float(row.hours_since_icu),3),
                        "note_age_at_landmark_hours":round(float((row.landmark_time-row.note_time).total_seconds()/3600.0),3),
                        "note_availability_basis":"max(charttime, storetime)" if bool(row.storetime_available) else "charttime_fallback",
                        "documentation_delay_hours":(
                            round(float(row.documentation_delay_hours),3)
                            if pd.notna(row.documentation_delay_hours) else None
                        ),
                        "note_characters":len(str(row.text)),
                    },
                    "questions":mod.SEMANTIC_CONSTRUCTS,
                    "gold":None,
                }
                f.write(json.dumps(rec,ensure_ascii=False)+"\n")

        manifest_outcomes[outcome]={
            "observable_stays":n,
            "observable_unique_patients":int(pop["subject_id"].nunique()),
            "cases":nc,
            "controls":nctrl,
            "event_prevalence":float(nc/n),
            "note_available_stays":nn,
            "note_available_unique_patients":int(with_note["subject_id"].nunique()),
            "note_available_cases":nnc,
            "note_available_controls":nnctrl,
            "note_coverage":float(nn/n),
            "case_note_coverage":float(nnc/nc),
            "control_note_coverage":float(nnctrl/nctrl),
            "note_available_event_prevalence":float(nnc/nn),
            "patients_with_multiple_stays_in_population":int((pop.groupby("subject_id").size()>1).sum()),
            "local_population_index":str(outdir/"population_index_local.csv"),
            "local_note_cases":str(outdir/"cases.jsonl"),
        }

    manifest={
        "analysis":"Frozen population-representative 12-hour landmark cohorts v1",
        "protocol":"docs/population_landmark12_cohort_protocol_v1.md",
        "source_feasibility_job":"Q7K4R9M3",
        "source_feasibility_artifact_sha256":"2a780dfbf0dc92a83511e63a5ea255454f4d60869a1ed6c6fc0c3a01e05b6b26",
        "local_only":True,
        "contains_note_text":False,
        "contains_source_patient_identifiers":False,
        "case_control_sampling":False,
        "landmark_hours":LANDMARK,
        "prediction_horizon_hours":HORIZON,
        "prospective_note_lookback_hours":LOOKBACK,
        "outcomes":manifest_outcomes,
        "guardrail":"Manifest only. Local cohort files retain all observable stays; note model inputs exist only for prospectively note-available stays. No model inference or performance was computed."
    }
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
