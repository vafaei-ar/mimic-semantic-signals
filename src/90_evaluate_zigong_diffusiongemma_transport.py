from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SEMANTIC_NAMES=[
    "overall_clinician_concern","worsening_trajectory","respiratory_concern",
    "hemodynamic_concern","poor_treatment_response","escalation_considered",
    "diagnostic_uncertainty","reassuring_stability",
]


def load_eval_helpers():
    path=Path(__file__).with_name("67_evaluate_multitask_diffusiongemma_hf.py")
    spec=importlib.util.spec_from_file_location("dg_eval_helpers_for_zigong",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load frozen DiffusionGemma evaluation helpers.")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def load_zigong_labels(path: Path) -> pd.DataFrame:
    rows=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec=json.loads(line)
            meta=rec.get("metadata",{})
            rows.append({
                "case_id":str(rec["case_id"]),
                "label":int(meta["label"]),
                "match_set":int(meta["match_set"]),
            })
    out=pd.DataFrame(rows)
    if len(out)!=340 or out["case_id"].duplicated().any():
        raise RuntimeError("Frozen Zigong cohort labels are incomplete or duplicated.")
    if int(out["label"].sum())!=85 or len(out)!=340:
        raise RuntimeError("Frozen Zigong cohort count mismatch.")
    return out


def metric_summary(y,p):
    from sklearn.metrics import average_precision_score,brier_score_loss,roc_auc_score
    return {
        "auroc":float(roc_auc_score(y,p)),
        "auprc":float(average_precision_score(y,p)),
        "brier":float(brier_score_loss(y,p)),
    }


def matched_bootstrap(df: pd.DataFrame, probability_col: str, seed:int, n_boot:int):
    from sklearn.metrics import average_precision_score,brier_score_loss,roc_auc_score
    sets=df["match_set"].drop_duplicates().to_numpy()
    by={k:g.copy() for k,g in df.groupby("match_set",sort=False)}
    rng=np.random.default_rng(seed)
    aucs=[]; aps=[]; briers=[]
    for _ in range(n_boot):
        sampled=rng.choice(sets,size=len(sets),replace=True)
        boot=pd.concat([by[x] for x in sampled],ignore_index=True)
        y=boot["label"].to_numpy(dtype=int)
        p=boot[probability_col].to_numpy(dtype=float)
        aucs.append(float(roc_auc_score(y,p)))
        aps.append(float(average_precision_score(y,p)))
        briers.append(float(brier_score_loss(y,p)))
    return {
        "auroc_ci95":[float(np.quantile(aucs,.025)),float(np.quantile(aucs,.975))],
        "auprc_ci95":[float(np.quantile(aps,.025)),float(np.quantile(aps,.975))],
        "brier_ci95":[float(np.quantile(briers,.025)),float(np.quantile(briers,.975))],
        "bootstrap_replicates":int(n_boot),
        "cluster":"match_set",
    }


def main():
    ap=argparse.ArgumentParser(description="Frozen MIMIC-to-Zigong DiffusionGemma semantic transport evaluation.")
    ap.add_argument("--mimic-features",required=True)
    ap.add_argument("--mimic-dg",required=True)
    ap.add_argument("--zigong-cases",required=True)
    ap.add_argument("--zigong-dg",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--bootstrap-replicates",type=int,default=2000)
    ap.add_argument("--seed",type=int,default=20260924)
    args=ap.parse_args()

    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    helper=load_eval_helpers()
    mimic_features=pd.read_csv(Path(args.mimic_features))
    mimic_dg=helper.load_diffusiongemma(Path(args.mimic_dg))
    mimic=mimic_features[["case_id","label"]].merge(mimic_dg,on="case_id",how="inner")
    if len(mimic)!=len(mimic_features) or len(mimic)!=1460:
        raise RuntimeError(f"Frozen MIMIC ventilation training count mismatch: {len(mimic)}")
    if int(mimic["label"].sum())!=365:
        raise RuntimeError("Frozen MIMIC ventilation case count mismatch.")

    zig_labels=load_zigong_labels(Path(args.zigong_cases))
    zig_dg=helper.load_diffusiongemma(Path(args.zigong_dg))
    zig=zig_labels.merge(zig_dg,on="case_id",how="inner")
    if len(zig)!=340:
        raise RuntimeError(f"Expected 340 complete Zigong DiffusionGemma rows, found {len(zig)}")

    cols=[f"dg_{x}" for x in SEMANTIC_NAMES]
    pre=ColumnTransformer([
        ("num",Pipeline([
            ("impute",SimpleImputer(strategy="median",add_indicator=True)),
            ("scale",StandardScaler()),
        ]),cols)
    ],remainder="drop")
    model=Pipeline([
        ("pre",pre),
        ("model",LogisticRegression(max_iter=3000,solver="liblinear",C=1.0)),
    ])
    model.fit(mimic[cols],mimic["label"].astype(int).to_numpy())
    zig["transport_probability"]=model.predict_proba(zig[cols])[:,1]

    y=zig["label"].astype(int).to_numpy()
    p=zig["transport_probability"].to_numpy(dtype=float)
    primary=metric_summary(y,p)
    primary.update(matched_bootstrap(
        zig[["label","match_set","transport_probability"]],
        "transport_probability",
        seed=args.seed,
        n_boot=args.bootstrap_replicates,
    ))

    constructs={}
    for name in SEMANTIC_NAMES:
        raw=zig[f"dg_{name}"].to_numpy(dtype=float)
        oriented=1.0-raw if name=="reassuring_stability" else raw
        constructs[name]={
            "orientation":"1-score" if name=="reassuring_stability" else "score",
            "auroc":float(roc_auc_score(y,oriented)),
            "case_mean":float(oriented[y==1].mean()),
            "control_mean":float(oriented[y==0].mean()),
        }

    report={
        "analysis":"Frozen MIMIC-to-Zigong DiffusionGemma semantic external transport v1",
        "protocol":"docs/zigong_diffusiongemma_external_transport_protocol_v1.md",
        "eligibility_gate_job":"H7R4K9M3",
        "eligibility_gate_artifact_sha256":"4a225fe589da282c528daa1159c909c83817e8e6fe78a8236c10b691cda99fac",
        "local_only":True,
        "contains_note_text":False,
        "contains_source_patient_identifiers":False,
        "patient_level_predictions_shared":False,
        "zigong_model_fitting_performed":False,
        "recalibration_performed":False,
        "model":"google/diffusiongemma-26B-A4B-it",
        "score_definition":"Prompted zero-shot 0-1 support scores; not Jev noul probabilities.",
        "training_dataset":{
            "name":"Frozen MIMIC-III invasive ventilation 12h benchmark",
            "n":int(len(mimic)),
            "cases":int(mimic["label"].sum()),
            "controls":int((1-mimic["label"]).sum()),
        },
        "external_dataset":{
            "name":"Frozen Zigong invasive ventilation 24h narrative risk-set cohort",
            "n":int(len(zig)),
            "cases":int(zig["label"].sum()),
            "controls":int((1-zig["label"]).sum()),
            "matched_sets":int(zig["match_set"].nunique()),
            "sampled_prevalence":float(zig["label"].mean()),
        },
        "transport_model":{
            "features":[f"dg_{x}" for x in SEMANTIC_NAMES],
            "preprocessing":"median imputation with missing indicators, then standard scaling",
            "classifier":"LogisticRegression(liblinear, C=1.0, max_iter=3000)",
            "fit_on":"MIMIC only",
            "applied_to":"Zigong without refitting, recalibration, or threshold selection",
        },
        "primary_transport_metrics":primary,
        "construct_level_exploratory":constructs,
        "interpretation_guardrail":(
            "This is a secondary external site+language+24h temporal-horizon transport analysis. "
            "The Zigong cohort has artificial 25% prevalence, so AUPRC is sample-conditional and "
            "Brier score is descriptive rather than population calibration."
        ),
    }
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
