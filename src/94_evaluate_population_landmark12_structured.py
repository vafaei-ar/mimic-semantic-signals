from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from runrelay_progress import update_progress

OUTCOMES=("invasive_ventilation","renal_replacement_therapy","icu_death")
THRESHOLDS=(0.0025,0.005,0.0075,0.01,0.015,0.02,0.03,0.05)
SEED=20260924


def logit(p):
    p=np.clip(np.asarray(p,dtype=float),1e-8,1-1e-8)
    return np.log(p/(1-p))


def calibration_metrics(y,p):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss,log_loss
    z=logit(p).reshape(-1,1)
    m=LogisticRegression(C=1e6,solver="lbfgs",max_iter=3000).fit(z,y)
    tmp=pd.DataFrame({"y":np.asarray(y,dtype=int),"p":np.asarray(p,dtype=float)})
    try:
        tmp["bin"]=pd.qcut(tmp["p"],q=10,duplicates="drop")
    except Exception:
        tmp["bin"]=pd.cut(tmp["p"],bins=10,duplicates="drop")
    tab=(
        tmp.groupby("bin",observed=True)
        .agg(n=("y","size"),mean_pred=("p","mean"),observed=("y","mean"))
        .reset_index(drop=True)
    )
    ece=float(np.sum((tab["n"]/len(tmp))*np.abs(tab["observed"]-tab["mean_pred"])))
    return {
        "brier":float(brier_score_loss(y,p)),
        "log_loss":float(log_loss(y,np.clip(p,1e-8,1-1e-8),labels=[0,1])),
        "calibration_intercept":float(m.intercept_[0]),
        "calibration_slope":float(m.coef_[0][0]),
        "ece_10_quantile_bins":ece,
        "calibration_bins":[
            {"n":int(r.n),"mean_pred":float(r.mean_pred),"observed":float(r.observed)}
            for r in tab.itertuples(index=False)
        ],
    }


def decision_curve(y,p):
    y=np.asarray(y,dtype=int); p=np.asarray(p,dtype=float); n=len(y)
    prevalence=float(y.mean())
    out={}
    for pt in THRESHOLDS:
        pred=p>=pt
        tp=int(np.sum(pred&(y==1)))
        fp=int(np.sum(pred&(y==0)))
        nb=float(tp/n-(fp/n)*(pt/(1-pt)))
        all_nb=float(prevalence-(1-prevalence)*(pt/(1-pt)))
        out[f"{pt:.4f}"]={
            "threshold_probability":float(pt),
            "model_net_benefit":nb,
            "treat_all_net_benefit":all_nb,
            "treat_none_net_benefit":0.0,
            "classified_positive":int(pred.sum()),
            "classified_positive_fraction":float(pred.mean()),
            "true_positives":tp,
            "false_positives":fp,
        }
    return out


def basic_metrics(y,p):
    from sklearn.metrics import average_precision_score,roc_auc_score
    out={
        "auroc":float(roc_auc_score(y,p)),
        "auprc":float(average_precision_score(y,p)),
    }
    out.update(calibration_metrics(y,p))
    out["decision_curve"]=decision_curve(y,p)
    return out


def bootstrap_patient_cluster(df,n_boot):
    from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss
    patients=df["subject_id"].drop_duplicates().to_numpy()
    by={k:g for k,g in df.groupby("subject_id",sort=False)}
    rng=np.random.default_rng(SEED)
    scalar_keys=["auroc","auprc","brier","calibration_intercept","calibration_slope"]
    vals={k:[] for k in scalar_keys}
    nb={f"{pt:.4f}":[] for pt in THRESHOLDS}

    for _ in range(n_boot):
        sampled=rng.choice(patients,size=len(patients),replace=True)
        pieces=[]
        for j,pid in enumerate(sampled):
            g=by[pid].copy()
            g["_boot_patient_instance"]=j
            pieces.append(g)
        b=pd.concat(pieces,ignore_index=True)
        y=b["label"].to_numpy(dtype=int)
        p=b["prediction"].to_numpy(dtype=float)
        if len(np.unique(y))<2:
            continue
        vals["auroc"].append(float(roc_auc_score(y,p)))
        vals["auprc"].append(float(average_precision_score(y,p)))
        vals["brier"].append(float(brier_score_loss(y,p)))
        cm=calibration_metrics(y,p)
        vals["calibration_intercept"].append(cm["calibration_intercept"])
        vals["calibration_slope"].append(cm["calibration_slope"])
        dc=decision_curve(y,p)
        for key in nb:
            nb[key].append(dc[key]["model_net_benefit"])

    def ci(x):
        a=np.asarray(x,dtype=float)
        return [float(np.quantile(a,.025)),float(np.quantile(a,.975))]
    return {
        "replicates_requested":int(n_boot),
        "replicates_used":int(len(vals["auroc"])),
        "cluster":"source_patient",
        "metrics_ci95":{k:ci(v) for k,v in vals.items()},
        "decision_curve_model_net_benefit_ci95":{k:ci(v) for k,v in nb.items()},
    }


