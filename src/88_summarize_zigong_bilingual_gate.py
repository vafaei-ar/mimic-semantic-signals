from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


def q(x,p):
    return float(np.quantile(np.asarray(x,dtype=float),p))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--jev-laya",required=True)
    ap.add_argument("--diffusiongemma",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()

    cfg=json.loads(Path(args.config).read_text(encoding="utf-8"))
    jl=json.loads(Path(args.jev_laya).read_text(encoding="utf-8"))
    dg=json.loads(Path(args.diffusiongemma).read_text(encoding="utf-8"))

    models={
        "open_jev":jl["models"]["open_jev"],
        "laya":jl["models"]["laya"],
        "diffusiongemma":{"score_definition":dg["score_definition"],"scores":dg["scores"]},
    }
    constructs=cfg["constructs"]
    thresholds=cfg["thresholds"]
    expected_ids=[
        f"{c['construct']}__{state}__{lang}"
        for c in cfg["contrasts"]
        for state in ("negative","positive")
        for lang in ("en","zh")
    ]

    out_models={}
    eligible=[]
    for model_name,model in models.items():
        scores=model["scores"]
        complete=all(cid in scores and all(k in scores[cid] for k in constructs) for cid in expected_ids)
        en=[]; zh=[]; absdiff=[]
        if complete:
            for contrast in cfg["contrasts"]:
                c=contrast["construct"]
                for state in ("negative","positive"):
                    a=scores[f"{c}__{state}__en"]
                    b=scores[f"{c}__{state}__zh"]
                    for k in constructs:
                        en.append(float(a[k])); zh.append(float(b[k]))
                        absdiff.append(abs(float(a[k])-float(b[k])))
            rho=float(spearmanr(en,zh).statistic)
        else:
            rho=float("nan")

        target_deltas={}
        correct=0; strong=0
        if complete:
            for contrast in cfg["contrasts"]:
                c=contrast["construct"]
                d_en=float(scores[f"{c}__positive__en"][c])-float(scores[f"{c}__negative__en"][c])
                d_zh=float(scores[f"{c}__positive__zh"][c])-float(scores[f"{c}__negative__zh"][c])
                ok=(d_en>0 and d_zh>0)
                strong_ok=(d_en>=thresholds["strong_margin"] and d_zh>=thresholds["strong_margin"])
                correct += int(ok); strong += int(strong_ok)
                target_deltas[c]={
                    "english_delta":d_en,
                    "chinese_delta":d_zh,
                    "correct_both_languages":ok,
                    "strong_both_languages":strong_ok,
                }

        median_abs=q(absdiff,.5) if absdiff else None
        pass_components={
            "all_32_notes_scored":bool(complete),
            "language_spearman_at_least_threshold":bool(complete and np.isfinite(rho) and rho>=thresholds["min_language_spearman"]),
            "median_abs_difference_at_most_threshold":bool(complete and median_abs<=thresholds["max_median_absolute_language_difference"]),
            "target_directions_at_least_threshold":bool(correct>=thresholds["min_positive_target_contrasts_both_languages"]),
            "strong_target_directions_at_least_threshold":bool(strong>=thresholds["min_strong_target_contrasts_both_languages"]),
        }
        passed=all(pass_components.values())
        if passed: eligible.append(model_name)
        out_models[model_name]={
            "score_definition":model["score_definition"],
            "all_required_notes_scored":bool(complete),
            "cross_language_spearman":rho if np.isfinite(rho) else None,
            "absolute_language_difference":{
                "mean":float(np.mean(absdiff)) if absdiff else None,
                "median":median_abs,
                "p90":q(absdiff,.9) if absdiff else None,
                "max":float(np.max(absdiff)) if absdiff else None,
                "n":len(absdiff),
            },
            "target_contrast_correct_both_languages":int(correct),
            "target_contrast_strong_both_languages":int(strong),
            "target_deltas":target_deltas,
            "pass_components":pass_components,
            "passed_direct_chinese_gate":bool(passed),
        }

    report={
        "analysis":"Frozen label-free bilingual semantic applicability gate for Zigong direct-Chinese scoring",
        "protocol":"docs/zigong_bilingual_semantic_gate_v1.md",
        "config":"configs/zigong_bilingual_semantic_gate_v1.json",
        "synthetic_only":True,
        "zigong_outcome_labels_read_or_used":False,
        "patient_data_read":False,
        "thresholds":thresholds,
        "models":out_models,
        "eligible_for_direct_chinese_zigong_outcome_scoring":eligible,
        "ineligible_models":[m for m in models if m not in eligible],
        "guardrail":"Eligibility is frozen from this synthetic label-free gate. Do not adapt prompts, translate notes, tune thresholds, or change model preprocessing in response to Zigong outcome performance."
    }
    out=Path(args.output).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
