from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress

OUTCOMES=("invasive_ventilation","renal_replacement_therapy","icu_death")
LANDMARKS=(6.0,12.0,24.0,36.0)


def load_builder():
    path=Path(__file__).with_name("54_build_multitask_benchmark.py")
    spec=importlib.util.spec_from_file_location("frozen_multitask_builder_landmark_audit",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen multitask benchmark builder.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def qstats(vals):
    x=pd.Series(list(vals),dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    if x.empty:
        return {"n":0,"p05":None,"p25":None,"median":None,"p75":None,"p95":None}
    return {
        "n":int(len(x)),
        "p05":float(x.quantile(.05)),
        "p25":float(x.quantile(.25)),
        "median":float(x.median()),
        "p75":float(x.quantile(.75)),
        "p95":float(x.quantile(.95)),
    }


def build_stay_endpoint_tables(mod, assigned, icu, root, washout):
    tables={}
    specs={
        "invasive_ventilation":(
            {"vent_procedure"},
            {"vent_procedure","vent_explicit_chart","vent_support"},
        ),
        "renal_replacement_therapy":(
            {"rrt_procedure","rrt_active_chart"},
            {"rrt_procedure","rrt_active_chart","rrt_strict_output"},
        ),
    }
    for outcome,(endpoint_evidence,disqualifying_evidence) in specs.items():
        relevant=assigned[assigned["evidence"].isin(disqualifying_evidence)].copy()
        prevalent=set(
            pd.to_numeric(
                relevant.loc[relevant["hours_since_icu"]<washout,"icustay_id"],
                errors="coerce"
            ).dropna().astype(int)
        )
        endpoint=assigned[
            assigned["evidence"].isin(endpoint_evidence)
            & (assigned["hours_since_icu"]>=washout)
        ].copy()
        endpoint=endpoint[
            ~pd.to_numeric(endpoint["icustay_id"],errors="coerce").fillna(-1).astype(int).isin(prevalent)
        ].copy()
        first_event=(
            endpoint.sort_values("event_time")
            .groupby("icustay_id",as_index=False)
            .first()[["icustay_id","event_time"]]
            .set_index("icustay_id")["event_time"]
        )
        first_disqual=(
            relevant.sort_values("event_time")
            .groupby("icustay_id",as_index=False)
            .first()[["icustay_id","event_time"]]
            .set_index("icustay_id")["event_time"]
        )
        tables[outcome]={
            "first_event":first_event,
            "first_disqual":first_disqual,
            "prevalent_stays":prevalent,
        }

    # Death uses the same frozen source definition but stays at ICU-stay level.
    f=mod.find_file(mod.module_path(root,"mimiciii"),["ADMISSIONS.csv.gz","ADMISSIONS.csv"])
    if f is None:
        raise FileNotFoundError("ADMISSIONS not found")
    d=mod.lower_columns(pd.read_csv(
        f,
        usecols=lambda c:c.lower() in {"subject_id","hadm_id","deathtime"},
        low_memory=False,
    ))
    d["subject_id"]=pd.to_numeric(d["subject_id"],errors="coerce")
    d["hadm_id"]=pd.to_numeric(d["hadm_id"],errors="coerce")
    d["event_time"]=mod.parse_datetime(d["deathtime"])
    d=d.dropna(subset=["subject_id","hadm_id","event_time"]).copy()
    m=d.merge(
        icu[["subject_id","hadm_id","icustay_id","intime","outtime"]],
        on=["subject_id","hadm_id"],
        how="inner",
    )
    m=m[(m["event_time"]>=m["intime"])&(m["event_time"]<=m["outtime"])].copy()
    m["hours_since_icu"]=(m["event_time"]-m["intime"]).dt.total_seconds()/3600.0
    first_death=(
        m[m["hours_since_icu"]>=washout]
        .sort_values("event_time")
        .groupby("icustay_id",as_index=False)
        .first()[["icustay_id","event_time"]]
        .set_index("icustay_id")["event_time"]
    )
    tables["icu_death"]={
        "first_event":first_death,
        "first_disqual":first_death,
        "prevalent_stays":set(),
    }
    return tables


def main():
    ap=argparse.ArgumentParser(description="Audit representative fixed-landmark risk-set feasibility.")
    ap.add_argument("--root",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--washout-hours",type=float,default=6.0)
    ap.add_argument("--horizon-hours",type=float,default=12.0)
    ap.add_argument("--note-lookback-hours",type=float,default=12.0)
    args=ap.parse_args()

    mod=load_builder()
    root=mod.resolve_root(args.root)
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)

    update_progress(current=1,total=6,phase="source",message="Loading ICU stays and frozen endpoint evidence",unit="stage")
    icu=mod.load_icustays(root).copy()
    icu["icustay_id"]=pd.to_numeric(icu["icustay_id"],errors="coerce").astype(int)
    icu["subject_id"]=pd.to_numeric(icu["subject_id"],errors="coerce").astype(int)

    evidence=mod.scan_event_evidence(root)
    assigned=mod.assign_evidence_to_icu(evidence,icu)
    endpoint_tables=build_stay_endpoint_tables(mod,assigned,icu,root,args.washout_hours)

    update_progress(current=2,total=6,phase="notes",message="Loading prospectively available bedside notes",unit="stage")
    notes=mod.load_notes(root,set(icu["hadm_id"].astype(int)))
    note_icu=mod.assign_notes_to_icu(notes,icu)
    note_icu["icustay_id"]=pd.to_numeric(note_icu["icustay_id"],errors="coerce").astype(int)

    report_outcomes={}
    for oi,outcome in enumerate(OUTCOMES):
        update_progress(
            current=3+oi,total=6,phase="landmarks",
            message=f"Auditing fixed landmarks for {outcome}",unit="stage"
        )
        spec=mod.OUTCOME_SPECS[outcome]
        rx=mod.compile_rx(spec["language_patterns"])
        outcome_notes=note_icu[
            ~note_icu["text"].fillna("").astype(str).str.contains(rx,regex=True,na=False)
        ].copy()

        info=endpoint_tables[outcome]
        event_map=info["first_event"]
        disqual_map=info["first_disqual"]
        prevalent=info["prevalent_stays"]

        landmark_reports={}
        for landmark in LANDMARKS:
            risk=icu.copy()
            risk["landmark_time"]=risk["intime"]+pd.to_timedelta(landmark,unit="h")
            risk["horizon_end"]=risk["landmark_time"]+pd.to_timedelta(args.horizon_hours,unit="h")
            risk=risk[risk["outtime"]>risk["landmark_time"]].copy()
            if prevalent:
                risk=risk[~risk["icustay_id"].isin(prevalent)].copy()

            risk["first_disqualifying_time"]=risk["icustay_id"].map(disqual_map)
            risk=risk[
                risk["first_disqualifying_time"].isna()
                | (risk["first_disqualifying_time"]>risk["landmark_time"])
            ].copy()

            risk["event_time"]=risk["icustay_id"].map(event_map)
            risk["is_case"]=(
                risk["event_time"].notna()
                & (risk["event_time"]>risk["landmark_time"])
                & (risk["event_time"]<=risk["horizon_end"])
            )
            risk["fully_observed_control"]=(
                ~risk["is_case"]
                & (risk["outtime"]>=risk["horizon_end"])
            )
            observable=risk[risk["is_case"]|risk["fully_observed_control"]].copy()
            observable["label"]=observable["is_case"].astype(int)

            lo=max(0.0,landmark-args.note_lookback_hours)
            candidate_notes=outcome_notes[
                (outcome_notes["hours_since_icu"]<=landmark)
                & (outcome_notes["hours_since_icu"]>=lo)
            ].copy()
            last_notes=(
                candidate_notes.sort_values(["icustay_id","note_time"])
                .groupby("icustay_id",as_index=False)
                .last()[["icustay_id","note_time","hours_since_icu","category","storetime_available","documentation_delay_hours"]]
            )
            analytic=observable.merge(last_notes,on="icustay_id",how="left",suffixes=("","_note"))
            analytic["has_note"]=analytic["note_time"].notna()
            with_note=analytic[analytic["has_note"]].copy()
            with_note["note_age_at_landmark_hours"]=(
                with_note["landmark_time"]-with_note["note_time"]
            ).dt.total_seconds()/3600.0
            cases_note=with_note[with_note["label"]==1].copy()
            if not cases_note.empty:
                cases_note["note_to_event_hours"]=(
                    cases_note["event_time"]-cases_note["note_time"]
                ).dt.total_seconds()/3600.0

            n_obs=len(observable); n_case=int(observable["label"].sum()); n_ctrl=n_obs-n_case
            n_note=len(with_note); nc_note=int(with_note["label"].sum()); nctrl_note=n_note-nc_note
            landmark_reports[str(int(landmark))]={
                "landmark_hours":float(landmark),
                "at_risk_stays_before_horizon_observability":int(len(risk)),
                "at_risk_unique_patients":int(risk["subject_id"].nunique()),
                "outcome_observable_stays":int(n_obs),
                "outcome_observable_unique_patients":int(observable["subject_id"].nunique()),
                "cases_within_12h":int(n_case),
                "observed_controls":int(n_ctrl),
                "event_prevalence_observable":float(n_case/n_obs) if n_obs else None,
                "note_available_stays":int(n_note),
                "note_available_unique_patients":int(with_note["subject_id"].nunique()),
                "note_available_cases":int(nc_note),
                "note_available_controls":int(nctrl_note),
                "event_prevalence_note_available":float(nc_note/n_note) if n_note else None,
                "note_coverage_observable":float(n_note/n_obs) if n_obs else None,
                "case_note_coverage":float(nc_note/n_case) if n_case else None,
                "control_note_coverage":float(nctrl_note/n_ctrl) if n_ctrl else None,
                "note_age_at_landmark_hours":qstats(with_note["note_age_at_landmark_hours"]),
                "case_note_to_event_hours":qstats(cases_note["note_to_event_hours"] if not cases_note.empty else []),
                "note_lookback_window_hours":[float(lo),float(landmark)],
            }
        report_outcomes[outcome]=landmark_reports

    report={
        "analysis":"Population-representative fixed-landmark feasibility audit v1",
        "protocol":"docs/population_landmark_feasibility_protocol_v1.md",
        "local_only":True,
        "model_inference_performed":False,
        "contains_note_text":False,
        "contains_source_patient_identifiers":False,
        "washout_hours":float(args.washout_hours),
        "prediction_horizon_hours":float(args.horizon_hours),
        "note_lookback_hours":float(args.note_lookback_hours),
        "candidate_landmarks_hours":[float(x) for x in LANDMARKS],
        "prospective_note_time":"max(CHARTTIME, STORETIME) when STORETIME exists; CHARTTIME fallback otherwise",
        "outcomes":report_outcomes,
        "guardrail":"Feasibility counts only. No model is scored and no calibration or decision curve is computed. Any later landmark choice must be frozen before model performance is examined."
    }
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    update_progress(current=6,total=6,phase="done",message="Completed representative landmark feasibility audit",unit="stage")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
