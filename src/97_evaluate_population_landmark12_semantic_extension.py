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
SEMANTIC_NAMES=[
    "overall_clinician_concern","worsening_trajectory","respiratory_concern",
    "hemodynamic_concern","poor_treatment_response","escalation_considered",
    "diagnostic_uncertainty","reassuring_stability",
]
THRESHOLDS=(0.0025,0.005,0.0075,0.01,0.015,0.02,0.03,0.05)
SEED=20260924
MODEL_NAMES=[
    "structured",
    "structured_context",
    "structured_context_openjev",
    "structured_context_laya",
    "structured_context_tfidf",
    "structured_context_tfidf_openjev",
    "structured_context_tfidf_laya",
]
COMPARISONS={
    "openjev_vs_context":("structured_context","structured_context_openjev"),
    "laya_vs_context":("structured_context","structured_context_laya"),
    "openjev_after_tfidf":("structured_context_tfidf","structured_context_tfidf_openjev"),
    "laya_after_tfidf":("structured_context_tfidf","structured_context_tfidf_laya"),
}


def load_helper():
    path=Path(__file__).with_name("94_evaluate_population_landmark12_structured.py")
    spec=importlib.util.spec_from_file_location("population_structured_helpers_semantic",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen population metric helpers.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def load_cases(path: Path) -> pd.DataFrame:
    rows=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec=json.loads(line)
            cid=str(rec.get("case_id"))
            text=rec.get("model_state",{}).get("clinical_note")
            if not cid or cid=="None" or not isinstance(text,str) or not text.strip():
                raise RuntimeError(f"Invalid note row in {path}")
            rows.append({"case_id":cid,"note_text":text})
    out=pd.DataFrame(rows)
    if out["case_id"].duplicated().any():
        raise RuntimeError(f"Duplicate case_id in {path}")
    return out


def load_mapping(path: Path,outcome: str) -> pd.DataFrame:
    rows=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec=json.loads(line)
            if str(rec.get("outcome"))!=outcome:
                continue
            rows.append({
                "case_id":str(rec["case_id"]),
                "note_case_id":str(rec["note_case_id"]),
            })
    out=pd.DataFrame(rows)
    if not out.empty and out["case_id"].duplicated().any():
        raise RuntimeError(f"{outcome}: duplicate mapping case_id")
    return out


def load_semantic_raw(path: Path,prefix: str) -> pd.DataFrame:
    rows=[]
    seen=set()
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec=json.loads(line)
            cid=str(rec.get("case_id"))
            if not cid or cid=="None" or cid in seen:
                raise RuntimeError(f"{path}: missing or duplicate case_id")
            seen.add(cid)
            if rec.get("status")!="ok":
                raise RuntimeError(f"{path}: non-ok semantic row for {cid}")
            ans=rec.get("response",{}).get("answers",{})
            row={"note_case_id":cid}
            for name in SEMANTIC_NAMES:
                item=ans.get(name,{})
                p=item.get("noul") if isinstance(item,dict) else None
                if not isinstance(p,(int,float)):
                    raise RuntimeError(f"{path}: missing {name} score for {cid}")
                row[f"{prefix}_{name}"]=float(p)
            rows.append(row)
    out=pd.DataFrame(rows)
    if len(out)!=36117:
        raise RuntimeError(f"{path}: expected 36117 semantic rows, found {len(out)}")
    return out


def normalize_has_note(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s):
        return s.astype(int)
    if pd.api.types.is_numeric_dtype(s):
        return (pd.to_numeric(s,errors="coerce").fillna(0)>0).astype(int)
    return s.astype(str).str.lower().isin({"true","1","yes"}).astype(int)


def load_outcome_frame(base: Path,outcome: str,mapping_path: Path,oj: pd.DataFrame,laya: pd.DataFrame):
    structured=pd.read_csv(base/outcome/"structured_features_local.csv",low_memory=False)
    index=pd.read_csv(base/outcome/"population_index_local.csv",low_memory=False)
    context_cols=["case_id","category","dbsource","hours_since_icu"]
    missing=[c for c in context_cols if c not in index.columns]
    if missing:
        raise RuntimeError(f"{outcome}: population index missing {missing}")

    df=structured.merge(index[context_cols],on="case_id",how="left",validate="one_to_one")
    df["has_note"]=normalize_has_note(df["has_note"])
    df["note_age_hours"]=np.where(
        df["has_note"].eq(1),
        12.0-pd.to_numeric(df["hours_since_icu"],errors="coerce"),
        np.nan,
    )
    df["category"]=df["category"].fillna("NO_NOTE").astype(str)
    df["dbsource"]=df["dbsource"].fillna("NO_NOTE").astype(str)

    notes=load_cases(base/outcome/"cases.jsonl")
    df=df.merge(notes,on="case_id",how="left",validate="one_to_one")
    df["note_text"]=df["note_text"].fillna("")
    if ((df["has_note"]==1)&df["note_text"].eq("")).any():
        raise RuntimeError(f"{outcome}: has_note row missing text")
    if ((df["has_note"]==0)&df["note_text"].ne("")).any():
        raise RuntimeError(f"{outcome}: no-note row unexpectedly has text")

    mapping=load_mapping(mapping_path,outcome)
    df=df.merge(mapping,on="case_id",how="left",validate="one_to_one")
    if ((df["has_note"]==1)&df["note_case_id"].isna()).any():
        raise RuntimeError(f"{outcome}: has_note row missing deduplicated mapping")
    if ((df["has_note"]==0)&df["note_case_id"].notna()).any():
        raise RuntimeError(f"{outcome}: no-note row unexpectedly has note mapping")

    df=df.merge(oj,on="note_case_id",how="left",validate="many_to_one")
    df=df.merge(laya,on="note_case_id",how="left",validate="many_to_one")

    oj_cols=[f"oj_{x}" for x in SEMANTIC_NAMES]
    laya_cols=[f"laya_{x}" for x in SEMANTIC_NAMES]
    if df.loc[df["has_note"]==1,oj_cols].isna().any().any():
        raise RuntimeError(f"{outcome}: missing Open-Jev scores for note-available rows")
    if df.loc[df["has_note"]==1,laya_cols].isna().any().any():
        raise RuntimeError(f"{outcome}: missing Laya scores for note-available rows")
    if df.loc[df["has_note"]==0,oj_cols+laya_cols].notna().any().any():
        raise RuntimeError(f"{outcome}: semantic score present for no-note row")
    return df


def weighted_decision_net_benefit(y,p,w,threshold):
    y=np.asarray(y,dtype=int)
    p=np.asarray(p,dtype=float)
    w=np.asarray(w,dtype=float)
    pred=p>=threshold
    n=float(w.sum())
    tp=float(np.dot(w,pred&(y==1)))
    fp=float(np.dot(w,pred&(y==0)))
    return float(tp/n-(fp/n)*(threshold/(1-threshold)))


def paired_cluster_bootstrap(df,preds,helper,n_boot=1000):
    y=df["label"].astype(int).to_numpy()
    patient_codes,patients=pd.factorize(df["subject_id"],sort=False)
    n_patients=len(patients)
    rng=np.random.default_rng(SEED)

    needed=sorted(set(x for pair in COMPARISONS.values() for x in pair))
    prepared={m:helper._prepare_weighted_rank_metrics(y,preds[m]) for m in needed}
    sqerr={m:(np.asarray(preds[m],dtype=float)-y.astype(float))**2 for m in needed}

    out={
        key:{
            "delta_auroc":[],
            "delta_auprc":[],
            "delta_brier":[],
            "delta_net_benefit":{f"{t:.4f}":[] for t in THRESHOLDS},
        }
        for key in COMPARISONS
    }

    for b in range(n_boot):
        sampled=rng.integers(0,n_patients,size=n_patients)
        mult=np.bincount(sampled,minlength=n_patients).astype(float)
        w=mult[patient_codes]
        n=float(w.sum())
        if float(np.dot(w,y))<=0 or float(np.dot(w,1-y))<=0:
            continue

        vals={}
        for m in needed:
            auc,ap=helper._weighted_auc_ap(prepared[m],w)
            if auc is None or ap is None:
                raise RuntimeError("Unexpected degenerate weighted bootstrap replicate")
            vals[m]={
                "auroc":float(auc),
                "auprc":float(ap),
                "brier":float(np.dot(w,sqerr[m])/n),
                "nb":{
                    f"{t:.4f}":weighted_decision_net_benefit(y,preds[m],w,t)
                    for t in THRESHOLDS
                },
            }

        for key,(base,aug) in COMPARISONS.items():
            out[key]["delta_auroc"].append(vals[aug]["auroc"]-vals[base]["auroc"])
            out[key]["delta_auprc"].append(vals[aug]["auprc"]-vals[base]["auprc"])
            out[key]["delta_brier"].append(vals[aug]["brier"]-vals[base]["brier"])
            for t in THRESHOLDS:
                tk=f"{t:.4f}"
                out[key]["delta_net_benefit"][tk].append(vals[aug]["nb"][tk]-vals[base]["nb"][tk])

        if (b+1)%100==0 or b+1==n_boot:
            update_progress(
                current=b+1,total=n_boot,
                phase="population_semantic_paired_bootstrap",
                message=f"paired patient bootstrap {b+1}/{n_boot}",
                unit="bootstrap",
            )

    def ci(x):
        a=np.asarray(x,dtype=float)
        return [float(np.quantile(a,.025)),float(np.quantile(a,.975))]

    return {
        key:{
            "replicates":int(len(v["delta_auroc"])),
            "delta_auroc_ci95":ci(v["delta_auroc"]),
            "delta_auprc_ci95":ci(v["delta_auprc"]),
            "delta_brier_ci95":ci(v["delta_brier"]),
            "delta_net_benefit_ci95":{t:ci(x) for t,x in v["delta_net_benefit"].items()},
        }
        for key,v in out.items()
    }


def main():
    ap=argparse.ArgumentParser(description="Evaluate frozen population semantic extension.")
    ap.add_argument("--base",required=True)
    ap.add_argument("--semantic-base",required=True)
    ap.add_argument("--structured-reference",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--folds",type=int,default=5)
    ap.add_argument("--bootstrap-replicates",type=int,default=1000)
    ap.add_argument("--max-features",type=int,default=10000)
    args=ap.parse_args()

    from scipy import sparse
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder,StandardScaler

    helper=load_helper()
    base=Path(args.base).expanduser().resolve()
    semantic_base=Path(args.semantic_base).expanduser().resolve()
    output=Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True,exist_ok=True)

    mapping_path=semantic_base/"case_to_note_mapping.jsonl"
    oj=load_semantic_raw(semantic_base/"open_jev_raw.jsonl","oj")
    laya=load_semantic_raw(semantic_base/"laya_raw.jsonl","laya")
    structured_ref=json.loads(Path(args.structured_reference).read_text(encoding="utf-8"))

    report={
        "analysis":"Population-representative semantic extension v1",
        "protocol":"docs/population_landmark12_semantic_extension_protocol_v1.md",
        "local_only":True,
        "contains_note_text":False,
        "contains_source_patient_identifiers":False,
        "contains_row_level_predictions":False,
        "semantic_inference_labels_read_or_used":False,
        "models":MODEL_NAMES,
        "comparisons":{k:{"base":v[0],"augmented":v[1]} for k,v in COMPARISONS.items()},
        "folds":int(args.folds),
        "bootstrap_replicates":int(args.bootstrap_replicates),
        "decision_thresholds":[float(x) for x in THRESHOLDS],
        "outcomes":{},
    }

    total_folds=len(OUTCOMES)*args.folds
    fold_done=0
    for oi,outcome in enumerate(OUTCOMES):
        df=load_outcome_frame(base,outcome,mapping_path,oj,laya)
        y=df["label"].astype(int).to_numpy()
        groups=df["subject_id"].to_numpy()

        structured_cols=[
            c for c in df.columns
            if c not in {
                "case_id","subject_id","icustay_id","label","has_note",
                "category","dbsource","hours_since_icu","note_age_hours",
                "note_text","note_case_id",
                *[f"oj_{x}" for x in SEMANTIC_NAMES],
                *[f"laya_{x}" for x in SEMANTIC_NAMES],
            }
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        if len(structured_cols)!=11:
            raise RuntimeError(f"{outcome}: expected 11 structured features, found {len(structured_cols)}")
        context_num=structured_cols+["has_note","note_age_hours"]
        cats=["category","dbsource"]
        oj_cols=[f"oj_{x}" for x in SEMANTIC_NAMES]
        laya_cols=[f"laya_{x}" for x in SEMANTIC_NAMES]

        def make_preprocessor(num_cols):
            return ColumnTransformer(
                [
                    (
                        "num",
                        Pipeline([
                            ("impute",SimpleImputer(strategy="median",add_indicator=True)),
                            ("scale",StandardScaler()),
                        ]),
                        num_cols,
                    ),
                    ("cat",OneHotEncoder(handle_unknown="ignore"),cats),
                ],
                remainder="drop",
            )

        preds={m:np.full(len(df),np.nan,dtype=float) for m in MODEL_NAMES}
        vocab=[]
        cv=StratifiedGroupKFold(
            n_splits=args.folds,
            shuffle=True,
            random_state=SEED+oi*100,
        )

        for fold,(tr,te) in enumerate(cv.split(df,y,groups=groups),start=1):
            train=df.iloc[tr]
            test=df.iloc[te]

            struct_pipe=Pipeline([
                ("impute",SimpleImputer(strategy="median",add_indicator=True)),
                ("scale",StandardScaler()),
            ])
            xs_tr=sparse.csr_matrix(struct_pipe.fit_transform(train[structured_cols]))
            xs_te=sparse.csr_matrix(struct_pipe.transform(test[structured_cols]))

            context_pre=make_preprocessor(context_num)
            xc_tr=sparse.csr_matrix(context_pre.fit_transform(train[context_num+cats]))
            xc_te=sparse.csr_matrix(context_pre.transform(test[context_num+cats]))

            oj_pre=make_preprocessor(context_num+oj_cols)
            xoj_tr=sparse.csr_matrix(oj_pre.fit_transform(train[context_num+oj_cols+cats]))
            xoj_te=sparse.csr_matrix(oj_pre.transform(test[context_num+oj_cols+cats]))

            laya_pre=make_preprocessor(context_num+laya_cols)
            xla_tr=sparse.csr_matrix(laya_pre.fit_transform(train[context_num+laya_cols+cats]))
            xla_te=sparse.csr_matrix(laya_pre.transform(test[context_num+laya_cols+cats]))

            vec=TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1,2),
                min_df=5,
                max_df=0.98,
                max_features=args.max_features,
                sublinear_tf=True,
                dtype=np.float64,
            )
            xt_tr=vec.fit_transform(train["note_text"].astype(str))
            xt_te=vec.transform(test["note_text"].astype(str))
            vocab.append(int(len(vec.vocabulary_)))

            matrices={
                "structured":(xs_tr,xs_te),
                "structured_context":(xc_tr,xc_te),
                "structured_context_openjev":(xoj_tr,xoj_te),
                "structured_context_laya":(xla_tr,xla_te),
                "structured_context_tfidf":(
                    sparse.hstack([xc_tr,xt_tr],format="csr"),
                    sparse.hstack([xc_te,xt_te],format="csr"),
                ),
                "structured_context_tfidf_openjev":(
                    sparse.hstack([xoj_tr,xt_tr],format="csr"),
                    sparse.hstack([xoj_te,xt_te],format="csr"),
                ),
                "structured_context_tfidf_laya":(
                    sparse.hstack([xla_tr,xt_tr],format="csr"),
                    sparse.hstack([xla_te,xt_te],format="csr"),
                ),
            }
            for name,(xtr,xte) in matrices.items():
                model=LogisticRegression(
                    max_iter=3000,solver="liblinear",C=1.0,class_weight=None
                )
                model.fit(xtr,y[tr])
                preds[name][te]=model.predict_proba(xte)[:,1]

            fold_done+=1
            update_progress(
                current=fold_done,total=total_folds,
                phase="population_semantic_crossfit",
                message=f"{outcome}: fold {fold}/{args.folds}",
                unit="fold",
            )

        for name,p in preds.items():
            if np.isnan(p).any():
                raise RuntimeError(f"{outcome}: missing OOF predictions for {name}")

        metrics={name:helper.basic_metrics(y,p) for name,p in preds.items()}

        ref=structured_ref["outcomes"][outcome]["metrics"]
        for metric in ("auroc","auprc","brier"):
            if abs(float(metrics["structured"][metric])-float(ref[metric]))>1e-12:
                raise RuntimeError(
                    f"{outcome}: structured fold-reuse check failed for {metric}: "
                    f"{metrics['structured'][metric]} vs {ref[metric]}"
                )

        point={}
        for key,(base_name,aug_name) in COMPARISONS.items():
            point[key]={
                "delta_auroc":float(metrics[aug_name]["auroc"]-metrics[base_name]["auroc"]),
                "delta_auprc":float(metrics[aug_name]["auprc"]-metrics[base_name]["auprc"]),
                "delta_brier":float(metrics[aug_name]["brier"]-metrics[base_name]["brier"]),
                "delta_net_benefit":{
                    t:float(
                        metrics[aug_name]["decision_curve"][t]["model_net_benefit"]
                        -metrics[base_name]["decision_curve"][t]["model_net_benefit"]
                    )
                    for t in metrics[base_name]["decision_curve"]
                },
            }

        paired=paired_cluster_bootstrap(
            df[["subject_id","label"]],
            preds,
            helper,
            n_boot=args.bootstrap_replicates,
        )

        report["outcomes"][outcome]={
            "n":int(len(df)),
            "cases":int(y.sum()),
            "controls":int(len(y)-y.sum()),
            "prevalence":float(y.mean()),
            "note_available":int(df["has_note"].sum()),
            "note_coverage":float(df["has_note"].mean()),
            "tfidf_vocabulary_size_by_fold":vocab,
            "metrics":metrics,
            "paired_semantic_comparisons":point,
            "paired_patient_bootstrap_ci95":paired,
        }

    report["guardrail"]=(
        "Full prevalence-preserving population analysis. No-note rows are retained with explicit "
        "context levels and missing semantic values handled inside training folds. Semantic inference "
        "was completed without labels. Paired bootstrap differences are augmented minus baseline; "
        "negative Brier differences favor the augmented model."
    )
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
