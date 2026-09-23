from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from runrelay_progress import update_progress

OUTCOMES=["invasive_ventilation","renal_replacement_therapy","icu_death"]
SEM=["overall_clinician_concern","worsening_trajectory","respiratory_concern","hemodynamic_concern","poor_treatment_response","escalation_considered","diagnostic_uncertainty","reassuring_stability"]

def load_sem(path,prefix):
    rows=[]
    for line in path.read_text().splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        if r.get("status")!="ok": continue
        z={"case_id":r["case_id"]}
        ans=r.get("response",{}).get("answers",{})
        for s in SEM:
            a=ans.get(s,{})
            vals=a.get("chunk_values") if isinstance(a,dict) else None
            z[f"{prefix}_{s}"]=float(np.mean(vals)) if isinstance(vals,list) and vals else float(a.get("noul",np.nan))
        rows.append(z)
    return pd.DataFrame(rows)

def cal_metrics(y,p):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss
    q=np.clip(np.asarray(p),1e-6,1-1e-6); logit=np.log(q/(1-q)).reshape(-1,1)
    m=LogisticRegression(C=1e6,solver="lbfgs",max_iter=2000).fit(logit,y)
    bins=pd.qcut(pd.Series(q),q=10,duplicates="drop")
    tmp=pd.DataFrame({"y":y,"p":q,"bin":bins})
    tab=tmp.groupby("bin",observed=True).agg(n=("y","size"),mean_pred=("p","mean"),observed=("y","mean")).reset_index(drop=True)
    ece=float(np.sum(tab["n"]/len(tmp)*np.abs(tab["observed"]-tab["mean_pred"])))
    return {"calibration_intercept_sampled":float(m.intercept_[0]),"calibration_slope":float(m.coef_[0][0]),"brier_sampled":float(brier_score_loss(y,q)),"ece_sampled":ece}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--base",required=True); ap.add_argument("--output",required=True); ap.add_argument("--folds",type=int,default=5); ap.add_argument("--repeats",type=int,default=10); ap.add_argument("--seed",type=int,default=20260923); a=ap.parse_args()
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    base=Path(a.base).expanduser().resolve(); total=len(OUTCOMES)*a.folds*a.repeats; cur=0; outc={}
    for oi,o in enumerate(OUTCOMES):
        d=base/o; df=pd.read_csv(d/"structured_features.csv").merge(load_sem(d/"open_jev_raw.jsonl","openjev"),on="case_id").merge(load_sem(d/"laya_raw.jsonl","laya"),on="case_id")
        y=df.label.astype(int).to_numpy(); groups=df.match_set.astype(int).to_numpy(); cats=[c for c in ["category","dbsource"] if c in df]; context=[c for c in ["hours_since_icu"] if c in df]+cats
        oj=[f"openjev_{s}" for s in SEM]; ly=[f"laya_{s}" for s in SEM]; exc={"case_id","label","match_set","patient_group",*context,*oj,*ly}
        phys=[c for c in df if c not in exc and pd.api.types.is_numeric_dtype(df[c])]; models={"structured":context+phys,"structured_plus_openjev":context+phys+oj,"structured_plus_laya":context+phys+ly}
        def pipe(cols):
            cat=[c for c in cols if c in cats]; num=[c for c in cols if c not in cat]; tx=[]
            if num: tx.append(("num",Pipeline([("imp",SimpleImputer(strategy="median",add_indicator=True)),("sc",StandardScaler())]),num))
            if cat: tx.append(("cat",OneHotEncoder(handle_unknown="ignore"),cat))
            return Pipeline([("pre",ColumnTransformer(tx)),("m",LogisticRegression(max_iter=3000,solver="liblinear"))])
        rep={m:[] for m in models}
        for r in range(a.repeats):
            cv=StratifiedGroupKFold(n_splits=a.folds,shuffle=True,random_state=a.seed+oi*100+r); pred={m:np.full(len(df),np.nan) for m in models}
            for fold,(tr,te) in enumerate(cv.split(df,y,groups=groups)):
                for name,cols in models.items():
                    p=pipe(cols); p.fit(df.iloc[tr][cols],y[tr]); pred[name][te]=p.predict_proba(df.iloc[te][cols])[:,1]
                cur+=1; update_progress(current=cur,total=total,phase="sampling_calibration",message=f"{o}: repeat {r+1}/{a.repeats}, fold {fold+1}/{a.folds}",unit="fold")
            for name in models: rep[name].append(cal_metrics(y,pred[name]))
        outc[o]={name:{k:float(np.mean([x[k] for x in vals])) for k in vals[0]} for name,vals in rep.items()}
    report={"analysis":"Sampled-design calibration diagnostics on frozen matched cohorts","warning":"These 1:3 matched case-control cohorts have an artificial 25% prevalence. Calibration intercept, Brier score, ECE, and decision-curve net benefit are not population-risk estimates. Calibration slope is reported as a model-stability diagnostic only. True clinical utility requires a prevalence-representative risk-set cohort or validated prevalence weights.","local_only":True,"outcomes":outc}
    p=Path(a.output).expanduser().resolve(); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2))
if __name__=="__main__": main()
