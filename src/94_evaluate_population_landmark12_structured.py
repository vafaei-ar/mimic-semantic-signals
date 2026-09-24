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


def _weighted_calibration(y,p,w):
    z=logit(p)
    y=np.asarray(y,dtype=float)
    w=np.asarray(w,dtype=float)
    beta=np.array([0.0,1.0],dtype=float)
    for _ in range(50):
        eta=beta[0]+beta[1]*z
        eta=np.clip(eta,-40.0,40.0)
        mu=1.0/(1.0+np.exp(-eta))
        resid=w*(y-mu)
        grad=np.array([resid.sum(),np.dot(resid,z)],dtype=float)
        v=w*mu*(1.0-mu)
        h00=v.sum()
        h01=np.dot(v,z)
        h11=np.dot(v,z*z)
        h=np.array([[h00,h01],[h01,h11]],dtype=float)
        if not np.all(np.isfinite(h)) or np.linalg.det(h)<=1e-12:
            break
        step=np.linalg.solve(h,grad)
        beta_new=beta+step
        if np.max(np.abs(step))<1e-9:
            beta=beta_new
            break
        beta=beta_new
    return float(beta[0]),float(beta[1])


def _prepare_weighted_rank_metrics(y,p):
    y=np.asarray(y,dtype=int)
    p=np.asarray(p,dtype=float)

    order_asc=np.argsort(p,kind="mergesort")
    p_asc=p[order_asc]
    y_asc=y[order_asc]
    starts_asc=np.r_[0,np.flatnonzero(np.diff(p_asc)!=0)+1]

    order_desc=order_asc[::-1]
    p_desc=p[order_desc]
    y_desc=y[order_desc]
    starts_desc=np.r_[0,np.flatnonzero(np.diff(p_desc)!=0)+1]

    return {
        "order_asc":order_asc,
        "y_asc":y_asc,
        "starts_asc":starts_asc,
        "order_desc":order_desc,
        "y_desc":y_desc,
        "starts_desc":starts_desc,
    }


def _weighted_auc_ap(prepared,w):
    w=np.asarray(w,dtype=float)

    wa=w[prepared["order_asc"]]
    ya=prepared["y_asc"]
    gp=np.add.reduceat(wa*ya,prepared["starts_asc"])
    gn=np.add.reduceat(wa*(1-ya),prepared["starts_asc"])
    total_pos=gp.sum()
    total_neg=gn.sum()
    if total_pos<=0 or total_neg<=0:
        return None,None
    cum_neg_before=np.cumsum(gn)-gn
    auc=float(np.sum(gp*(cum_neg_before+0.5*gn))/(total_pos*total_neg))

    wd=w[prepared["order_desc"]]
    yd=prepared["y_desc"]
    gp_d=np.add.reduceat(wd*yd,prepared["starts_desc"])
    gn_d=np.add.reduceat(wd*(1-yd),prepared["starts_desc"])
    cum_tp=np.cumsum(gp_d)
    cum_fp=np.cumsum(gn_d)
    precision=np.divide(
        cum_tp,cum_tp+cum_fp,
        out=np.ones_like(cum_tp,dtype=float),
        where=(cum_tp+cum_fp)>0,
    )
    recall_inc=gp_d/total_pos
    ap=float(np.sum(recall_inc*precision))
    return auc,ap


