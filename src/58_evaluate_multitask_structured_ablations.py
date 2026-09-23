from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress

OUTCOMES = ["invasive_ventilation", "renal_replacement_therapy", "icu_death"]

VITAL_GROUPS = {
    "heart_rate": ["heart_rate_last", "heart_rate_delta"],
    "map": ["map_last", "map_delta"],
    "resp_rate": ["resp_rate_last", "resp_rate_delta"],
    "spo2": ["spo2_last", "spo2_delta"],
}
LABS = ["lactate_last", "creatinine_last", "wbc_last"]
CONTEXT_NUM = ["hours_since_icu"]
CONTEXT_CAT = ["category", "dbsource"]


def bootstrap_auc_diff(avg: pd.DataFrame, a: str, b: str, n_boot: int, seed: int) -> dict:
    from sklearn.metrics import roc_auc_score
    wide = avg.pivot_table(index=["case_id", "label", "match_set"], columns="model", values="probability").dropna(subset=[a,b]).reset_index()
    sets = wide["match_set"].drop_duplicates().to_numpy()
    by_set = {k:g for k,g in wide.groupby("match_set", sort=False)}
    observed = float(roc_auc_score(wide["label"], wide[a]) - roc_auc_score(wide["label"], wide[b]))
    rng = np.random.default_rng(seed)
    vals=[]
    for _ in range(n_boot):
        sampled=rng.choice(sets, size=len(sets), replace=True)
        d=pd.concat([by_set[k] for k in sampled], ignore_index=True)
        vals.append(float(roc_auc_score(d["label"], d[a]) - roc_auc_score(d["label"], d[b])))
    return {"difference": observed, "ci95":[float(np.quantile(vals,.025)), float(np.quantile(vals,.975))], "bootstrap_replicates":n_boot, "cluster":"match_set"}


def evaluate(outcome: str, path: Path, folds: int, repeats: int, n_boot: int, seed: int, offset: int, total: int) -> dict:
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    df=pd.read_csv(path)
    y=df["label"].astype(int).to_numpy()
    groups=df["match_set"].astype(int).to_numpy()
    cats=[c for c in CONTEXT_CAT if c in df]
    context=[c for c in CONTEXT_NUM if c in df] + cats
    vitals=[c for cols in VITAL_GROUPS.values() for c in cols if c in df]
    labs=[c for c in LABS if c in df]
    all_struct=context+vitals+labs

    models={
        "context_only": context,
        "vitals_only": context+vitals,
        "labs_only": context+labs,
        "creatinine_only": context+(["creatinine_last"] if "creatinine_last" in df else []),
        "all_structured": all_struct,
        "all_minus_creatinine": [c for c in all_struct if c!="creatinine_last"],
        "all_minus_labs": [c for c in all_struct if c not in labs],
    }
    for g, cols in VITAL_GROUPS.items():
        use=[c for c in cols if c in df]
        if use:
            models[f"{g}_only"]=context+use

    def pipe(cols: list[str], indicators: bool=True):
        cat=[c for c in cols if c in cats]
        num=[c for c in cols if c not in cat]
        tx=[]
        if num:
            tx.append(("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=indicators)), ("scale", StandardScaler())]), num))
        if cat:
            tx.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat))
        return Pipeline([("pre", ColumnTransformer(tx, remainder="drop")), ("model", LogisticRegression(max_iter=3000, solver="liblinear", C=1.0))])

    specs={name:(cols, True) for name,cols in models.items()}
    specs["all_structured_no_missing_indicators"]=(all_struct, False)
    specs["creatinine_only_no_missing_indicator"]=(models["creatinine_only"], False)

    rep_rows=[]; oof=[]
    current=offset
    for r in range(repeats):
        cv=StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed+r)
        preds={m:np.full(len(df), np.nan) for m in specs}
        for fold,(tr,te) in enumerate(cv.split(df,y,groups=groups)):
            for name,(cols,ind) in specs.items():
                p=pipe(cols, ind)
                p.fit(df.iloc[tr][cols], y[tr])
                preds[name][te]=p.predict_proba(df.iloc[te][cols])[:,1]
            current+=1
            update_progress(current=current,total=total,phase="structured_ablation",message=f"{outcome}: repeat {r+1}/{repeats}, fold {fold+1}/{folds}",unit="fold")
        for name,pred in preds.items():
            rep_rows.append({"repeat":r,"model":name,"auroc":float(roc_auc_score(y,pred)),"auprc":float(average_precision_score(y,pred)),"brier":float(brier_score_loss(y,pred))})
            for i,v in enumerate(pred):
                oof.append({"repeat":r,"model":name,"case_id":df.iloc[i]["case_id"],"label":int(y[i]),"match_set":int(df.iloc[i]["match_set"]),"probability":float(v)})

    rep=pd.DataFrame(rep_rows)
    avg=pd.DataFrame(oof).groupby(["case_id","label","match_set","model"],as_index=False)["probability"].mean()
    summary=rep.groupby("model").agg(auroc_mean=("auroc","mean"),auroc_sd=("auroc","std"),auprc_mean=("auprc","mean"),brier_mean=("brier","mean")).reset_index().to_dict(orient="records")
    comparisons={}
    for j,(a,b) in enumerate([
        ("all_structured","all_minus_creatinine"),
        ("all_structured","all_minus_labs"),
        ("all_structured","all_structured_no_missing_indicators"),
        ("creatinine_only","context_only"),
        ("labs_only","vitals_only"),
    ]):
        comparisons[f"{a}_minus_{b}"]=bootstrap_auc_diff(avg,a,b,n_boot,seed+1000+j)
    return {
        "n":int(len(df)),"cases":int(y.sum()),"controls":int((1-y).sum()),
        "feature_groups":{"context":context,"vitals":vitals,"labs":labs},
        "models":summary,
        "matched_set_bootstrap_auroc_differences":comparisons,
        "guardrail":"Ablations explain structured discrimination only; they do not alter the frozen endpoint or cohort."
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True); ap.add_argument("--output",required=True)
    ap.add_argument("--folds",type=int,default=5); ap.add_argument("--repeats",type=int,default=20)
    ap.add_argument("--bootstrap-replicates",type=int,default=2000); ap.add_argument("--seed",type=int,default=20260923)
    a=ap.parse_args()
    base=Path(a.base).expanduser().resolve()
    total=len(OUTCOMES)*a.folds*a.repeats
    results={}; offset=0
    for j,o in enumerate(OUTCOMES):
        results[o]=evaluate(o,base/o/"structured_features.csv",a.folds,a.repeats,a.bootstrap_replicates,a.seed+100*j,offset,total)
        offset+=a.folds*a.repeats
    report={"analysis":"Frozen multitask structured-feature ablation","local_only":True,"contains_patient_identifiers":False,"outcomes":results}
    out=Path(a.output).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
