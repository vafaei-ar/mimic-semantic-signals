from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress


def load_builder():
    path=Path(__file__).with_name("54_build_multitask_benchmark.py")
    spec=importlib.util.spec_from_file_location("frozen_multitask_builder_pop_features",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen multitask benchmark builder.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def read_population(local_root: Path):
    frames=[]
    for outcome in ("invasive_ventilation","renal_replacement_therapy","icu_death"):
        path=local_root/outcome/"population_index_local.csv"
        df=pd.read_csv(path,low_memory=False)
        required={"case_id","subject_id","hadm_id","icustay_id","label","landmark_time"}
        missing=required-set(df.columns)
        if missing:
            raise RuntimeError(f"{path}: missing columns {sorted(missing)}")
        df["outcome"]=outcome
        df["landmark_time"]=pd.to_datetime(df["landmark_time"],errors="coerce")
        if df["landmark_time"].isna().any():
            raise RuntimeError(f"{path}: invalid landmark times")
        frames.append(df)
    return pd.concat(frames,ignore_index=True)


def build_feature_map(item_groups):
    out={}
    for name,ids in item_groups.items():
        for itemid in ids:
            out[int(itemid)]=name
    return out


def main():
    ap=argparse.ArgumentParser(description="Build structured features at frozen 12-hour population landmark.")
    ap.add_argument("--root",required=True)
    ap.add_argument("--local-root",required=True)
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--vital-lookback-hours",type=float,default=6.0)
    ap.add_argument("--lab-lookback-hours",type=float,default=24.0)
    args=ap.parse_args()

    mod=load_builder()
    root=mod.resolve_root(args.root)
    local_root=Path(args.local_root).expanduser().resolve()
    manifest_path=Path(args.manifest).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True,exist_ok=True)

    pop=read_population(local_root)
    unique=(
        pop[["icustay_id","hadm_id","landmark_time"]]
        .drop_duplicates()
        .copy()
    )
    if unique["icustay_id"].duplicated().any():
        # Same ICU stay must have the same admission and landmark across outcomes.
        dup=unique[unique["icustay_id"].duplicated(keep=False)].sort_values("icustay_id")
        raise RuntimeError(f"Inconsistent duplicate ICU-stay landmarks: {len(dup)} rows")

    unique["icustay_id"]=pd.to_numeric(unique["icustay_id"],errors="raise").astype("int64")
    unique["hadm_id"]=pd.to_numeric(unique["hadm_id"],errors="raise").astype("int64")
    icu_ids=set(unique["icustay_id"].tolist())
    hadm_ids=set(unique["hadm_id"].tolist())

    update_progress(current=1,total=4,phase="vitals",message="Scanning frozen vital item ids at the 12-hour landmark",unit="stage")
    vital_map=build_feature_map(mod.VITAL_ITEMIDS)
    chart=mod.find_file(mod.module_path(root,"mimiciii"),["CHARTEVENTS.csv.gz","CHARTEVENTS.csv"])
    vital_rows=[]
    if chart is not None:
        lookup=unique[["icustay_id","hadm_id","landmark_time"]]
        for chunk in mod.read_columns(
            chart,
            ["hadm_id","icustay_id","itemid","charttime","valuenum","error"],
            chunksize=500_000,
        ):
            c=mod.lower_columns(chunk)
            c["icustay_id"]=pd.to_numeric(c["icustay_id"],errors="coerce")
            c["hadm_id"]=pd.to_numeric(c["hadm_id"],errors="coerce")
            c=c[c["icustay_id"].isin(icu_ids)&c["hadm_id"].isin(hadm_ids)].copy()
            if c.empty: continue
            c["itemid"]=pd.to_numeric(c["itemid"],errors="coerce")
            c=c[c["itemid"].isin(vital_map)].copy()
            if "error" in c.columns:
                c=c[c["error"].fillna(0).astype(str)!="1"]
            c["charttime"]=mod.parse_datetime(c["charttime"])
            c["valuenum"]=pd.to_numeric(c["valuenum"],errors="coerce")
            c=c.dropna(subset=["icustay_id","hadm_id","itemid","charttime","valuenum"])
            if c.empty: continue
            c["icustay_id"]=c["icustay_id"].astype("int64")
            c["hadm_id"]=c["hadm_id"].astype("int64")
            c=c.merge(lookup,on=["icustay_id","hadm_id"],how="inner")
            c=c[
                (c["charttime"]<=c["landmark_time"])
                &(c["charttime"]>=c["landmark_time"]-pd.to_timedelta(args.vital_lookback_hours,unit="h"))
            ].copy()
            if c.empty: continue
            c["feature"]=c["itemid"].astype(int).map(vital_map)
            vital_rows.append(c[["icustay_id","feature","charttime","valuenum"]])

    vitals=pd.concat(vital_rows,ignore_index=True) if vital_rows else pd.DataFrame(
        columns=["icustay_id","feature","charttime","valuenum"]
    )

    update_progress(current=2,total=4,phase="labs",message="Scanning frozen laboratory item ids at the 12-hour landmark",unit="stage")
    lab_map=build_feature_map(mod.LAB_ITEMIDS)
    lab=mod.find_file(mod.module_path(root,"mimiciii"),["LABEVENTS.csv.gz","LABEVENTS.csv"])
    lab_rows=[]
    if lab is not None:
        lookup_h=unique[["icustay_id","hadm_id","landmark_time"]]
        for chunk in mod.read_columns(
            lab,
            ["hadm_id","itemid","charttime","valuenum"],
            chunksize=500_000,
        ):
            c=mod.lower_columns(chunk)
            c["hadm_id"]=pd.to_numeric(c["hadm_id"],errors="coerce")
            c=c[c["hadm_id"].isin(hadm_ids)].copy()
            if c.empty: continue
            c["itemid"]=pd.to_numeric(c["itemid"],errors="coerce")
            c=c[c["itemid"].isin(lab_map)].copy()
            c["charttime"]=mod.parse_datetime(c["charttime"])
            c["valuenum"]=pd.to_numeric(c["valuenum"],errors="coerce")
            c=c.dropna(subset=["hadm_id","itemid","charttime","valuenum"])
            if c.empty: continue
            c["hadm_id"]=c["hadm_id"].astype("int64")
            c=c.merge(lookup_h,on="hadm_id",how="inner")
            c=c[
                (c["charttime"]<=c["landmark_time"])
                &(c["charttime"]>=c["landmark_time"]-pd.to_timedelta(args.lab_lookback_hours,unit="h"))
            ].copy()
            if c.empty: continue
            c["feature"]=c["itemid"].astype(int).map(lab_map)
            lab_rows.append(c[["icustay_id","feature","charttime","valuenum"]])

    labs=pd.concat(lab_rows,ignore_index=True) if lab_rows else pd.DataFrame(
        columns=["icustay_id","feature","charttime","valuenum"]
    )

    update_progress(current=3,total=4,phase="aggregate",message="Aggregating landmark physiology and laboratory features",unit="stage")
    feat=pd.DataFrame({"icustay_id":sorted(icu_ids)})

    for name in mod.VITAL_ITEMIDS:
        x=vitals[vitals["feature"]==name].sort_values(["icustay_id","charttime"])
        if x.empty:
            last=pd.Series(dtype=float); delta=pd.Series(dtype=float)
        else:
            g=x.groupby("icustay_id")["valuenum"]
            last=g.last()
            delta=g.last()-g.first()
            counts=g.size()
            delta=delta.where(counts>=2,np.nan)
        feat=feat.merge(last.rename(f"{name}_last"),left_on="icustay_id",right_index=True,how="left")
        feat=feat.merge(delta.rename(f"{name}_delta"),left_on="icustay_id",right_index=True,how="left")

    for name in mod.LAB_ITEMIDS:
        x=labs[labs["feature"]==name].sort_values(["icustay_id","charttime"])
        last=x.groupby("icustay_id")["valuenum"].last() if not x.empty else pd.Series(dtype=float)
        feat=feat.merge(last.rename(f"{name}_last"),left_on="icustay_id",right_index=True,how="left")

    feature_cols=[c for c in feat.columns if c!="icustay_id"]
    outcome_reports={}
    for outcome,g in pop.groupby("outcome",sort=False):
        outdir=local_root/outcome
        safe=g[["case_id","subject_id","icustay_id","label","has_note"]].merge(feat,on="icustay_id",how="left")
        if len(safe)!=len(g):
            raise RuntimeError(f"{outcome}: feature merge changed row count")
        safe.to_csv(outdir/"structured_features_local.csv",index=False)

        overall_missing=float(safe[feature_cols].isna().mean().mean())
        case_mask=safe["label"].astype(int)==1
        outcome_reports[outcome]={
            "rows":int(len(safe)),
            "cases":int(case_mask.sum()),
            "controls":int((~case_mask).sum()),
            "feature_count":int(len(feature_cols)),
            "overall_feature_missing_fraction":overall_missing,
            "case_feature_missing_fraction":float(safe.loc[case_mask,feature_cols].isna().mean().mean()),
            "control_feature_missing_fraction":float(safe.loc[~case_mask,feature_cols].isna().mean().mean()),
            "rows_with_all_features_missing":int(safe[feature_cols].isna().all(axis=1).sum()),
            "per_feature_nonmissing_fraction":{
                c:float(safe[c].notna().mean()) for c in feature_cols
            },
            "local_feature_file":str(outdir/"structured_features_local.csv"),
        }

    update_progress(current=4,total=4,phase="done",message="Completed structured population landmark features",unit="stage")
    report={
        "analysis":"Frozen 12-hour population landmark structured feature extraction v1",
        "cohort_protocol":"docs/population_landmark12_cohort_protocol_v1.md",
        "cohort_manifest_sha256":"c629dd0e51bfe83a76db451b2ff4e05883880d2c5be3ea5863c8d1438c29dc72",
        "local_only":True,
        "contains_source_patient_identifiers":False,
        "contains_row_level_features":False,
        "model_inference_performed":False,
        "landmark_hours":12.0,
        "vital_lookback_hours":float(args.vital_lookback_hours),
        "lab_lookback_hours":float(args.lab_lookback_hours),
        "feature_names":feature_cols,
        "unique_icu_stays_processed":int(len(feat)),
        "outcomes":outcome_reports,
        "guardrail":"Aggregate feature-availability summary only. Row-level features and patient grouping remain local. No predictive model was fitted or scored."
    }
    manifest_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
