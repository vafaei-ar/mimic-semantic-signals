from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from runrelay_progress import update_progress

OUTCOMES=["invasive_ventilation","renal_replacement_therapy","icu_death"]
SEM=["overall_clinician_concern","worsening_trajectory","respiratory_concern","hemodynamic_concern","poor_treatment_response","escalation_considered","diagnostic_uncertainty","reassuring_stability"]

def load_djev(path):
    rows=[]
    with path.open() as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line)
            if r.get("status")!="ok": continue
            resp=r.get("response",{})
            ans=resp.get("answers",resp) if isinstance(resp,dict) else {}
            z={"case_id":r.get("case_id")}
            for s in SEM:
                a=ans.get(s,{}) if isinstance(ans,dict) else {}
                v=np.nan
                if isinstance(a,dict):
                    if isinstance(a.get("noul"),(int,float)): v=float(a["noul"])
                    elif isinstance(a.get("probability"),(int,float)): v=float(a["probability"])
                    elif isinstance(a.get("confidence"),(int,float)) and isinstance(a.get("value"),bool):
                        v=float(a["confidence"]) if a["value"] else 1-float(a["confidence"])
                z[f"djev_{s}"]=v
            rows.append(z)
    out=pd.DataFrame(rows)
    if out.empty or out.case_id.duplicated().any(): raise RuntimeError("Invalid local djev output")
    if out.drop(columns=["case_id"]).isna().any().any(): raise RuntimeError("Missing djev semantic probabilities")
    return out

def boot(avg,a,b,n,seed):
    from sklearn.metrics import roc_auc_score
    w=avg.pivot_table(index=["case_id","label","match_set"],columns="model",values="probability").dropna(subset=[a,b]).reset_index()
    sets=w.match_set.drop_duplicates().to_numpy(); by={k:g for k,g in w.groupby("match_set",sort=False)}
    obs=float(roc_auc_score(w.label,w[a])-roc_auc_score(w.label,w[b])); rng=np.random.default_rng(seed); vals=[]
    for _ in range(n):
        sm=rng.choice(sets,size=len(sets),replace=True); d=pd.concat([by[k] for k in sm],ignore_index=True)
        vals.append(float(roc_auc_score(d.label,d[a])-roc_auc_score(d.label,d[b])))
    return {"difference":obs,"ci95":[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))],"bootstrap_replicates":n}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--base",required=True); ap.add_argument("--output",required=True); ap.add_argument("--folds",type=int,default=5); ap.add_argument("--repeats",type=int,default=20); ap.add_argument("--bootstrap-replicates",type=int,default=2000); ap.add_argument("--seed",type=int,default=20260923); a=ap.parse_args()
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    base=Path(a.base).resolve(); total=len(OUTCOMES)*a.folds*a.repeats; cur=0; results={}
    for oi,o in enumerate(OUTCOMES):
        d=base/o; df=pd.read_csv(d/"structured_features.csv").merge(load_djev(d/"djev_raw.jsonl"),on="case_id")
        y=df.label.astype(int).to_numpy(); groups=df.match_set.astype(int).to_numpy(); cats=[c for c in ["category","dbsource"] if c in df]; context=[c for c in ["hours_since_icu"] if c in df]+cats; dj=[f"djev_{s}" for s in SEM]
        exc={"case_id","label","match_set","patient_group",*context,*dj}; phys=[c for c in df if c not in exc and pd.api.types.is_numeric_dtype(df[c])]
        models={"djev_8_scores_only":dj,"structured_only":context+phys,"structured_plus_djev":context+phys+dj}
        def pipe(cols):
            cat=[c for c in cols if c in cats]; num=[c for c in cols if c not in cat]; tx=[]
            if num: tx.append(("num",Pipeline([("imp",SimpleImputer(strategy="median",add_indicator=True)),("sc",StandardScaler())]),num))
            if cat: tx.append(("cat",OneHotEncoder(handle_unknown="ignore"),cat))
            return Pipeline([("pre",ColumnTransformer(tx)),("m",LogisticRegression(max_iter=3000,solver="liblinear"))])
        rr=[]; oo=[]
        for r in range(a.repeats):
            cv=StratifiedGroupKFold(n_splits=a.folds,shuffle=True,random_state=a.seed+oi*100+r); preds={m:np.full(len(df),np.nan) for m in models}
            for fold,(tr,te) in enumerate(cv.split(df,y,groups=groups)):
                for name,cols in models.items():
                    p=pipe(cols); p.fit(df.iloc[tr][cols],y[tr]); preds[name][te]=p.predict_proba(df.iloc[te][cols])[:,1]
                cur+=1; update_progress(current=cur,total=total,phase="djev_evaluation",message=f"{o}: repeat {r+1}/{a.repeats}, fold {fold+1}/{a.folds}",unit="fold")
            for name,p in preds.items():
                rr.append({"repeat":r,"model":name,"auroc":float(roc_auc_score(y,p)),"auprc":float(average_precision_score(y,p)),"brier":float(brier_score_loss(y,p))})
                for i,v in enumerate(p): oo.append({"model":name,"case_id":df.iloc[i].case_id,"label":int(y[i]),"match_set":int(df.iloc[i].match_set),"probability":float(v)})
        rep=pd.DataFrame(rr); avg=pd.DataFrame(oo).groupby(["case_id","label","match_set","model"],as_index=False).probability.mean()
        summ=rep.groupby("model").agg(auroc_mean=("auroc","mean"),auroc_sd=("auroc","std"),auprc_mean=("auprc","mean"),brier_mean=("brier","mean")).reset_index().to_dict(orient="records")
        results[o]={"n":len(df),"cases":int(y.sum()),"controls":int((1-y).sum()),"models":summ,"matched_set_bootstrap_auroc_differences":{"structured_plus_djev_minus_structured":boot(avg,"structured_plus_djev","structured_only",a.bootstrap_replicates,a.seed+oi)}}
    report={"analysis":"Local DiffusionGemma-Jev zero-shot evaluation on frozen multitask benchmark","model":"nvidia/diffusiongemma-26B-A4B-it-NVFP4 via local djev-run","local_only":True,"contains_note_text":False,"outcomes":results}
    p=Path(a.output).resolve(); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2))
if __name__=="__main__": main()