def bootstrap_patient_cluster(df,n_boot,*,progress_base,total_progress,outcome,checkpoint=None):
    y=df["label"].to_numpy(dtype=int)
    p=df["prediction"].to_numpy(dtype=float)
    patient_codes,patients=pd.factorize(df["subject_id"],sort=False)
    n_patients=len(patients)
    rng=np.random.default_rng(SEED)

    prepared=_prepare_weighted_rank_metrics(y,p)
    squared_error=(p-y.astype(float))**2
    threshold_masks={f"{pt:.4f}":(p>=pt) for pt in THRESHOLDS}

    scalar_keys=["auroc","auprc","brier","calibration_intercept","calibration_slope"]
    vals={k:[] for k in scalar_keys}
    nb={f"{pt:.4f}":[] for pt in THRESHOLDS}

    for b in range(n_boot):
        sampled=rng.integers(0,n_patients,size=n_patients)
        patient_mult=np.bincount(sampled,minlength=n_patients).astype(float)
        w=patient_mult[patient_codes]
        n_eff=float(w.sum())
        pos=float(np.dot(w,y))
        neg=n_eff-pos
        if pos<=0 or neg<=0:
            continue

        auc,ap=_weighted_auc_ap(prepared,w)
        if auc is None or ap is None:
            continue
        vals["auroc"].append(float(auc))
        vals["auprc"].append(float(ap))
        vals["brier"].append(float(np.dot(w,squared_error)/n_eff))
        intercept,slope=_weighted_calibration(y,p,w)
        vals["calibration_intercept"].append(intercept)
        vals["calibration_slope"].append(slope)

        for pt in THRESHOLDS:
            key=f"{pt:.4f}"
            mask=threshold_masks[key]
            tp=float(np.dot(w,mask&(y==1)))
            fp=float(np.dot(w,mask&(y==0)))
            nb[key].append(float(tp/n_eff-(fp/n_eff)*(pt/(1-pt))))

        if (b+1)%25==0 or (b+1)==n_boot:
            update_progress(
                current=progress_base+b+1,
                total=total_progress,
                phase="population_structured_bootstrap",
                message=f"{outcome}: bootstrap {b+1}/{n_boot}",
                unit="bootstrap",
            )
            if checkpoint is not None:
                checkpoint()

    def ci(x):
        a=np.asarray(x,dtype=float)
        return [float(np.quantile(a,.025)),float(np.quantile(a,.975))]
    return {
        "replicates_requested":int(n_boot),
        "replicates_used":int(len(vals["auroc"])),
        "cluster":"source_patient",
        "implementation":"patient multiplicity weights; fixed predictions; weighted rank metrics and two-parameter Newton calibration",
        "metrics_ci95":{k:ci(v) for k,v in vals.items()},
        "decision_curve_model_net_benefit_ci95":{k:ci(v) for k,v in nb.items()},
    }


def _self_check_weighted_bootstrap_math():
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score,brier_score_loss,roc_auc_score

    y=np.array([0,1,0,1,0,1,0,1],dtype=int)
    p=np.array([0.05,0.80,0.20,0.65,0.40,0.55,0.10,0.90],dtype=float)
    patient_codes=np.array([0,0,1,2,2,3,4,4],dtype=int)
    patient_mult=np.array([2,0,1,3,1],dtype=int)
    w=patient_mult[patient_codes].astype(float)
    idx=np.repeat(np.arange(len(y)),w.astype(int))

    prepared=_prepare_weighted_rank_metrics(y,p)
    auc_fast,ap_fast=_weighted_auc_ap(prepared,w)
    auc_exact=float(roc_auc_score(y[idx],p[idx]))
    ap_exact=float(average_precision_score(y[idx],p[idx]))
    brier_fast=float(np.dot(w,(p-y.astype(float))**2)/w.sum())
    brier_exact=float(brier_score_loss(y[idx],p[idx]))

    z=logit(p).reshape(-1,1)
    exact=LogisticRegression(C=1e6,solver="lbfgs",max_iter=3000).fit(z[idx],y[idx])
    ci_fast,cs_fast=_weighted_calibration(y,p,w)

    checks=[
        abs(auc_fast-auc_exact)<1e-12,
        abs(ap_fast-ap_exact)<1e-12,
        abs(brier_fast-brier_exact)<1e-12,
        abs(ci_fast-float(exact.intercept_[0]))<1e-4,
        abs(cs_fast-float(exact.coef_[0][0]))<1e-4,
    ]
    if not all(checks):
        raise RuntimeError(
            "Optimized weighted bootstrap failed equivalence self-check: "
            f"auc={auc_fast}/{auc_exact}, ap={ap_fast}/{ap_exact}, "
            f"brier={brier_fast}/{brier_exact}, "
            f"cal={ci_fast},{cs_fast}/{exact.intercept_[0]},{exact.coef_[0][0]}"
        )

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

    _self_check_weighted_bootstrap_math()

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

    total=len(OUTCOMES)*(args.folds+args.bootstrap_replicates)
    cur=0

    def write_checkpoint(status):
        tmp=dict(report)
        tmp["status"]=status
        out_path.write_text(json.dumps(tmp,indent=2)+"\\n",encoding="utf-8")
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
        fold_progress=(oi+1)*args.folds+oi*args.bootstrap_replicates
        boot=bootstrap_patient_cluster(
            eval_df,
            args.bootstrap_replicates,
            progress_base=fold_progress,
            total_progress=total,
            outcome=outcome,
            checkpoint=lambda: write_checkpoint("running"),
        )
        cur=fold_progress+args.bootstrap_replicates

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
    report["status"]="completed"
    out_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