def main():
    ap=argparse.ArgumentParser(description="Population structured cross-fitted calibration and decision curve.")
    ap.add_argument("--base",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--folds",type=int,default=5)
    ap.add_argument("--bootstrap-replicates",type=int,default=1000)
    args=ap.parse_args()

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score,roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    base=Path(args.base).expanduser().resolve()
    out_path=Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True,exist_ok=True)

    report={
        "analysis":"Population-representative structured calibration and decision-curve analysis v1",
        "protocol":"docs/population_landmark12_structured_calibration_protocol_v1.md",
        "local_only":True,
        "contains_source_patient_identifiers":False,
        "contains_row_level_predictions":False,
        "landmark_hours":12.0,
        "prediction_horizon_hours":12.0,
        "cross_fitting":{"folds":int(args.folds),"group":"source_patient","class_weight":None},
        "decision_thresholds":[float(x) for x in THRESHOLDS],
        "bootstrap_replicates":int(args.bootstrap_replicates),
        "outcomes":{},
    }

    total=len(OUTCOMES)*args.folds
    cur=0
    for oi,outcome in enumerate(OUTCOMES):
        d=base/outcome
        df=pd.read_csv(d/"structured_features_local.csv",low_memory=False)
        required={"case_id","subject_id","label"}
        if not required.issubset(df.columns):
            raise RuntimeError(f"{outcome}: missing required columns {sorted(required-set(df.columns))}")
        feature_cols=[
            c for c in df.columns
            if c not in {"case_id","subject_id","icustay_id","label","has_note"}
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        if len(feature_cols)!=11:
            raise RuntimeError(f"{outcome}: expected 11 structured features, found {len(feature_cols)}")

        y=df["label"].astype(int).to_numpy()
        groups=df["subject_id"].to_numpy()
        pred=np.full(len(df),np.nan,dtype=float)
        fold_summaries=[]
        cv=StratifiedGroupKFold(
            n_splits=args.folds,
            shuffle=True,
            random_state=SEED+oi*100,
        )
        for fold,(tr,te) in enumerate(cv.split(df,y,groups=groups),start=1):
            model=Pipeline([
                ("impute",SimpleImputer(strategy="median",add_indicator=True)),
                ("scale",StandardScaler()),
                ("model",LogisticRegression(
                    max_iter=3000,solver="liblinear",C=1.0,class_weight=None
                )),
            ])
            model.fit(df.iloc[tr][feature_cols],y[tr])
            pred[te]=model.predict_proba(df.iloc[te][feature_cols])[:,1]
            fold_summaries.append({
                "fold":fold,
                "train_n":int(len(tr)),
                "test_n":int(len(te)),
                "train_cases":int(y[tr].sum()),
                "test_cases":int(y[te].sum()),
                "test_unique_patients":int(pd.Series(groups[te]).nunique()),
            })
            cur+=1
            update_progress(
                current=cur,total=total,phase="population_structured_crossfit",
                message=f"{outcome}: fold {fold}/{args.folds}",unit="fold"
            )
        if np.isnan(pred).any():
            raise RuntimeError(f"{outcome}: incomplete out-of-fold predictions")

        eval_df=df[["subject_id","label"]].copy()
        eval_df["prediction"]=pred
        metrics=basic_metrics(y,pred)
        boot=bootstrap_patient_cluster(eval_df,args.bootstrap_replicates)

        report["outcomes"][outcome]={
            "n":int(len(df)),
            "cases":int(y.sum()),
            "controls":int(len(y)-y.sum()),
            "prevalence":float(y.mean()),
            "feature_names":feature_cols,
            "folds":fold_summaries,
            "metrics":metrics,
            "bootstrap":boot,
        }

    report["guardrail"]=(
        "All predictions are patient-grouped out-of-fold predictions in prevalence-preserving cohorts. "
        "Decision-curve net benefit is exploratory and does not prescribe treatment thresholds. "
        "No semantic scores were used."
    )
    out_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
